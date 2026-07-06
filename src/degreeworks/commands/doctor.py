"""`dw doctor` — diagnose install, PATH, auth, and live API access."""

import json
import shutil
import time
from importlib.metadata import version as pkg_version

import click

from ..auth import get_student_info, load_cookies, make_session
from ..client import DegreeworksClient
from ..config import BROWSER_PROFILE, CONFIG_FILE, load_config
from ..errors import DegreeworksError
from ..formatting import get_format


def _check(name, ok, detail, next_step=None, info_only=False):
    return {
        "check": name,
        "ok": bool(ok),
        "detail": detail,
        "next_step": next_step,
        "info_only": info_only,
    }


def _run_checks():
    checks = []

    # 1. CLI version
    try:
        ver = pkg_version("degreeworks-cli")
    except Exception:
        ver = "unknown"
    checks.append(_check("cli", True, f"degreeworks-cli {ver}", info_only=True))

    # 2. PATH — would `dw` resolve in a fresh shell?
    dw_path = shutil.which("dw")
    checks.append(_check(
        "path", dw_path is not None,
        f"dw on PATH: {dw_path}" if dw_path
        else "dw is not on PATH — a fresh terminal won't find it",
        next_step=None if dw_path else "add Python's user scripts dir to PATH (see pip's install warning)",
        info_only=True,
    ))

    # 3. Playwright — only needed for `dw login`
    from importlib.util import find_spec
    have_playwright = find_spec("playwright") is not None
    checks.append(_check(
        "playwright", have_playwright,
        "Playwright installed (browser login available)" if have_playwright
        else "Playwright not installed (only needed for `dw login`)",
        next_step=None if have_playwright else 'pip install "degreeworks-cli[login]"',
        info_only=True,
    ))

    # 4. Config — school/degree
    have_config = CONFIG_FILE.exists()
    cfg = load_config()
    checks.append(_check(
        "config", True,
        f"school={cfg['school']} degree={cfg['degree']} audit={cfg['audit_type']}"
        + ("" if have_config else " (defaults — auto-detected on first login)"),
        info_only=True,
    ))

    # 5. Saved browser profile — enables silent headless refresh
    checks.append(_check(
        "session", BROWSER_PROFILE.exists(),
        "Saved browser session present (silent refresh available)" if BROWSER_PROFILE.exists()
        else "No saved browser session (first login not done yet)",
        next_step=None if BROWSER_PROFILE.exists() else "dw login",
        info_only=True,
    ))

    # 6. Token validity
    student_id = None
    token_ok = False
    try:
        cookies = load_cookies()
        info = get_student_info(cookies)
        student_id = info.get("student_id")
        expires = info.get("expires", 0)
        remaining = (expires - time.time()) / 60 if expires else 0
        token_ok = remaining > 0
        if token_ok:
            detail = f"Token valid for {info.get('name') or student_id}, {remaining:.0f} min remaining"
        else:
            detail = "Auth token expired (a command will try to refresh it silently)"
        checks.append(_check("token", token_ok, detail, next_step=None if token_ok else "dw login"))
    except DegreeworksError as e:
        cookies = None
        checks.append(_check("token", False, str(e).splitlines()[0], next_step="dw login"))

    # 7. Live read-only API call
    if token_ok and student_id:
        try:
            client = DegreeworksClient(
                make_session(cookies),
                school=cfg["school"], degree=cfg["degree"], audit_type=cfg["audit_type"],
            )
            audit = client.get_audit(student_id)
            ok = isinstance(audit, dict) and bool(audit)
            checks.append(_check(
                "api", ok,
                "Degree audit reachable (read-only API OK)" if ok
                else "Audit request returned no data — check school/degree config",
                next_step=None if ok else "dw login",
            ))
        except Exception as e:
            checks.append(_check("api", False, f"API call failed: {str(e).splitlines()[0]}", next_step="dw login"))
    else:
        checks.append(_check("api", False, "Skipped (fix auth first)"))

    return checks


@click.command()
def doctor():
    """Diagnose setup state: install, PATH, Playwright, auth, and live API access.

    Designed for agents: `dw --json doctor` reports every check with a
    `next_step` command, so the next required action is never a guess.
    Exits non-zero when a required check fails.
    """
    checks = _run_checks()
    required_failed = [c for c in checks if not c["ok"] and not c["info_only"]]
    next_steps = [c["next_step"] for c in checks if c["next_step"]]
    result = {
        "status": "ready" if not required_failed else "action_needed",
        "checks": checks,
        "next_step": next_steps[0] if next_steps else None,
    }

    if get_format() == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        for c in checks:
            mark = "ok" if c["ok"] else ("--" if c["info_only"] else "!!")
            line = f"  [{mark}] {c['check']:<10} {c['detail']}"
            if c["next_step"]:
                line += f"  -> {c['next_step']}"
            click.echo(line)
        click.echo()
        if result["status"] == "ready":
            click.echo("Ready." + (f" Suggested: {result['next_step']}" if result["next_step"] else ""))
        else:
            click.echo(f"Action needed. Next: {result['next_step']}")

    if required_failed:
        raise SystemExit(1)
