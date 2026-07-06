"""No-network tests for `dw doctor`.

Auth is mocked so no cookies, browser, or network are touched. Verifies the
check set, the failure path (no session), and that a live-API success path
reports ready.
"""

from __future__ import annotations

import time
from unittest.mock import patch

from click.testing import CliRunner

from degreeworks.commands import doctor as doctor_mod
from degreeworks.commands.doctor import doctor
from degreeworks.errors import CookieNotFoundError


def _check_names(checks):
    return [c["check"] for c in checks]


def test_checks_cover_install_auth_and_api():
    with patch.object(doctor_mod, "load_cookies", side_effect=CookieNotFoundError("no cookies")):
        checks = doctor_mod._run_checks()
    names = _check_names(checks)
    for expected in ("cli", "path", "playwright", "config", "session", "token", "api"):
        assert expected in names


def test_no_session_fails_token_and_skips_api():
    with patch.object(doctor_mod, "load_cookies", side_effect=CookieNotFoundError("no cookies")):
        checks = doctor_mod._run_checks()
    by_name = {c["check"]: c for c in checks}
    assert by_name["token"]["ok"] is False
    assert by_name["token"]["next_step"] == "dw login"
    assert by_name["api"]["ok"] is False
    assert "Skipped" in by_name["api"]["detail"]


def test_doctor_command_exits_nonzero_when_unauthenticated():
    runner = CliRunner()
    with patch.object(doctor_mod, "load_cookies", side_effect=CookieNotFoundError("no cookies")):
        result = runner.invoke(doctor)
    assert result.exit_code == 1
    assert "dw login" in result.output


def test_doctor_reports_ready_on_live_api_success():
    future = time.time() + 3600
    fake_info = {"student_id": "900000000", "name": "Test Owl", "expires": future}
    with patch.object(doctor_mod, "load_cookies", return_value="X-AUTH-TOKEN=..."):
        with patch.object(doctor_mod, "get_student_info", return_value=fake_info):
            with patch.object(doctor_mod, "make_session", return_value=object()):
                with patch.object(
                    doctor_mod.DegreeworksClient, "get_audit", return_value={"header": {}}
                ):
                    checks = doctor_mod._run_checks()
    by_name = {c["check"]: c for c in checks}
    assert by_name["token"]["ok"] is True
    assert by_name["api"]["ok"] is True
    required_failed = [c for c in checks if not c["ok"] and not c["info_only"]]
    assert required_failed == []
