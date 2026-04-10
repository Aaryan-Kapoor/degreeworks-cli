"""Full audit view."""

import click

from ..errors import handle_errors
from ..formatting import output, section, subsection, table, progress_bar, get_format
from ..parser import parse_header, parse_blocks


@click.command()
@click.pass_context
@handle_errors
def audit(ctx):
    """Show the full degree audit."""
    client = ctx.obj["client_factory"]()
    student_id = ctx.obj["student_id"]
    raw = client.get_audit(student_id)

    if get_format() == "json":
        output(raw)
        return

    header = parse_header(raw)
    blocks = parse_blocks(raw)

    section(f"Degree Audit – {header['name']}")
    output({
        "Student ID": header["student_id"],
        "GPA": header["gpa"],
        "Progress": f"{header['percent_complete']}%",
        "Credits Applied": header["credits_applied"],
    })

    for block in blocks:
        if block["type"] == "DEGREE":
            continue

        pct = float(block["percent_complete"]) if block["percent_complete"] else 0
        subsection(f"{block['title']} ({pct:.0f}%)")

        for rule in block["rules"]:
            _print_rule(rule, indent=1)


def _print_rule(rule: dict, indent: int = 0):
    """Print a single rule and its sub-rules."""
    prefix = "  " * indent
    pct = rule["percent_complete"]
    label = rule["label"]
    if not label:
        return

    try:
        pct_f = float(pct)
    except (ValueError, TypeError):
        pct_f = 0

    # Status indicator
    if pct_f >= 100:
        status = "DONE"
    elif rule["in_progress"]:
        status = "IP"
    elif pct_f > 0:
        status = f"{pct_f:.0f}%"
    else:
        status = "NEED"

    fmt = get_format()
    if fmt == "md":
        marker = "x" if pct_f >= 100 else " "
        click.echo(f"{prefix}- [{marker}] **{label}** [{status}]")
    else:
        click.echo(f"{prefix}  [{status:>4s}] {label}")

    # Show applied courses
    for c in rule["courses_applied"]:
        grade_str = c.get("grade") or ""
        if grade_str == "REGD":
            grade_str = "In Progress"
        credits = c.get("credits") or "?"
        course = c.get("course") or ""
        term_label = c.get("term_label") or ""
        if fmt == "md":
            click.echo(f"{prefix}  - {course} ({credits}cr) – {grade_str}, {term_label}")
        else:
            click.echo(f"{prefix}         ✓ {course:.<20s} {credits:>3s}cr  {grade_str:<12s} {term_label}")

    # Show needed courses
    for c in rule["courses_needed"]:
        title = f" – {c['title']}" if c.get("title") else ""
        credits = c.get("credits") or "?"
        course = c.get("course") or ""
        if fmt == "md":
            click.echo(f"{prefix}  - **NEED**: {course}{title} ({credits}cr)")
        else:
            click.echo(f"{prefix}         ✗ {course:.<20s} {credits:>3s}cr  {title}")

    # Proxy advice
    if rule.get("proxy_advice"):
        if fmt == "md":
            click.echo(f"{prefix}  > {rule['proxy_advice']}")
        else:
            click.echo(f"{prefix}         → {rule['proxy_advice']}")

    for sub in rule["sub_rules"]:
        _print_rule(sub, indent + 1)
