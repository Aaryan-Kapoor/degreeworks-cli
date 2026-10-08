# degreeworks-cli Installation Guide for AI Agents

You are an AI agent setting up `degreeworks-cli` — a strictly read-only CLI for a KSU student's DegreeWorks degree audit and course catalog — so that you and future agent sessions can answer questions about the student's degree progress and plan their semesters.

This file is self-contained: everything you need is here and in the skill you install in Step 2. Follow the steps in order.

Handle everything technical yourself. The user's part is: completing one browser login (Step 3) and picking what to do first (Step 5). Those are part of setup, not interruptions — never skip an interactive step just to ask fewer questions.

## Step 0: Operating Rules

These rules apply during setup and forever after:

1. Treat DegreeWorks as **read-only**. Never register or drop courses, modify the audit, submit forms, or perform any action that mutates DegreeWorks state. The CLI physically cannot — every request is a GET.
2. The browser is for **authentication only**. Never scrape DegreeWorks through the browser — all data comes from `dw` commands.
3. Never ask the user to open DevTools, copy tokens, or paste cookies. `dw login` captures the session automatically while they log in normally through KSU SSO.
4. Any schedule you plan is **advisory** — always tell the user to confirm with their academic advisor before registering. The CLI cannot register anything.
5. If required data can't be fetched because of auth, permissions, or access, stop and report the blocker. Do not guess from stale or partial data unless the user explicitly accepts that tradeoff.

## Step 1: Install the CLI — Onto the User's PATH

**Requirement: when this step is done, `dw` must work in a fresh terminal** — installed user-globally with its directory persisted on the user's PATH, not just reachable in your current shell or a venv. Only deviate if the user explicitly asks for a different install location.

If `pipx` is available, prefer it:

```bash
pipx install "degreeworks-cli[login]"
pipx ensurepath      # persists the install dir on PATH (no-op if already there)
dw --version
```

Otherwise use pip (`py` instead of `python` on Windows if `python` is not found):

```bash
python -m pip install --user "degreeworks-cli[login]"
dw --version
```

With pip, always find the user scripts directory and make sure it is persisted on PATH — don't wait for a "command not found" to do this:

```bash
python -c "import os, sysconfig; print(sysconfig.get_path('scripts', f'{os.name}_user'))"
```

- **macOS / Linux:** if the user's shell rc file (`~/.profile`, `~/.bashrc`, or `~/.zshrc`) doesn't already put that directory on PATH, append `export PATH="<that dir>:$PATH"` to it — and `export` it in your current session too.
- **Windows (PowerShell):** persist with
  `[Environment]::SetEnvironmentVariable("Path", "<that dir>;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")`
  and for the current session run `$env:Path = "<that dir>;$env:Path"`.

Notes:

- `playwright install chromium` is **not** required: `dw login` automatically falls back to the user's installed Chrome or Edge. Only run `python -m playwright install chromium` if login later reports that no browser could be launched.
- The `[login]` extra pulls in Playwright, used only for the one-time SSO login. After that, the CLI reads the saved session and refreshes it silently.

## Step 2: Install the Skill — Into Your Own Skill Directory

The package bundles a portable agent skill (SKILL.md + reference docs). Install it into **your own agent system's skill directory** right now, before continuing — it is your permanent reference for commands, the schedule-planning protocol, and safety rules, and it makes every future session productive without this file.

```bash
dw skill install ~/.claude/skills/degreeworks      # Claude Code (user-level)
dw skill install .claude/skills/degreeworks        # Claude Code (project-level)
dw skill install ~/.agents/skills/degreeworks      # OpenClaw (personal)
dw skill install <your-skill-dir>/degreeworks      # any other agent system
```

Pick the location that matches the system you are running in. If your runtime has no skill support, run `dw skill cat` and keep its contents in your working context instead.

There is no school to configure — degreeworks-cli is wired to KSU (`degreeworks.kennesaw.edu`), and the student's specific degree/school codes are auto-detected during login in the next step.

## Step 3: Authenticate — Hand Off to the User

This is the one step only the user can do. Ask them first:

> I need you to log in to DegreeWorks in a browser window so the CLI can capture a read-only session — you just log in normally with your KSU SSO. May I open the browser?

When they agree, run:

```bash
dw login
```

A browser opens to KSU SSO. **The user completes their normal login (username, password, Duo/2FA) — wait for them.** You never see their password; the CLI just captures the DegreeWorks session cookies and auto-detects their school and degree codes from the first audit request. Then verify:

```bash
dw whoami
```

It should print the student's name, ID, and an `ACTIVE` token.

**After this one login, auth maintains itself.** The auth token expires about every 90 minutes, but every `dw` command silently refreshes it from the saved browser session before failing. You should almost never be asked to log in again — if you are, the saved session has fully expired, and the fix is one more `dw login`.

## Step 4: Verify Everything

```bash
dw doctor
```

`dw doctor` is your compass for this entire setup. It reports every check — install, PATH, Playwright, config, saved session, token validity, and a **live read-only API call** — and prints the exact `next_step` command for anything that isn't ready. Use `dw --json doctor` when you want to parse it. Whenever you're unsure what state things are in, during setup or months from now, run it and follow `next_step`.

Then pull a real snapshot to confirm data access:

```bash
dw --md dump --shallow
```

Expected: doctor reports `"status": "ready"`, and `dump --shallow` returns the student's degree progress and in-progress courses.

## Step 5: Get the User Started

Setup ends with a demonstration, not a checklist. Pull something real, then offer a personalized first move:

1. Run `dw --md progress` (or reuse the Step 4 snapshot).
2. Tell the user one concrete thing you found — their overall completion percentage, how many credits remain, or the requirement block closest to done.
3. Offer 2–3 things they could ask you right now, built from **their actual audit** — not generic examples. For instance:
   - "You're 78% done and only General Education area C and 4 major courses remain — want me to plan a two-semester path to graduation?"
   - "You have 3 'Ready' CS electives whose prereqs you've already cleared — I can check which are offered next term and build a conflict-free schedule."
   - "I can audit your completed courses against the catalog and flag anything that didn't apply where you'd expect."

If they pick one that involves planning a semester, follow the **8-phase Schedule Planning Protocol** from the skill exactly.

## Step 6: Daily Usage Patterns

```bash
dw --md dump                 # full snapshot: progress + completed + in-progress + remaining
dw --md dump --shallow       # quick: progress + in-progress only
dw --md progress             # % to graduation, per-requirement
dw --md remaining            # every course still needed
dw --md completed            # completed courses by term (--transfers to include transfers)
dw --md audit                # full degree-audit tree
dw --md course CS 3305       # prereqs + scheduled sections for one course
```

Rules of thumb:

- Global flags go **before** the command: `dw --md course CS 3305`, never `dw course --md CS 3305`.
- Use `--md` or `--json` whenever you process output; bare human tables are for display only.
- For schedule planning, follow the 8-phase protocol in the skill — never substitute memory for `dw course` verification.

## Final Checklist

Before declaring setup complete:

- [ ] `dw --version` works, and would work in a fresh terminal (PATH persisted — Step 1)
- [ ] The skill is installed in your skill directory (Step 2)
- [ ] `dw whoami` identifies the user with an `ACTIVE` token
- [ ] `dw --json doctor` reports `"status": "ready"`
- [ ] You told the user their login now refreshes itself
- [ ] You showed the user one real result and offered personalized prompts to try (Step 5)
