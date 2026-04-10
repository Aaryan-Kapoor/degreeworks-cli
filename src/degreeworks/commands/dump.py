"""AI agent snapshot – everything in one shot."""

import json

import click

from ..errors import handle_errors
from ..formatting import get_format, set_format
from ..parser import (
    parse_blocks,
    parse_completed,
    parse_header,
    parse_in_progress,
    parse_progress,
    parse_remaining,
)


@click.command()
@click.option("--shallow", is_flag=True, help="Quick overview only (progress + in-progress)")
@click.pass_context
@handle_errors
def dump(ctx, shallow):
    """Dump full academic snapshot for AI agents.

    Best used with --md or --json flag:
        dw --md dump
        dw --json dump
    """
    client = ctx.obj["client_factory"]()
    student_id = ctx.obj["student_id"]
    raw = client.get_audit(student_id)

    fmt = get_format()

    if fmt == "json":
        snapshot = _build_snapshot(raw, shallow)
        click.echo(json.dumps(snapshot, indent=2))
        return

    # Force markdown for dump if not already set
    if fmt == "human":
        set_format("md")

    _dump_md(raw, shallow)


def _build_snapshot(audit: dict, shallow: bool) -> dict:
    """Build structured JSON snapshot."""
    header = parse_header(audit)
    progress = parse_progress(audit)
    in_progress = parse_in_progress(audit)

    snapshot = {
        "student": header,
        "progress": progress,
        "in_progress": in_progress,
    }

    if not shallow:
        snapshot["completed"] = parse_completed(audit)
        snapshot["remaining"] = parse_remaining(audit)
        snapshot["blocks"] = parse_blocks(audit)

    return snapshot


def _dump_md(audit: dict, shallow: bool):
    """Print markdown snapshot."""
    header = parse_header(audit)
    progress = parse_progress(audit)
    in_progress = parse_in_progress(audit)

    click.echo(f"# DegreeWorks Audit – {header['name']}")
    click.echo(f"\n**Student ID**: {header['student_id']}")
    click.echo(f"**GPA**: {header['gpa']}")
    click.echo(f"**Degree Progress**: {header['percent_complete']}%")
    click.echo(f"**Credits**: {progress['credits_applied']} / {progress['credits_needed']}")

    click.echo("\n## Progress by Requirement")
    for block in progress["blocks"]:
        pct = float(block["percent"]) if block["percent"] else 0
        marker = "x" if pct >= 100 else " "
        click.echo(f"- [{marker}] {block['title']}: {pct:.0f}%")

    if in_progress:
        click.echo("\n## Currently In Progress")
        click.echo("| Course | Title | Credits | Term |")
        click.echo("| --- | --- | --- | --- |")
        for c in in_progress:
            click.echo(f"| {c['course']} | {c['title']} | {c['credits']} | {c['term_label']} |")

    if shallow:
        return

    # Completed courses
    completed = parse_completed(audit)
    done = [c for c in completed if not c["in_progress"]]
    if done:
        click.echo("\n## Completed Courses")
        click.echo("| Course | Title | Credits | Grade | Term |")
        click.echo("| --- | --- | --- | --- | --- |")
        for c in done:
            click.echo(
                f"| {c['course']} | {c['title']} | {c['credits']} | {c['grade']} | {c['term_label']} |"
            )

    # Remaining
    remaining = parse_remaining(audit)
    course_items = [c for c in remaining if c.get("course")]
    text_items = [c for c in remaining if not c.get("course") and c.get("text")]

    if course_items or text_items:
        click.echo("\n## Remaining Requirements")

    if course_items:
        click.echo("| Course | Title | Credits | Prereqs? | Requirement |")
        click.echo("| --- | --- | --- | --- | --- |")
        for c in course_items:
            prereq = "Yes" if c.get("has_prereqs") else ""
            click.echo(
                f"| {c['course']} | {c.get('title', '')} | {c.get('credits', '')} | {prereq} | {c['rule_label']} |"
            )

    if text_items:
        click.echo()
        for item in text_items:
            click.echo(f"- **{item['rule_label']}**: {item['text']}")
