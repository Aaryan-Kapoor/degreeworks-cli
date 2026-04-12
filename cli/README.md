# `dw` CLI — alternative to the MCP server

The `dw` command is the underlying transport that the `degreeworks-mcp` server shells out to. The MCP server is the **recommended** way to use this project — see the project [README](../README.md). This document covers the CLI as a direct alternative for harnesses that don't speak MCP, scripts, or human terminal use.

## When to use the CLI directly instead of the MCP server

- Your agent harness doesn't support MCP yet — Codex, Aider, GitHub Copilot, JetBrains Junie, plain VS Code agents. They read this `cli/README.md` (or the project root README) and shell out to `dw`.
- You're writing a shell script or Makefile that needs DegreeWorks data.
- You want a human-readable progress check from a terminal (e.g., to verify what an agent told you).
- You're debugging the MCP server and want to invoke commands directly to isolate issues.

For everything else (Claude Desktop, Claude Code, Cursor, Windsurf, Zed, Continue, Gemini CLI), the MCP server is simpler and gives the agent richer context via the `plan_semester` prompt.

## Install

```bash
pip install "degreeworks-mcp[login]"
playwright install chromium
dw login
```

This installs the same package as the MCP route — the `dw` CLI is always present alongside `degreeworks-mcp`. The `[login]` extra brings in Playwright, which is needed for the one-time SSO bootstrap.

After `dw login`, cookies are saved to `~/.degreeworks/cookies.txt` and reused by both the CLI and the MCP server.

## Commands

| Command | What it does |
|---|---|
| `dw login` | Capture cookies via KSU SSO (Playwright browser) |
| `dw login --headless` | Refresh cookies using saved browser profile (no UI) |
| `dw whoami` | Show student info and token expiry (works when expired) |
| `dw progress` | Progress bars by requirement area |
| `dw remaining` | Courses still needed for graduation |
| `dw completed` | Completed courses grouped by term |
| `dw completed --transfers` | Include transfer credits |
| `dw audit` | Full degree audit tree with per-rule status |
| `dw course CS 3305` | Course description, prereqs, sections |
| `dw dump` | Full academic snapshot (best paired with `--md`) |
| `dw dump --shallow` | Quick overview only |

## Output formats

All commands except `dw login` accept these global flags, placed **before** the subcommand:

| Flag | Purpose |
|---|---|
| `--json` | Structured JSON output (best for programmatic parsing) |
| `--md` | Markdown output (best for AI agents — easiest to read) |
| `--help` | Show help text (works without auth) |

```bash
dw --md dump           # markdown snapshot for AI agents
dw --json remaining    # structured JSON
dw progress            # human-readable tables (default)
```

## Example: agent workflow via shell-out

If your harness shells out to commands, it can use `dw` directly to follow the 8-phase Schedule Planning Protocol:

```
You: "Plan my next 4 semesters"

Agent runs:
  dw --md whoami               # Phase 0: verify auth
  dw --md dump                 # Phase 1: full picture
  # asks you for Phase 2 constraints
  dw --md course CS 3503       # Phase 4: verify each candidate
  dw --md course CS 3410
  ...

Agent returns: a semester-by-semester plan with specific CRNs,
schedule conflict checks, and prereq chain validation.
```

The full 8-phase Schedule Planning Protocol lives in `src/degreeworks/_protocol.py` (it's the same text the MCP server's `plan_semester` prompt returns). For non-MCP harnesses, point the agent at that file directly, or use the [project README](../README.md#the-schedule-planning-protocol) which contains the 8-step summary.

## How auth works

DegreeWorks uses two JWT cookies:

- `X-AUTH-TOKEN` — 90 minutes, used for API calls
- `REFRESH_TOKEN` — 8 hours, used to refresh the auth token without re-logging in

`dw login` launches Chromium via Playwright with a persistent browser profile at `~/.degreeworks/browser_profile/`. You log in with KSU SSO normally. Playwright polls for the auth cookie to appear, captures all `degreeworks.kennesaw.edu` cookies, and intercepts the first `/api/audit` request to auto-detect your school (US) and degree (BS/BA/BBA/...) from the query params. Everything is saved to `~/.degreeworks/`.

Token expiry is checked **before** every API call so you get clear error messages instead of cryptic 401s. If the auth token is expired but the refresh token is alive, the CLI tells you to run `dw login --headless` — which reuses the saved browser profile's SSO session to refresh silently.

## Auth error recovery

| Error | What it means | What to do |
|---|---|---|
| `No cookies found` | First time use, or cookies deleted | Run `dw login` |
| `Auth token expired, but refresh token is still valid` | 90 min lapsed | Run `dw login --headless` |
| `Session fully expired` | Both tokens dead (>8 hrs) | Run `dw login` |

Check `dw whoami` anytime to see exact token status without triggering an API call.

## Configuration

`~/.degreeworks/` holds:

- `cookies.txt` — captured session cookies (keep private)
- `config.json` — auto-detected `school` / `degree` / `audit_type`
- `browser_profile/` — Playwright's persistent browser state (SSO session, etc.)

You can override config via environment variables:

| Env var | Purpose | Default |
|---|---|---|
| `DEGREEWORKS_SCHOOL` | Banner school code (`US` for undergrad) | `US` |
| `DEGREEWORKS_DEGREE` | Degree code (`BS`, `BA`, `BBA`, `BFA`, etc.) | `BS` |
| `DEGREEWORKS_AUDIT_TYPE` | Audit type | `AA` |

Priority: env vars > config.json > hardcoded defaults.

## Read-only by design

The `dw` CLI (and the MCP server built on it) is **strictly read-only**. The `DegreeworksClient` in `src/degreeworks/client.py` has no method other than `_get()`, `get_audit()`, and `get_course()`. It cannot register, drop, or modify anything. Use Owl Express or your academic advisor for registration actions.
