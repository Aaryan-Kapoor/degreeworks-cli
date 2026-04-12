<div align="center">
  <img src="banner.svg" alt="degreeworks-cli" width="720"/>
</div>

<p align="center">
  <strong>Read-only DegreeWorks CLI for KSU – built for AI agents to plan student schedules.</strong><br/>
  <em>Plans schedules good enough to pass advisor review<a href="#advisor-note">*</a>.</em>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#commands">Commands</a> ·
  <a href="#ai-agent-setup">AI Agent Setup</a> ·
  <a href="#how-it-works">How it works</a>
</p>

---

`degreeworks-cli` is a tiny, strictly **read-only** CLI that pulls your KSU DegreeWorks degree audit and course catalog into clean JSON, markdown, or human tables — so an AI agent in Claude Code, Cursor, or any other tool can help you plan your semesters.

It is designed to be used by AI agents, not humans. Humans are welcome anyway.

## Features

- **`dw login`** – one-time browser login via KSU SSO (Playwright), cookies captured automatically
- **`dw progress`** – how close you are to graduating, with progress bars per requirement
- **`dw remaining`** – every course you still need, grouped by requirement
- **`dw completed`** – every course you've done, grouped by term, with grades
- **`dw audit`** – full degree audit tree with per-rule status
- **`dw course CS 3305`** – course description, prerequisites (fully parsed into boolean logic), and all scheduled sections with days/times/instructors/seats
- **`dw dump`** – full academic snapshot in one command, optimized for AI agents
- **Three output formats**: human tables, `--json`, `--md`
- **Strictly read-only.** No POST/PUT/DELETE methods exist in the client, by design. This tool cannot register, drop, or modify anything.

## Quickstart

```bash
git clone https://github.com/Aaryan-Kapoor/degreeworks-cli.git
cd degreeworks-cli
pip install -e ".[login]"
playwright install chromium

dw login          # opens browser, log in with KSU SSO
dw progress       # how close to graduation?
```

That's it. Cookies are saved to `~/.degreeworks/cookies.txt` and last 90 minutes. Run `dw login --headless` to refresh without re-entering credentials (requires a prior interactive login).

## Commands

| Command | What it does |
|---|---|
| `dw login` | Capture cookies via KSU SSO (Playwright browser) |
| `dw login --headless` | Refresh cookies using saved browser profile (no UI) |
| `dw whoami` | Show student info and token expiry |
| `dw progress` | Progress bars by requirement area |
| `dw remaining` | Courses still needed for graduation |
| `dw completed` | Completed courses grouped by term |
| `dw completed --transfers` | Include transfer credits |
| `dw audit` | Full degree audit tree with per-rule status |
| `dw course CS 3305` | Course description, prereqs, sections |
| `dw dump` | Full academic snapshot (best paired with `--md`) |
| `dw dump --shallow` | Quick overview only |

All commands support `--json` and `--md` flags for structured output:

```bash
dw --md dump           # markdown snapshot for AI agents
dw --json remaining    # structured JSON
```

## AI Agent Setup

All agent instructions live in a single file: **[`AGENTS.md`](AGENTS.md)**. It follows the [agents.md](https://agents.md) open standard and is natively discovered by Codex, Cursor, Aider, Copilot, Windsurf, Jules, Junie, Factory, Devin, and most other coding-agent harnesses. No per-tool setup needed — just open the project in your agent.

For **Claude Code**, a one-line `CLAUDE.md` imports `AGENTS.md` via `@AGENTS.md` so it loads automatically, and `.claude/skills/degreeworks/SKILL.md` provides a skill-triggered entry point that reads the same file. Open the project and start asking about your schedule.

### The Schedule Planning Protocol

`AGENTS.md` contains a deterministic **8-phase Schedule Planning Protocol** designed to produce reliable, reproducible plans across different LLMs, different users, and different conversations. When you ask an agent to plan a semester, it will:

1. **Verify auth** — `dw whoami` to confirm cookies are live
2. **Gather ground truth** — `dw --md dump` for the complete current state
3. **Gather constraints explicitly** — ask you for target terms, credit load, time window, days, campus, online cap, locked-in courses, graduation target (no assumed defaults)
4. **Identify candidates** — categorize every remaining course as Ready / Blocked / Free-text
5. **Verify each candidate with `dw course`** — prereqs, offering term, seats, schedule fit
6. **Draft the plan** — conflict-free, credit-load-compliant
7. **Validate against a checklist** — CRNs, conflicts, credits, prereq chains, all Phase 2 constraints
8. **Present with rationale, risks, and fallbacks** — then defer to your academic advisor for final sign-off

The protocol forces verification at every step instead of letting the model hallucinate prereqs or assume a course is offered.

## How it works

### Auth

DegreeWorks uses two JWT cookies:
- `X-AUTH-TOKEN` — 90 min, used for API calls
- `REFRESH_TOKEN` — 8 hr, used to refresh the auth token without re-logging in

`dw login` launches Chromium via Playwright with a persistent browser profile at `~/.degreeworks/browser_profile/`. You log in with KSU SSO normally. Playwright polls for the auth cookie to appear, captures all `degreeworks.kennesaw.edu` cookies, and also intercepts the first `/api/audit` request to auto-detect your school (US) and degree (BS/BA/BBA/...) from the query params. Everything is saved to `~/.degreeworks/`.

Token expiry is checked **before** every API call so you get clear error messages instead of cryptic 401s. If the auth token is expired but the refresh token is alive, the CLI tells you to run `dw login --headless` — which reuses the saved browser profile's SSO session to refresh silently.

### Client

One file, ~50 lines. Only a `_get()` method exists. No POST, PUT, PATCH, or DELETE methods — not because they'd fail, but because the class literally doesn't have them. This is the same pattern as [`d2l-cli`](https://github.com/Aaryan-Kapoor/d2l-cli).

Two endpoints:
- `/api/audit?studentId=...&school=US&degree=BS&audit-type=AA&...` → full degree audit JSON
- `/api/course-link?discipline=CS&number=3305` → course info with prereqs and sections

### Parser

The audit JSON is a 3000+ line recursive rule tree. The `parser.py` module walks it once and produces clean Python dicts: header, blocks with rules, completed courses, in-progress courses, remaining requirements, progress summary. Every command uses these structured dicts instead of touching the raw JSON.

Notable: the DegreeWorks course API encodes prerequisites as a flat array with per-entry `connector` (A/O), `leftParenthesis`, and `rightParenthesis` fields. The parser reconstructs this into a readable boolean expression: `((MATH 2345 (min C) OR CSE 2300 (min C)) AND ((CSE 1322 (min C) AND CSE 1322L (min C)) OR MTRE 2710 (min B) OR CPE 3000 (min B)))`.

### Configuration

`~/.degreeworks/` holds:
- `cookies.txt` — captured session cookies (keep private)
- `config.json` — auto-detected `school`/`degree`/`audit_type`
- `browser_profile/` — Playwright's persistent browser state (SSO session, etc.)

You can override config via env vars: `DEGREEWORKS_SCHOOL`, `DEGREEWORKS_DEGREE`, `DEGREEWORKS_AUDIT_TYPE`.

## Scope

This tool is currently wired to `degreeworks.kennesaw.edu`. DegreeWorks is an Ellucian product used by many universities — generalizing to other schools is possible by making `BASE_URL` configurable, but that's not done yet. If you're at another school and want this to work, open an issue.

## License

MIT — see [LICENSE](LICENSE).

---

<a name="advisor-note"></a>
<sub>* A Spring/Fall 2026 semester plan generated using this tool together with Claude Opus 4.6 in Claude Code was reviewed and approved by a KSU academic advisor. The advisor was not affiliated with this project and was not informed that the plan was AI-generated; it was presented as my own work. This note exists to share a real-world validation signal and does not imply any endorsement by the advisor or the university. — Aaryan Kapoor</sub>
