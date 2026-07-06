"""Tests for the silent headless session refresh.

No network, no browser. `_capture_and_save` (the only piece that would launch
Playwright) is always mocked out, so these exercise the decision logic:
when a background refresh is attempted, and how an expired session is resolved
before a command runs.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from degreeworks import cli as cli_mod
from degreeworks.commands import auth_cmd
from degreeworks.errors import CookieExpiredError, CookieNotFoundError


class TestAttemptAutoLogin:
    def test_disabled_by_env(self, tmp_path):
        with patch.object(auth_cmd, "BROWSER_PROFILE", tmp_path):
            with patch.dict(os.environ, {auth_cmd.AUTO_LOGIN_DISABLED_ENV: "1"}):
                assert auth_cmd.attempt_auto_login() is False

    def test_no_browser_profile_fails_fast(self, tmp_path):
        with patch.object(auth_cmd, "BROWSER_PROFILE", tmp_path / "nope"):
            os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
            assert auth_cmd.attempt_auto_login() is False

    def test_runs_quiet_headless_capture_when_profile_exists(self, tmp_path):
        with patch.object(auth_cmd, "BROWSER_PROFILE", tmp_path):
            os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
            with patch.object(auth_cmd, "_playwright_available", return_value=True):
                with patch.object(auth_cmd, "_capture_and_save", return_value=True) as cap:
                    assert auth_cmd.attempt_auto_login() is True
        cap.assert_called_once_with(headless=True, channel="auto", quiet=True)

    def test_never_raises(self, tmp_path):
        with patch.object(auth_cmd, "BROWSER_PROFILE", tmp_path):
            os.environ.pop(auth_cmd.AUTO_LOGIN_DISABLED_ENV, None)
            with patch.object(auth_cmd, "_playwright_available", return_value=True):
                with patch.object(auth_cmd, "_capture_and_save", side_effect=RuntimeError("boom")):
                    assert auth_cmd.attempt_auto_login() is False


class TestResolveCookies:
    def test_valid_session_needs_no_refresh(self):
        with patch.object(cli_mod, "load_cookies", return_value="ck"):
            with patch.object(cli_mod, "check_token_expiry", return_value=None):
                with patch.object(auth_cmd, "attempt_auto_login") as auto:
                    assert cli_mod._resolve_cookies() == "ck"
        auto.assert_not_called()

    def test_expired_session_refreshes_and_retries(self):
        # First expiry check raises; refresh succeeds; reload + re-check passes.
        with patch.object(cli_mod, "load_cookies", side_effect=["stale", "fresh"]):
            with patch.object(
                cli_mod, "check_token_expiry", side_effect=[CookieExpiredError("old"), None]
            ):
                with patch.object(auth_cmd, "attempt_auto_login", return_value=True):
                    assert cli_mod._resolve_cookies() == "fresh"

    def test_failed_refresh_tells_user_to_login_interactively(self):
        with patch.object(cli_mod, "load_cookies", side_effect=CookieNotFoundError("none")):
            with patch.object(auth_cmd, "attempt_auto_login", return_value=False):
                with pytest.raises(CookieNotFoundError) as exc:
                    cli_mod._resolve_cookies()
        assert "dw login" in str(exc.value)
        assert "browser window will open" in str(exc.value)
