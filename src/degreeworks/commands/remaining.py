"""Remaining requirements view."""

import click

from ..errors import handle_errors
from ..formatting import get_format, output, section, table
from ..parser import parse_remaining


@click.command()
@click.pass_context
@handle_errors
def remaining(ctx):
    """Show remaining courses needed for graduation."""
    client = ctx.obj["client_factory"]()
    student_id = ctx.obj["student_id"]
    raw = client.get_audit(student_id)

    courses = parse_remaining(raw)

    if get_format() == "json":
        output(courses)
        return

    section("Remaining Requirements")

    # Separate actual courses from text-only advice
    course_items = [c for c in courses if c.get("course")]
    text_items = [c for c in courses if not c.get("course") and c.get("text")]

    # Normalize bool → Yes/empty for display
    for c in course_items:
        c["prereqs_display"] = "Yes" if c.get("has_prereqs") else ""

    if course_items:
        table(
            course_items,
            [
                ("Course", "course"),
                ("Title", "title"),
                ("Cr", "credits"),
                ("Prereqs?", "prereqs_display"),
                ("Requirement", "rule_label"),
            ],
        )

    if text_items:
        click.echo()
        for item in text_items:
            fmt = get_format()
            if fmt == "md":
                click.echo(f"- **{item['rule_label']}**: {item['text']}")
            else:
                click.echo(f"  [{item['rule_label']}] {item['text']}")
