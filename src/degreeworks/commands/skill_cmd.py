"""`dw skill` — manage the bundled agent skill (SKILL.md + references)."""

from importlib.resources import files
from pathlib import Path

import click

from ..errors import DegreeworksError, handle_errors


def _skill_root():
    root = files("degreeworks") / "data" / "skill"
    if not root.is_dir():
        raise DegreeworksError("Bundled skill files not found in this installation.")
    return root


def _walk(traversable, rel=""):
    for entry in traversable.iterdir():
        entry_rel = f"{rel}/{entry.name}" if rel else entry.name
        if entry.is_dir():
            yield from _walk(entry, entry_rel)
        else:
            yield entry_rel, entry


@click.group()
def skill():
    """Manage the bundled agent skill (SKILL.md + references).

    The skill teaches any agent system (Claude Code, OpenClaw, Codex, etc.)
    how to use this CLI and how to run the schedule-planning protocol. It
    ships inside the package, so it is available from any pip/pipx install —
    no repo checkout needed.
    """


@skill.command("install")
@click.argument("target_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--force", is_flag=True, help="Overwrite existing files in TARGET_DIR")
@handle_errors
def skill_install(target_dir, force):
    """Copy the bundled skill into TARGET_DIR (e.g. ~/.claude/skills/degreeworks).

    Examples:
      dw skill install ~/.claude/skills/degreeworks   # Claude Code (user)
      dw skill install .claude/skills/degreeworks     # Claude Code (project)
      dw skill install ~/.agents/skills/degreeworks   # OpenClaw (personal)
    """
    root = _skill_root()
    entries = list(_walk(root))

    existing = [rel for rel, _ in entries if (target_dir / rel).exists()]
    if existing and not force:
        raise DegreeworksError(
            f"{target_dir} already contains skill files ({existing[0]}, ...). "
            "Re-run with --force to overwrite."
        )

    for rel, entry in entries:
        dest = target_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(entry.read_bytes())
        click.echo(f"  {dest}")
    click.echo(f"Installed degreeworks skill ({len(entries)} files) to {target_dir}")


@skill.command("cat")
@handle_errors
def skill_cat():
    """Print the bundled SKILL.md to stdout."""
    click.echo((_skill_root() / "SKILL.md").read_text())
