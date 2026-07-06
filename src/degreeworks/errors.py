"""Exception hierarchy and error handler."""

import functools
import sys

import click


class DegreeworksError(Exception):
    """Base error."""


class CookieNotFoundError(DegreeworksError):
    """No cookies file found."""


class CookieExpiredError(DegreeworksError):
    """Session cookies have expired."""


class APIError(DegreeworksError):
    """DegreeWorks API returned an error."""

    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


def raise_for_status(resp):
    """Map HTTP status codes to typed exceptions."""
    if resp.ok:
        return
    if resp.status_code == 401:
        raise CookieExpiredError(
            "Session expired. Run `dw login` to re-authenticate with KSU SSO."
        )
    raise APIError(resp.status_code, resp.text[:200])


def handle_errors(fn):
    """Decorator that catches errors and prints clean CLI messages."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except CookieNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except CookieExpiredError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except APIError as e:
            click.echo(f"API Error: {e}", err=True)
            sys.exit(1)
        except DegreeworksError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    return wrapper
