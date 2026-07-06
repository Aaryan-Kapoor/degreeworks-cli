"""CLI entry point."""

import sys

# Ensure Unicode output works on Windows consoles (cp1252 by default).
# Progress bars, checkmarks, and en-dashes throughout the UI are non-ASCII.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

import click

from .auth import check_token_expiry, get_student_info, load_cookies, make_session
from .client import DegreeworksClient
from .config import load_config
from .errors import CookieExpiredError, CookieNotFoundError, DegreeworksError
from .formatting import set_format

from .commands.auth_cmd import login, whoami
from .commands.audit import audit
from .commands.completed import completed
from .commands.course import course
from .commands.dump import dump
from .commands.doctor import doctor
from .commands.progress import progress
from .commands.remaining import remaining
from .commands.skill_cmd import skill


def _resolve_cookies() -> str:
    """Load cookies, transparently refreshing them via a silent headless login
    when the session is missing or expired. Only when that silent refresh fails
    does the user need to sign in interactively with `dw login`."""
    from .commands.auth_cmd import attempt_auto_login

    try:
        cookies = load_cookies()
        check_token_expiry(cookies)
        return cookies
    except (CookieExpiredError, CookieNotFoundError) as e:
        if attempt_auto_login():
            cookies = load_cookies()
            check_token_expiry(cookies)
            click.echo("[*] Signed in automatically using your saved session.", err=True)
            return cookies
        raise e.__class__(
            "Your DegreeWorks session needs a fresh sign-in. Run: dw login "
            "(a browser window will open — log in with KSU SSO like normal)"
        ) from e


def _make_client_factory(cookies: str, config: dict):
    """Lazy client initialization."""
    state = {}

    def factory():
        if "client" not in state:
            session = make_session(cookies)
            state["client"] = DegreeworksClient(
                session,
                school=config["school"],
                degree=config["degree"],
                audit_type=config["audit_type"],
            )
        return state["client"]

    return factory


@click.group()
@click.option("--json", "fmt", flag_value="json", help="JSON output")
@click.option("--md", "fmt", flag_value="md", help="Markdown output (best for AI)")
@click.pass_context
def cli(ctx, fmt):
    """DegreeWorks CLI – built for AI agents to plan KSU student schedules.

    Setup:
        dw login            # opens browser, captures cookies
        dw whoami            # verify auth

    Quick start:
        dw progress          # how close to graduation?
        dw remaining         # what courses are left?
        dw course CS 3305    # prereqs, sections, schedules
        dw --md dump         # full snapshot for AI agents
    """
    ctx.ensure_object(dict)

    if fmt:
        set_format(fmt)

    # Skip auth entirely when the user is just asking for help.
    # Click's resilient_parsing flag is set while generating help text.
    # We also check sys.argv so `dw <cmd> --help` works without cookies.
    if ctx.resilient_parsing or "--help" in sys.argv or "-h" in sys.argv:
        return

    # Commands that don't need auth (doctor does its own auth diagnosis)
    if ctx.invoked_subcommand in ("login", "skill", "doctor"):
        return

    try:
        # whoami reports current token status (even when expired) and must not
        # trigger a refresh. Everything else auto-refreshes an expired session.
        if ctx.invoked_subcommand in ("whoami",):
            cookies = load_cookies()
        else:
            cookies = _resolve_cookies()

        info = get_student_info(cookies)
        ctx.obj["student_id"] = info.get("student_id", "")
        ctx.obj["client_factory"] = _make_client_factory(cookies, load_config())
    except DegreeworksError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


cli.add_command(login)
cli.add_command(whoami)
cli.add_command(audit)
cli.add_command(completed)
cli.add_command(course)
cli.add_command(dump)
cli.add_command(progress)
cli.add_command(remaining)
cli.add_command(skill)
cli.add_command(doctor)
