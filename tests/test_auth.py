"""Unit tests for JWT cookie decoding and expiry logic.

No network or real cookies — we mint synthetic JWTs with known `exp`
claims and assert the auth layer reads them correctly. This is the logic
behind `whoami`'s ACTIVE/EXPIRED status and the pre-flight expiry check.
"""

from __future__ import annotations

import base64
import json
import time

import pytest

from degreeworks.auth import check_token_expiry, get_student_info
from degreeworks.errors import CookieExpiredError


def _jwt(payload: dict) -> str:
    """Build an unsigned JWT with the given payload (signature is ignored)."""

    def seg(d: dict) -> str:
        raw = json.dumps(d).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{seg({'alg': 'HS256', 'typ': 'JWT'})}.{seg(payload)}.sig"


def _cookie(auth_exp: int, refresh_exp: int) -> str:
    auth = _jwt({"sub": "900123456", "name": "Test Owl", "exp": auth_exp})
    refresh = _jwt({"exp": refresh_exp})
    return f"X-AUTH-TOKEN=Bearer+{auth}; REFRESH_TOKEN=Bearer+{refresh}"


def test_get_student_info_decodes_claims():
    info = get_student_info(_cookie(auth_exp=2_000_000_000, refresh_exp=2_000_000_000))
    assert info["student_id"] == "900123456"
    assert info["name"] == "Test Owl"
    assert info["expires"] == 2_000_000_000


def test_active_token_does_not_raise():
    future = int(time.time()) + 3600
    # Should return None without raising for a live auth token.
    assert check_token_expiry(_cookie(auth_exp=future, refresh_exp=future)) is None


def test_expired_auth_live_refresh_suggests_headless():
    now = int(time.time())
    with pytest.raises(CookieExpiredError) as exc:
        check_token_expiry(_cookie(auth_exp=now - 60, refresh_exp=now + 3600))
    assert "dw login --headless" in str(exc.value)


def test_fully_expired_suggests_full_login():
    now = int(time.time())
    with pytest.raises(CookieExpiredError) as exc:
        check_token_expiry(_cookie(auth_exp=now - 3600, refresh_exp=now - 60))
    assert "fully expired" in str(exc.value).lower()
