"""Course info lookup."""

import click

from ..errors import handle_errors
from ..formatting import get_format, output, section, subsection, table


CAMPUS_MAP = {
    "M": "Marietta",
    "K": "Kennesaw",
    "O": "Online",
    "D": "Distance",
}


def _format_time(hhmm: str) -> str:
    """Convert '1700' to '5:00 PM'."""
    if not hhmm or len(hhmm) != 4:
        return ""
    hour = int(hhmm[:2])
    minute = hhmm[2:]
    period = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 or 12
    return f"{hour_12}:{minute} {period}"


def _format_days(meeting: dict) -> str:
    """Build 'MWF' or 'TR' style day string from meeting fields."""
    day_map = [
        ("monday", "M"),
        ("tuesday", "T"),
        ("wednesday", "W"),
        ("thursday", "R"),
        ("friday", "F"),
        ("saturday", "S"),
        ("sunday", "U"),
    ]
    return "".join(code for key, code in day_map if meeting.get(key))


def _format_prereqs(prereqs: list) -> str:
    """Convert structured prereqs into a readable logical expression.

    Each prereq entry has connector (A/O), leftParenthesis, rightParenthesis,
    and either a course (subjectCodePrerequisite + courseNumberPrerequisite)
    or a test (tescCode + testScore).
    """
    parts = []
    for p in prereqs:
        token = ""
        if p.get("subjectCodePrerequisite"):
            token = f"{p['subjectCodePrerequisite']} {p['courseNumberPrerequisite']}"
            if p.get("minimumGrade"):
                token += f" (min {p['minimumGrade']})"
        elif p.get("tescCode"):
            token = f"{p['tescCode']}={p.get('testScore', '')}"

        connector = p.get("connector", "")
        left = p.get("leftParenthesis", "")
        right = p.get("rightParenthesis", "")

        prefix = ""
        if connector == "A":
            prefix = " AND "
        elif connector == "O":
            prefix = " OR "

        parts.append(f"{prefix}{left}{token}{right}")

    return "".join(parts).strip()


def _format_section(section: dict) -> dict:
    """Flatten a section + its first meeting into a display-ready row."""
    meetings = section.get("meetings", [])
    meeting = meetings[0] if meetings else {}

    days = _format_days(meeting)
    begin = _format_time(meeting.get("beginTime", ""))
    end = _format_time(meeting.get("endTime", ""))
    time_str = f"{begin}-{end}" if begin and end else ""

    building = meeting.get("buildingCode", "")
    room = meeting.get("roomCode", "")
    location = f"{building} {room}".strip() if building or room else ""

    campus_code = section.get("campusCode", "")
    campus = CAMPUS_MAP.get(campus_code, campus_code)

    enrollment = section.get("enrollment", "0")
    max_enroll = section.get("maximumEnrollment", "0")

    return {
        "term": section.get("termLiteral", ""),
        "crn": section.get("courseReferenceNumber", ""),
        "seq": section.get("sequenceNumber", ""),
        "days": days,
        "time": time_str,
        "location": location,
        "instructor": meeting.get("funcCode", "").strip(),
        "campus": campus,
        "enrolled": f"{enrollment}/{max_enroll}",
        "waitlist": section.get("waitCount", "0"),
    }


@click.command()
@click.argument("discipline")
@click.argument("number")
@click.pass_context
@handle_errors
def course(ctx, discipline, number):
    """Look up course info: prereqs, sections, schedules.

    Example: dw course CS 3305
    """
    client = ctx.obj["client_factory"]()
    raw = client.get_course(discipline.upper(), number)

    if get_format() == "json":
        output(raw)
        return

    courses = raw.get("courseInformation", {}).get("courses", [])
    if not courses:
        click.echo(f"  No course found: {discipline.upper()} {number}")
        return

    for c in courses:
        subject = c.get("subjectCode", "")
        num = c.get("courseNumber", "")
        title = c.get("title", "")
        credits_low = c.get("creditHourLow", "")
        credits_high = c.get("creditHourHigh", "")
        credits = credits_low
        if credits_high and credits_high != credits_low:
            credits = f"{credits_low}-{credits_high}"

        section(f"{subject} {num} – {title}")
        click.echo(f"  Credits: {credits}")

        # Description
        desc_lines = c.get("description", [])
        desc = " ".join(l.strip() for l in desc_lines if l.strip())
        if desc:
            click.echo(f"\n  {desc}")

        # Prerequisites
        prereqs = c.get("prerequisites", [])
        if prereqs:
            prereq_str = _format_prereqs(prereqs)
            if prereq_str:
                click.echo(f"\n  Prerequisites: {prereq_str}")

        # Sections
        sections_raw = c.get("sections", [])
        if sections_raw:
            subsection(f"Available Sections ({len(sections_raw)})")
            rows = [_format_section(s) for s in sections_raw]
            table(
                rows,
                [
                    ("Term", "term"),
                    ("CRN", "crn"),
                    ("Days", "days"),
                    ("Time", "time"),
                    ("Location", "location"),
                    ("Instructor", "instructor"),
                    ("Campus", "campus"),
                    ("Enrolled", "enrolled"),
                ],
            )
        else:
            click.echo("\n  No sections available.")
