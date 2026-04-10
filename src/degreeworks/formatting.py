"""Output engine: human tables, JSON, and markdown."""

import json

import click

_format = "human"


def set_format(fmt: str):
    global _format
    _format = fmt


def get_format() -> str:
    return _format


def output(data):
    """Print data in the current format."""
    if _format == "json":
        click.echo(json.dumps(data, indent=2))
    elif _format == "md":
        if isinstance(data, str):
            click.echo(data)
        elif isinstance(data, dict):
            for k, v in data.items():
                click.echo(f"- **{k}**: {v}")
        elif isinstance(data, list):
            for item in data:
                click.echo(f"- {item}")
        else:
            click.echo(str(data))
    else:
        if isinstance(data, str):
            click.echo(data)
        elif isinstance(data, dict):
            for k, v in data.items():
                click.echo(f"  {k}: {v}")
        elif isinstance(data, list):
            for item in data:
                click.echo(f"  {item}")


def section(title: str, content: str = ""):
    """Print a section header."""
    if _format == "md":
        click.echo(f"\n## {title}\n")
    else:
        click.echo(f"\n{'=' * 60}")
        click.echo(f"  {title}")
        click.echo(f"{'=' * 60}")
    if content:
        click.echo(content)


def subsection(title: str):
    if _format == "md":
        click.echo(f"\n### {title}\n")
    else:
        click.echo(f"\n  --- {title} ---")


def table(rows: list[dict], columns: list[tuple[str, str]]):
    """Print a table.

    columns: list of (header, key) tuples.
    """
    if not rows:
        click.echo("  (none)")
        return

    if _format == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    if _format == "md":
        # Markdown table
        headers = [c[0] for c in columns]
        click.echo("| " + " | ".join(headers) + " |")
        click.echo("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            vals = [str(row.get(c[1], "")) for c in columns]
            click.echo("| " + " | ".join(vals) + " |")
        return

    # Human-readable aligned table
    widths = []
    for header, key in columns:
        col_width = len(header)
        for row in rows:
            col_width = max(col_width, len(str(row.get(key, ""))))
        widths.append(col_width)

    # Header
    header_line = "  ".join(h.ljust(w) for (h, _), w in zip(columns, widths))
    click.echo(f"  {header_line}")
    click.echo(f"  {'  '.join('-' * w for w in widths)}")

    # Rows
    for row in rows:
        vals = [str(row.get(key, "")).ljust(w) for (_, key), w in zip(columns, widths)]
        click.echo(f"  {'  '.join(vals)}")


def progress_bar(label: str, percent: float, width: int = 30):
    """Print a text-based progress bar."""
    if _format == "md":
        click.echo(f"- **{label}**: {percent:.0f}%")
        return
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    click.echo(f"  {label:.<40s} [{bar}] {percent:.0f}%")
