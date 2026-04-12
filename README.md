<div align="center">
  <img src="banner.svg" alt="degreeworks-mcp" width="720"/>
</div>

<p align="center">
  <strong>Read-only DegreeWorks MCP server for KSU – built for AI agents to plan student schedules.</strong><br/>
  <em>Plans schedules good enough to pass advisor review<a href="#advisor-note">*</a>.</em>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#mcp-client-config">MCP Client Config</a> ·
  <a href="#tools">Tools</a> ·
  <a href="#how-it-works">How it works</a>
</p>

---

`degreeworks-mcp` is a strictly **read-only** Model Context Protocol server that pulls a KSU student's DegreeWorks degree audit and course catalog. Drop one JSON snippet into your MCP client (Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Continue, Gemini CLI) and your agent gets 7 tools plus a deterministic 8-phase Schedule Planning Protocol prompt — no project files, no per-tool config.

It is designed to be used by AI agents, not humans.

## Features

- **MCP server** for any MCP-speaking client — 7 read-only tools (`whoami`, `progress`, `remaining`, `completed`, `audit`, `course`, `dump`) and a `plan_semester` prompt over stdio
- **Deterministic 8-phase Schedule Planning Protocol** baked into the `plan_semester` prompt, designed for reliability across different LLMs
- **One-time browser login** via KSU SSO (Playwright); after that, the MCP server reads cookies from disk and never touches a browser
- **Course detail with parsed boolean prereqs** — `((MATH 2345 (min C) OR CSE 2300 (min C)) AND CSE 1322 (min C))` — plus every scheduled section with days, times, CRNs, instructors, seats
- **Strictly read-only.** No POST/PUT/DELETE methods exist in the underlying client, by design. The server cannot register, drop, or modify anything.

## Quickstart

```bash
pip install "degreeworks-mcp[login]"
playwright install chromium
dw login                              # one-time browser SSO in your terminal
```

Add the MCP server to your client (per-client config paths in [the table below](#mcp-client-config)):

```json
{ "mcpServers": { "degreeworks": { "command": "degreeworks-mcp" } } }
```

Restart your MCP client and ask your agent to plan a semester. It will load the `plan_semester` prompt and follow the 8-phase protocol.

Cookies last 90 minutes (auth token) / 8 hours (refresh token). When the auth token expires the agent will tell you to run `dw login --headless` in a terminal; when the refresh token expires too, run `dw login` for a fresh interactive SSO. **All you need a terminal for is `dw login`** — every other interaction goes through your MCP client.

## MCP Client Config

The same JSON works for almost every client. Drop this into the right config file:

| Client | Config file |
|---|---|
| **Claude Desktop** (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Claude Desktop** (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Claude Code** (per-project) | `.mcp.json` at the repo root, or `claude mcp add degreeworks -- degreeworks-mcp` |
| **Cursor** (global) | `~/.cursor/mcp.json` |
| **Cursor** (project) | `.cursor/mcp.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **Continue** | `.continue/config.yaml` (under `mcpServers:`) |
| **Zed** | `settings.json` under `"context_servers"` (Zed uses a different key) |

```json
{
  "mcpServers": {
    "degreeworks": {
      "command": "degreeworks-mcp"
    }
  }
}
```

If your client launches with a stripped PATH (Claude Desktop on macOS in particular), use the absolute path: `"command": "/path/to/your/venv/bin/degreeworks-mcp"` — find it with `which degreeworks-mcp`.

## Tools

Once the server is connected your agent has these tools:

| Tool | Purpose |
|---|---|
| `whoami` | Verify auth status (works even when expired) |
| `progress` | Degree progress bars by requirement area |
| `remaining` | All courses still needed for graduation |
| `completed(include_transfers=False)` | Completed and in-progress courses grouped by term |
| `audit` | Full nested audit tree with per-rule status |
| `course(discipline, number)` | Description, parsed prereqs, all scheduled sections |
| `dump(shallow=False)` | Full academic snapshot in one call |

Plus one **prompt**:

| Prompt | Purpose |
|---|---|
| `plan_semester` | Loads the deterministic 8-phase Schedule Planning Protocol into the conversation |

Each tool's full description, including which protocol phase it belongs to, is shipped in the MCP server itself — your client will display it when you list tools or hover over one. The MCP server is the single source of truth for what the agent sees; this README is for humans.

## The Schedule Planning Protocol

A deterministic **8-phase protocol** designed to produce reliable, reproducible plans across different LLMs, different users, and different conversations. When you ask an agent to plan a semester, it will:

1. **Verify auth** — call `whoami` to confirm cookies are live
2. **Gather ground truth** — call `dump` for the complete current state
3. **Gather constraints explicitly** — ask you for target terms, credit load, time window, days, campus, online cap, locked-in courses, graduation target (no assumed defaults)
4. **Identify candidates** — categorize every remaining course as Ready / Blocked / Free-text
5. **Verify each candidate with `course`** — prereqs, offering term, seats, schedule fit
6. **Draft the plan** — conflict-free, credit-load-compliant
7. **Validate against a checklist** — CRNs, conflicts, credits, prereq chains, all Phase 2 constraints
8. **Present with rationale, risks, and fallbacks** — then defer to your academic advisor for final sign-off

The protocol forces verification at every step instead of letting the model hallucinate prereqs or assume a course is offered. Full text lives in `src/degreeworks/_protocol.py` and is served as the `plan_semester` MCP prompt — an agent invokes it once at the start of a planning conversation to load the rules into context.

## Direct CLI use (alternative)

The MCP server is a wrapper around an underlying `dw` CLI. If your harness doesn't speak MCP yet (Codex, Aider, plain Copilot, JetBrains Junie), or you want a human terminal escape hatch, the same data is available via `dw` directly. See [`cli/README.md`](cli/README.md) for the CLI surface, install instructions, and command reference.

The CLI route is the same install (`pip install "degreeworks-mcp[login]"`); both `dw` and `degreeworks-mcp` console scripts come with the package.

## How it works

### MCP server

`src/degreeworks/mcp_server.py` is ~190 lines. It uses the `mcp` Python SDK's `FastMCP` high-level API to declare 7 tools and one prompt, then shells out to the underlying `dw` CLI via `asyncio.create_subprocess_exec` for every tool call. There is no HTTP code, no audit parsing, and no Playwright in the MCP server — it inherits all of that from the CLI underneath. This means:

- **One canonical code path** for auth, parsing, and output. A bug fix in the CLI is automatically a bug fix in the MCP server.
- **No GUI subprocesses inside MCP transport.** Spawning Chromium from a stdio MCP subprocess is fragile (sandboxed clients block it; headless containers have no display; remote SSH has no `$DISPLAY`). Keeping `dw login` as a terminal command gives one clear failure mode: "open a terminal and run `dw login`."
- **Errors surface verbatim.** When the underlying CLI exits non-zero, the server raises `ToolError` with the stderr — so when cookies expire, the agent sees `Session fully expired (both auth and refresh tokens). Run \`dw login\` to re-authenticate.` and can relay it to the student unchanged.
- **Logs go to stderr only.** Stdio MCP uses stdout for the JSON-RPC channel; any stray byte on stdout corrupts the connection. The server configures `logging.basicConfig(stream=sys.stderr, ...)` and never calls `print()`.

The 8-phase Schedule Planning Protocol is served via the `plan_semester` MCP prompt, defined in `src/degreeworks/_protocol.py`. That file is the single source of truth — there is no separate `AGENTS.md` to keep in sync.

### Auth bootstrap

DegreeWorks uses two JWT cookies:

- `X-AUTH-TOKEN` — 90 min, used for API calls
- `REFRESH_TOKEN` — 8 hr, used to refresh the auth token without re-logging in

`dw login` launches Chromium via Playwright with a persistent browser profile at `~/.degreeworks/browser_profile/`. You log in with KSU SSO normally. Playwright polls for the auth cookie to appear, captures all `degreeworks.kennesaw.edu` cookies, and intercepts the first `/api/audit` request to auto-detect your school (US) and degree (BS/BA/BBA/...) from the query params. Everything is saved to `~/.degreeworks/`.

Token expiry is checked **before** every API call so you get clear error messages instead of cryptic 401s. If the auth token is expired but the refresh token is alive, the server tells you to run `dw login --headless` — which reuses the saved browser profile's SSO session to refresh silently in ~5 seconds.

### HTTP client

`src/degreeworks/client.py` is ~50 lines. Only a `_get()` method exists. No POST, PUT, PATCH, or DELETE methods — not because they'd fail, but because the class literally doesn't have them. This is the same pattern as [`d2l-cli`](https://github.com/Aaryan-Kapoor/d2l-cli).

Two endpoints:

- `/api/audit?studentId=...&school=US&degree=BS&audit-type=AA&...` → full degree audit JSON
- `/api/course-link?discipline=CS&number=3305` → course info with prereqs and sections

### Parser

The audit JSON is a 3000+ line recursive rule tree. The `parser.py` module walks it once and produces clean Python dicts: header, blocks with rules, completed courses, in-progress courses, remaining requirements, progress summary. Every tool uses these structured dicts instead of touching the raw JSON.

Notable: the DegreeWorks course API encodes prerequisites as a flat array with per-entry `connector` (A/O), `leftParenthesis`, and `rightParenthesis` fields. The parser reconstructs this into a readable boolean expression: `((MATH 2345 (min C) OR CSE 2300 (min C)) AND ((CSE 1322 (min C) AND CSE 1322L (min C)) OR MTRE 2710 (min B) OR CPE 3000 (min B)))`.

### Configuration

`~/.degreeworks/` holds:

- `cookies.txt` — captured session cookies (keep private)
- `config.json` — auto-detected `school` / `degree` / `audit_type`
- `browser_profile/` — Playwright's persistent browser state (SSO session, etc.)

You can override config via env vars: `DEGREEWORKS_SCHOOL`, `DEGREEWORKS_DEGREE`, `DEGREEWORKS_AUDIT_TYPE`.

## Scope

This tool is currently wired to `degreeworks.kennesaw.edu`. DegreeWorks is an Ellucian product used by many universities — generalizing to other schools is possible by making `BASE_URL` configurable, but that's not done yet. If you're at another school and want this to work, open an issue.

## License

MIT — see [LICENSE](LICENSE).

---

<a name="advisor-note"></a>
<sub>* A Spring/Fall 2026 semester plan generated using this tool together with Claude Opus 4.6 in Claude Code was reviewed and approved by a KSU academic advisor. The advisor was not affiliated with this project and was not informed that the plan was AI-generated; it was presented as my own work. This note exists to share a real-world validation signal and does not imply any endorsement by the advisor or the university. — Aaryan Kapoor</sub>
