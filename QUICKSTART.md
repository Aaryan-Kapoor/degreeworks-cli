# Agent Quick Start

You are an AI agent. This file is the short version of how to use the `dw` CLI to
access a KSU student's DegreeWorks data. Everything is **read-only**. For the full
end-to-end setup, follow
[`INSTALL_FOR_AGENTS.md`](INSTALL_FOR_AGENTS.md); for the schedule-planning
protocol and command reference, read [`AGENTS.md`](AGENTS.md).

## Setup (run once)

```bash
pipx install "degreeworks-cli[login]"   # or: python -m pip install --user "degreeworks-cli[login]"
dw skill install ~/.claude/skills/degreeworks   # install the bundled skill
dw login                                 # user logs in via KSU SSO — opens a browser
```

`dw` should be installed on PATH (persist Python's user scripts dir if using pip).
Do not rely on an activated venv for normal agent use. `dw login` falls back to
installed Chrome/Edge when Playwright's bundled Chromium is missing, so
`playwright install chromium` is optional. There is no school to configure —
degreeworks-cli is wired to KSU and auto-detects the student's degree at login.

At any point, `dw --json doctor` reports setup state with the exact next command.

## Check auth

```bash
dw whoami          # student identity + token status (ACTIVE / EXPIRED)
```

Expired tokens refresh themselves: every command silently re-authenticates from
the saved browser session before failing. If a command still reports a sign-in
error, ask the user whether you may launch the browser, then run `dw login`.

## Commands

```bash
dw --json doctor              # setup state + next step
dw whoami                     # verify identity
dw --md progress              # % to graduation, per-requirement bars
dw --md remaining             # every course still needed
dw --md completed             # completed courses by term (--transfers for transfers)
dw --md audit                 # full degree-audit tree with per-rule status
dw --md course CS 3305        # description, parsed prereqs, scheduled sections
dw --md dump                  # full academic snapshot
dw --md dump --shallow        # quick: progress + in-progress only
```

## Output flags

- No flag: human-readable tables (for display)
- `--md`: markdown optimized for AI consumption (use this)
- `--json`: structured JSON (for parsing)

Put the flag before the command: `dw --md course CS 3305`.

## Safety defaults

- Use `dw` only for read-only DegreeWorks data. It cannot register, drop, or modify anything.
- Do not scrape DegreeWorks through the browser; browser login is for authentication only.
- Always re-verify prereqs, offerings, and sections with `dw course` — never from memory.
- Any schedule plan is advisory: tell the user to confirm with their advisor and register via Owl Express.
- If required data can't be fetched, stop and report the blocker instead of guessing.

## Schedule planning

When the user asks to plan a semester, pick courses, or check if they're on track
to graduate, follow the **8-phase Schedule Planning Protocol** in
[`AGENTS.md`](AGENTS.md) exactly — do not skip verification steps.

## Skill file

The skill ships inside the package. Install it into your agent system's native
skills directory:

```bash
dw skill install ~/.claude/skills/degreeworks      # Claude Code (user-level)
dw skill install .claude/skills/degreeworks        # Claude Code (project)
dw skill install ~/.agents/skills/degreeworks      # OpenClaw (personal)
```
