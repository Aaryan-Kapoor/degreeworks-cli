"""Authentication commands: login, whoami, plus silent headless refresh."""

import os
import time
from urllib.parse import parse_qs, urlparse

import click

from ..auth import get_student_info, load_cookies
from ..config import BROWSER_PROFILE, CONFIG_DIR, COOKIES_FILE, save_config
from ..errors import handle_errors
from ..formatting import get_format, output, section

# Env var to disable the automatic background refresh (mirrors d2l).
AUTO_LOGIN_DISABLED_ENV = "DEGREEWORKS_NO_AUTO_LOGIN"

# Interactive logins wait for a human at the SSO screen; headless refreshes
# reuse the saved SSO session and should either work fast or give up quickly.
LOGIN_WAIT_SECONDS = 120
HEADLESS_WAIT_SECONDS = 30


def _has_auth_cookie(cookies: list[dict]) -> bool:
    """Check if the captured cookies include a DegreeWorks auth token."""
    return any(c.get("name") == "X-AUTH-TOKEN" for c in cookies)


def _launch_context(p, headless, channel):
    """Launch a persistent browser context, falling back across browsers.

    'auto' tries Playwright's bundled Chromium first, then installed Chrome and
    Edge — so login works even when `playwright install chromium` was never run,
    as long as any Chromium-family browser is on the machine.
    """
    if channel == "auto":
        attempts = [(None, "bundled Chromium"), ("chrome", "Google Chrome"), ("msedge", "Microsoft Edge")]
    elif channel == "chromium":
        attempts = [(None, "bundled Chromium")]
    else:
        attempts = [(channel, channel)]

    errors = []
    for chan, label in attempts:
        kwargs = {"headless": headless, "viewport": {"width": 1280, "height": 720}}
        if chan:
            kwargs["channel"] = chan
        try:
            return p.chromium.launch_persistent_context(str(BROWSER_PROFILE), **kwargs), label
        except Exception as e:
            first_line = str(e).splitlines()[0] if str(e).strip() else type(e).__name__
            errors.append(f"    {label}: {first_line}")

    return None, errors


def _capture_and_save(headless, channel="auto", quiet=False):
    """Launch a browser, capture DegreeWorks cookies, and save them.

    Returns True on success. quiet=True suppresses all output — used by the
    automatic background refresh so command output stays clean.
    """
    def echo(msg, err=False):
        if not quiet:
            click.echo(msg, err=err)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        echo(
            'Playwright not installed. Install with:\n'
            '  pip install "degreeworks-cli[login]"',
            err=True,
        )
        return False

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Capture school/degree from the first /api/audit request.
    captured = {}

    def on_request(request):
        url = request.url
        if "/api/audit" in url and "studentId" in url:
            try:
                qs = parse_qs(urlparse(url).query)
                if "school" in qs and "degree" in qs:
                    captured.setdefault("school", qs["school"][0])
                    captured.setdefault("degree", qs["degree"][0])
                    captured.setdefault("audit_type", qs.get("audit-type", ["AA"])[0])
            except Exception:
                pass

    with sync_playwright() as p:
        context, launch_result = _launch_context(p, headless, channel)
        if context is None:
            echo("[!] Could not launch a browser for login. Tried:", err=True)
            for line in launch_result:
                echo(line, err=True)
            echo(
                "    Fix: run `python -m playwright install chromium`, "
                "or install Google Chrome / Microsoft Edge.",
                err=True,
            )
            return False

        page = context.pages[0] if context.pages else context.new_page()
        page.on("request", on_request)

        if not headless:
            echo("Opening DegreeWorks... Log in with your KSU credentials.")
        else:
            echo("Refreshing cookies (headless)...")

        page.goto("https://degreeworks.kennesaw.edu/")

        # Wait for both the auth cookie AND the audit request (for school/degree).
        deadline = time.time() + (HEADLESS_WAIT_SECONDS if headless else LOGIN_WAIT_SECONDS)
        while time.time() < deadline:
            cookies = page.context.cookies()
            if _has_auth_cookie(cookies) and captured.get("school"):
                break
            time.sleep(1)
        else:
            cookies = page.context.cookies()
            if not _has_auth_cookie(cookies):
                echo("Timed out waiting for login. Try again." if not headless
                     else "[!] Headless refresh timed out (saved session may be expired).",
                     err=True)
                context.close()
                return False
            # Got cookies but not the audit request — proceed with existing config.
            if not headless:
                echo("Note: couldn't auto-detect school/degree. Keeping existing config.")

        time.sleep(1)
        cookies = page.context.cookies()

        # Filter to degreeworks.kennesaw.edu cookies only.
        dw_cookies = [c for c in cookies if "degreeworks" in c.get("domain", "")]
        all_cookies = dw_cookies if dw_cookies else cookies
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in all_cookies)

        COOKIES_FILE.write_text(cookie_str)

        if captured.get("school") and captured.get("degree"):
            save_config(
                school=captured["school"],
                degree=captured["degree"],
                audit_type=captured.get("audit_type", "AA"),
            )

        info = get_student_info(cookie_str)
        if info.get("name"):
            expires = time.strftime(
                "%H:%M:%S", time.localtime(info["expires"])
            ) if info.get("expires") else "unknown"
            echo(f"Logged in as: {info['name']} ({info['student_id']})")
            echo(f"Auth token expires at: {expires} (90 min)")
            echo(f"Cookies saved to {COOKIES_FILE}")
            if captured.get("school"):
                echo(f"Detected degree: {captured['school']}/{captured['degree']}")
        else:
            echo(f"Cookies saved to {COOKIES_FILE} (could not decode token)")

        context.close()

    return True


def _playwright_available():
    from importlib.util import find_spec

    return find_spec("playwright") is not None


def attempt_auto_login():
    """Silent headless cookie refresh using the saved browser profile.

    Called automatically when a command finds the session missing/expired.
    Returns True if fresh cookies were captured; never raises and never opens
    a visible browser.
    """
    if os.environ.get(AUTO_LOGIN_DISABLED_ENV):
        return False
    if not BROWSER_PROFILE.exists():
        return False
    if not _playwright_available():
        return False

    click.echo(
        "[*] DegreeWorks session expired — refreshing sign-in in the background...",
        err=True,
    )
    try:
        return _capture_and_save(headless=True, channel="auto", quiet=True)
    except Exception:
        return False


@click.command()
@click.option("--headless", is_flag=True, help="Headless browser (reuse saved SSO session)")
@click.option(
    "--channel",
    type=click.Choice(["auto", "chromium", "chrome", "msedge"]),
    default="auto",
    show_default=True,
    help="Browser to launch; auto falls back from bundled Chromium to installed Chrome/Edge",
)
@handle_errors
def login(headless, channel):
    """Capture DegreeWorks cookies via browser login.

    Opens a browser to KSU SSO. Log in normally — cookies are captured
    automatically once DegreeWorks loads.

    Use --headless to refresh cookies without a visible browser (requires a
    prior interactive login so the browser profile has saved SSO cookies).
    """
    if not _capture_and_save(headless=headless, channel=channel):
        raise SystemExit(1)


@click.command()
@handle_errors
def whoami():
    """Show current student info from saved cookies."""
    cookies = load_cookies()
    info = get_student_info(cookies)
    if not info.get("student_id"):
        click.echo("Could not decode student info from cookies.", err=True)
        raise SystemExit(1)

    now = time.time()
    expires = info.get("expires", 0)
    remaining_min = max(0, (expires - now) / 60)

    data = {
        "Name": info["name"],
        "Student ID": info["student_id"],
        "Token Expires": time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(expires)
        ) if expires else "unknown",
        "Time Remaining": f"{remaining_min:.0f} min" if expires else "unknown",
        "Status": "ACTIVE" if remaining_min > 0 else "EXPIRED",
    }

    if get_format() == "json":
        output(data)
        return

    section("Student Info")
    output(data)

    if remaining_min <= 0:
        click.echo("\nSession expired. Run `dw login` to re-authenticate.", err=True)
    elif remaining_min < 10:
        click.echo(f"\nSession expiring soon ({remaining_min:.0f} min). Consider running `dw login`.", err=True)
