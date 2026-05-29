"""DegreeWorks MCP server.

Exposes the read-only `dw` CLI as MCP tools and prompts so any MCP-speaking
agent (Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Continue, Gemini
CLI, etc.) can query KSU DegreeWorks data directly. This is the default
install route — students add one JSON snippet to their client config and
their agent gets `whoami`, `progress`, `remaining`, `completed`, `audit`,
`course`, `dump`, and a deterministic `plan_semester` prompt.

Design: the server shells out to the existing `dw` CLI. There is no
Playwright, no HTTP logic, and no audit parsing duplicated here — the
CLI stays canonical. Keeping Playwright in the CLI (where `dw login` runs
in a real terminal with a real display) avoids GUI-subprocess fragility
that breaks sandboxed MCP clients like Claude Desktop on macOS.

Auth: the server reads cookies from `~/.degreeworks/cookies.txt`, populated
by running `dw login` once in a terminal. When the session is expired,
the `whoami` tool reports it and the agent should tell the student to
run `dw login` again.

Stdio transport notes: MCP stdio uses stdout as the JSON-RPC channel. All
logging must go to stderr. Never `print()` in this module or any code it
imports at the top level.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ._protocol import SCHEDULE_PLANNING_PROTOCOL

# Logging MUST go to stderr. Any byte on stdout that isn't valid JSON-RPC
# corrupts the stream and the client disconnects with a parse error.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s degreeworks-mcp: %(message)s",
)
log = logging.getLogger("degreeworks-mcp")

mcp = FastMCP("degreeworks")

# Resolve the `dw` CLI absolute path at startup. Claude Desktop on macOS
# launches MCP servers with a stripped PATH (typically /usr/bin:/bin), so
# PATH lookup at tool-call time is unreliable. Resolving once at import
# means one clear failure mode if the CLI is missing, not a mysterious
# failure on the tenth call.
DW_PATH = shutil.which("dw")

# 30s is generous — every dw command is a single HTTP request plus parsing.
# A hung subprocess (e.g., waiting on an expired auth redirect) should
# fail fast rather than hang the MCP server indefinitely.
DEFAULT_TIMEOUT = 30.0


async def _run_dw(*args: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Run `dw <args>` and return stdout. Raises ToolError on any failure.

    Uses asyncio.create_subprocess_exec so the event loop is not blocked
    if the server is handling concurrent tool calls. Synchronous
    `subprocess.run` would serialize everything and can silently deadlock.
    """
    if DW_PATH is None:
        raise ToolError(
            "The `dw` CLI is not installed or not on PATH. "
            'Install with: pip install "degreeworks-mcp[login]"  '
            "Then run `dw login` in a terminal to authenticate. "
            "If installed via uvx/pipx, ensure the install location is on "
            "PATH, or set an absolute `command` path in your MCP client config."
        )

    log.info("run: dw %s", " ".join(args))
    proc = await asyncio.create_subprocess_exec(
        DW_PATH,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ToolError(
            f"`dw {' '.join(args)}` timed out after {timeout:.0f}s. "
            "This usually means the DegreeWorks API is slow or unreachable. "
            "Retry in a minute; if it persists, check https://degreeworks.kennesaw.edu in a browser."
        )

    stdout = stdout_b.decode("utf-8", errors="replace").strip()
    stderr = stderr_b.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        # Surface the dw CLI's own error message verbatim. For auth failures
        # this is "Session fully expired (both auth and refresh tokens). Run
        # `dw login` to re-authenticate with KSU SSO." which the agent can
        # relay to the student unchanged.
        msg = stderr or stdout or f"dw exited with code {proc.returncode}"
        log.warning("dw failed: %s", msg)
        raise ToolError(msg)

    return stdout


# ---------- Tools ----------


@mcp.tool()
async def whoami() -> str:
    """Verify DegreeWorks auth status. Returns student name, ID, token expiry, time remaining, and ACTIVE/EXPIRED status. Call this FIRST before any other tool in a session. If status is EXPIRED, tell the student to run `dw login` in a terminal and stop — the MCP server cannot perform SSO login.

    This tool works even when the session is fully expired (it reads cookie contents, no API call)."""
    return await _run_dw("--md", "whoami")


@mcp.tool()
async def progress() -> str:
    """Show the student's degree progress: overall completion percentage, GPA, credits applied, and progress bars for every requirement block (State Legislative, each Gen Ed area, Honors if applicable, Major, etc.). Use for a quick high-level snapshot; for the full state use `dump`."""
    return await _run_dw("--md", "progress")


@mcp.tool()
async def remaining() -> str:
    """List every course the student still needs for graduation. Includes both specific course requirements and free-text requirements like "Complete 9 credits of CS 3000-4000 level coursework". Each row shows course code, title, credit hours, whether prerequisites exist, and which requirement the course satisfies. This is the input to Phase 3 of the Schedule Planning Protocol."""
    return await _run_dw("--md", "remaining")


@mcp.tool()
async def completed(include_transfers: bool = False) -> str:
    """List all completed and in-progress courses grouped by term. Each row shows code, title, credits, grade (REGD = registered/in-progress), and term.

    Args:
        include_transfers: When True, also include transfer credits from other institutions. Default False (KSU courses only)."""
    args = ["--md", "completed"]
    if include_transfers:
        args.append("--transfers")
    return await _run_dw(*args)


@mcp.tool()
async def audit() -> str:
    """Show the full degree audit tree with nested rules. Use when you need to understand WHY a specific course counts toward a specific requirement, or to see the complete structure of the degree plan (every requirement block, every sub-rule, per-rule status DONE/IP/NEED/percentage, applied courses, and needed courses).

    For most schedule-planning tasks, `dump` is more useful. Reach for `audit` only when rule-level detail matters."""
    return await _run_dw("--md", "audit")


@mcp.tool()
async def course(discipline: str, number: str) -> str:
    """Look up a specific course: description, prerequisites as a parsed boolean expression, and every scheduled section for upcoming terms (term, CRN, days, time, building/room, instructor, campus, enrollment, waitlist).

    Example prerequisite output:
    `((MATH 2345 (min C) OR CSE 2300 (min C)) AND (CSE 1322 (min C) AND CSE 1322L (min C)))`

    This is the verification tool in Phase 4 of the Schedule Planning Protocol — call it for EVERY candidate course before adding it to a plan. Never recall prereqs or section availability from memory; the catalog changes between terms.

    Args:
        discipline: Course discipline/prefix, e.g. "CS", "MATH", "HIST".
        number: Course number, e.g. "3305", "2202", "2112"."""
    return await _run_dw("--md", "course", discipline, number)


@mcp.tool()
async def dump(shallow: bool = False) -> str:
    """Get a full academic snapshot in one call: student info, degree progress, in-progress courses, completed courses, and remaining requirements. This is Phase 1 of the Schedule Planning Protocol — the ground truth that every other phase builds on.

    Args:
        shallow: When True, return only progress + in-progress courses (quick orientation). Default False (full snapshot)."""
    args = ["--md", "dump"]
    if shallow:
        args.append("--shallow")
    return await _run_dw(*args)


# ---------- Prompts ----------


@mcp.prompt()
def plan_semester() -> str:
    """The deterministic 8-phase Schedule Planning Protocol. Invoke this prompt at the start of any schedule planning conversation to load the full protocol into context. Use when the student asks you to plan a semester, pick courses, or build a schedule — not for simple informational queries like "what's my GPA?" """
    return SCHEDULE_PLANNING_PROTOCOL


# ---------- Entry point ----------


def main() -> None:
    """Console script entry point: `degreeworks-mcp`."""
    log.info("degreeworks-mcp starting (dw path: %s)", DW_PATH or "NOT FOUND")
    mcp.run()


if __name__ == "__main__":
    main()
