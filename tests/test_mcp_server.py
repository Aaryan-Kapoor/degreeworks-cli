"""Smoke tests for the MCP server surface.

These run without network, cookies, Playwright, or a `dw login` — they
exercise the parts of the server that are deterministic: tool/prompt
registration, the single-source protocol prompt, and the error message
shown when the `dw` CLI is missing.

The MCP SDK methods are async; we drive them with asyncio.run() so the
only test dependency is pytest (no pytest-asyncio needed).
"""

from __future__ import annotations

import asyncio

import pytest

from degreeworks import mcp_server
from degreeworks._protocol import SCHEDULE_PLANNING_PROTOCOL
from mcp.server.fastmcp.exceptions import ToolError

EXPECTED_TOOLS = {
    "whoami",
    "progress",
    "remaining",
    "completed",
    "audit",
    "course",
    "dump",
}


def test_all_tools_registered_with_descriptions():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS
    # Every tool description is what the LLM sees in tools/list — none may be empty.
    assert all((t.description or "").strip() for t in tools)


def test_plan_semester_prompt_is_single_source():
    prompts = asyncio.run(mcp_server.mcp.list_prompts())
    assert [p.name for p in prompts] == ["plan_semester"]

    result = asyncio.run(mcp_server.mcp.get_prompt("plan_semester", {}))
    rendered = result.messages[0].content.text
    # The prompt must be byte-equal to the constant: one source of truth.
    assert rendered == SCHEDULE_PLANNING_PROTOCOL
    # And it must actually contain the 8-phase structure agents rely on.
    for phase in range(9):  # Phase 0 through Phase 8
        assert f"Phase {phase}" in rendered


def test_missing_cli_error_names_the_right_package(monkeypatch):
    """When `dw` is not on PATH, the error must point at the real package.

    Guards against regressing the install hint back to the pre-rebrand
    `degreeworks-cli` name or a non-existent extra.
    """
    monkeypatch.setattr(mcp_server, "DW_PATH", None)
    with pytest.raises(ToolError) as exc:
        asyncio.run(mcp_server._run_dw("--md", "whoami"))
    msg = str(exc.value)
    assert 'pip install "degreeworks-mcp[login]"' in msg
    assert "degreeworks-cli" not in msg
