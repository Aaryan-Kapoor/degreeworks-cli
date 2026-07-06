"""Smoke tests for the bundled agent skill and `dw skill install`.

No network. Verifies the skill files ship inside the package (package-data
wiring) and that install copies them into a target directory.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from degreeworks.commands.skill_cmd import _skill_root, skill


def test_bundled_skill_files_present():
    root = _skill_root()
    assert (root / "SKILL.md").is_file()
    assert (root / "references" / "commands.md").is_file()
    assert (root / "references" / "safety.md").is_file()


def test_skill_md_is_self_contained():
    # The bundled skill must not point at the repo's AGENTS.md — a pip-installed
    # skill has no repo checkout to reach.
    text = (_skill_root() / "SKILL.md").read_text()
    assert "AGENTS.md" not in text
    assert "Schedule Planning Protocol" in text
    assert "read-only" in text.lower()


def test_skill_install_copies_files_and_refuses_overwrite():
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "degreeworks"

        result = runner.invoke(skill, ["install", str(target)])
        assert result.exit_code == 0, result.output
        assert (target / "SKILL.md").is_file()
        assert (target / "references" / "safety.md").is_file()

        # Second install without --force fails cleanly.
        again = runner.invoke(skill, ["install", str(target)])
        assert again.exit_code != 0
        assert "--force" in again.output

        # With --force it succeeds.
        forced = runner.invoke(skill, ["install", str(target), "--force"])
        assert forced.exit_code == 0, forced.output


def test_skill_cat_prints_skill_md():
    runner = CliRunner()
    result = runner.invoke(skill, ["cat"])
    assert result.exit_code == 0
    assert "DegreeWorks" in result.output
