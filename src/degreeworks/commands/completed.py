"""Completed courses view."""

import click

from ..errors import handle_errors
from ..formatting import get_format, output, section, table
from ..parser import parse_completed


@click.command()
@click.option("--transfers", is_flag=True, help="Include transfer credits")
@click.pass_context
@handle_errors
def completed(ctx, transfers):
    """Show completed and in-progress courses."""
    client = ctx.obj["client_factory"]()
    student_id = ctx.obj["student_id"]
    raw = client.get_audit(student_id)

    courses = parse_completed(raw)

    if not transfers:
        courses = [c for c in courses if not c["transfer"]]

    if get_format() == "json":
        output(courses)
        return

    section("Completed & In-Progress Courses")

    # Group by term
    by_term: dict[str, list] = {}
    for c in courses:
        key = c["term_label"] or "Unknown"
        by_term.setdefault(key, []).append(c)

    for term_label, term_courses in by_term.items():
        click.echo(f"\n  {term_label}:")
        table(
            term_courses,
            [
                ("Course", "course"),
                ("Title", "title"),
                ("Cr", "credits"),
                ("Grade", "grade"),
            ],
        )
