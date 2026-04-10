"""Cookie loading, JWT decoding, and session factory."""

import base64
import json
import time

import requests

from .config import COOKIES_FILE, DEFAULT_HEADERS
from .errors import CookieExpiredError, CookieNotFoundError


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (we just need the claims)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    # Fix base64 padding
    payload += "=" * (4 - len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def _extract_token(cookies: str, name: str) -> dict:
    """Extract and decode a JWT cookie by name."""
    for part in cookies.split(";"):
        part = part.strip()
        if part.startswith(f"{name}="):
            token = part.split("=", 1)[1]
            if token.startswith("Bearer+"):
                token = token[7:]
            return _decode_jwt_payload(token)
    return {}


def load_cookies() -> str:
    """Load cookie string from ~/.degreeworks/cookies.txt or raise."""
    if COOKIES_FILE.exists():
        text = COOKIES_FILE.read_text().strip()
        if text:
            return text
    raise CookieNotFoundError(
        f"No cookies found at {COOKIES_FILE}\n"
        "Run `dw login` to capture cookies automatically, or:\n"
        "  1. Log into degreeworks.kennesaw.edu in your browser\n"
        "  2. Copy the full cookie string from devtools (Network tab → request headers)\n"
        f"  3. Paste into {COOKIES_FILE} (single line, no quotes)"
    )


def get_student_info(cookies: str) -> dict:
    """Extract student info from the X-AUTH-TOKEN JWT in the cookies."""
    payload = _extract_token(cookies, "X-AUTH-TOKEN")
    if not payload:
        return {}
    return {
        "student_id": payload.get("sub", ""),
        "name": payload.get("name", ""),
        "roles": payload.get("roles", []),
        "expires": payload.get("exp", 0),
    }


def check_token_expiry(cookies: str):
    """Check if the auth token is expired and raise with helpful context.

    Checks both X-AUTH-TOKEN (90 min) and REFRESH_TOKEN (8 hrs).
    """
    auth = _extract_token(cookies, "X-AUTH-TOKEN")
    refresh = _extract_token(cookies, "REFRESH_TOKEN")
    now = time.time()

    auth_exp = auth.get("exp", 0)
    refresh_exp = refresh.get("exp", 0)

    if auth_exp and auth_exp > now:
        # Auth token still valid
        remaining = (auth_exp - now) / 60
        if remaining < 5:
            import sys
            print(
                f"Warning: session expiring in {remaining:.0f} minutes. "
                "Run `dw login` soon.",
                file=sys.stderr,
            )
        return

    # Auth token expired — check refresh token
    if refresh_exp and refresh_exp > now:
        remaining = (refresh_exp - now) / 60
        raise CookieExpiredError(
            "Auth token expired, but refresh token is still valid "
            f"({remaining:.0f} min remaining).\n"
            "Run `dw login --headless` to refresh without re-entering credentials."
        )

    # Both expired
    raise CookieExpiredError(
        "Session fully expired (both auth and refresh tokens).\n"
        "Run `dw login` to re-authenticate with KSU SSO."
    )


def make_session(cookies: str) -> requests.Session:
    """Create a requests session with cookies and default headers."""
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    s.headers["Cookie"] = cookies
    return s
