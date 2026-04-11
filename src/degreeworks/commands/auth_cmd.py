"""Authentication commands: login, whoami."""

import time
from urllib.parse import parse_qs, urlparse

import click

from ..auth import get_student_info, load_cookies
from ..config import CONFIG_DIR, COOKIES_FILE, save_config
from ..errors import handle_errors
from ..formatting import get_format, output, section


def _has_auth_cookies(cookies: list[dict]) -> bool:
    """Check if the captured cookies include a DegreeWorks auth token."""
    names = {c["name"] for c in cookies}
    return "X-AUTH-TOKEN" in names


@click.command()
@click.option("--headless", is_flag=True, help="Headless browser (reuse saved SSO session)")
@handle_errors
def login(headless):
    """Capture DegreeWorks cookies via browser login.

    Opens a browser to KSU SSO. Log in normally — cookies are captured
    automatically once DegreeWorks loads.

    Use --headless to refresh cookies without a visible browser (requires
    a prior interactive login so the browser profile has saved SSO cookies).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        click.echo(
            "Playwright not installed. Install with:\n"
            '  pip install "degreeworks-cli[login]"\n'
            "  playwright install chromium"
        )
        raise SystemExit(1)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    browser_profile = CONFIG_DIR / "browser_profile"

    # We'll capture school/degree from the first /api/audit request
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
        browser = p.chromium.launch_persistent_context(
            str(browser_profile),
            headless=headless,
            viewport={"width": 1280, "height": 720},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.on("request", on_request)

        if not headless:
            click.echo("Opening DegreeWorks... Log in with your KSU credentials.")
        else:
            click.echo("Refreshing cookies (headless)...")

        page.goto("https://degreeworks.kennesaw.edu/")

        # Wait for both auth cookies AND the audit request so we can capture
        # school/degree from the query params.
        deadline = time.time() + 120
        while time.time() < deadline:
            cookies = page.context.cookies()
            if _has_auth_cookies(cookies) and captured.get("school"):
                break
            time.sleep(1)
        else:
            cookies = page.context.cookies()
            if not _has_auth_cookies(cookies):
                click.echo("Timed out waiting for login. Try again.", err=True)
                browser.close()
                raise SystemExit(1)
            # We got cookies but not the audit request — proceed with defaults
            click.echo("Note: couldn't auto-detect school/degree. Using defaults (US/BS).")

        # Small delay for all cookies to settle
        time.sleep(1)
        cookies = page.context.cookies()

        # Filter to degreeworks.kennesaw.edu cookies only
        dw_cookies = [c for c in cookies if "degreeworks" in c.get("domain", "")]
        all_cookies = dw_cookies if dw_cookies else cookies
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in all_cookies)

        COOKIES_FILE.write_text(cookie_str)

        # Persist captured school/degree if we got them
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
            click.echo(f"Logged in as: {info['name']} ({info['student_id']})")
            click.echo(f"Auth token expires at: {expires} (90 min)")
            click.echo(f"Cookies saved to {COOKIES_FILE}")
            if captured.get("school"):
                click.echo(
                    f"Detected degree: {captured['school']}/{captured['degree']}"
                )
        else:
            click.echo(f"Cookies saved to {COOKIES_FILE} (could not decode token)")

        browser.close()


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
