"""Progress summary view."""

import click

from ..errors import handle_errors
from ..formatting import get_format, output, progress_bar, section
from ..parser import parse_progress


@click.command()
@click.pass_context
@handle_errors
def progress(ctx):
    """Show degree progress summary."""
    client = ctx.obj["client_factory"]()
    student_id = ctx.obj["student_id"]
    raw = client.get_audit(student_id)

    prog = parse_progress(raw)

    if get_format() == "json":
        output(prog)
        return

    section("Degree Progress")
    click.echo(f"  GPA: {prog['gpa']}")
    click.echo(f"  Credits: {prog['credits_applied']} / {prog['credits_needed']}")
    click.echo()

    pct = float(prog["percent_complete"]) if prog["percent_complete"] else 0
    progress_bar("Overall", pct)
    click.echo()

    for block in prog["blocks"]:
        bpct = float(block["percent"]) if block["percent"] else 0
        progress_bar(block["title"], bpct)
