<div align="center">
  <img src="https://raw.githubusercontent.com/Aaryan-Kapoor/degreeworks-cli/main/assets/banner.gif" alt="degreeworks-cli: a student tells their AI agent to plan spring — 15 credits, nothing before 10am, works MWF afternoons; the agent runs dw commands to check prereq bottlenecks and real sections, then lays out a conflict-free weekly schedule with CRNs" width="720"/>
</div>

<p align="center">
  <a href="https://pypi.org/project/degreeworks-cli/"><img src="https://img.shields.io/pypi/v/degreeworks-cli?logo=pypi&logoColor=white&color=blue" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"/>
  <img src="https://img.shields.io/badge/read--only-by%20design-brightgreen" alt="Read-only"/>
  <img src="https://github.com/Aaryan-Kapoor/degreeworks-cli/actions/workflows/ci.yml/badge.svg" alt="CI"/>
</p>

**degreeworks-cli** turns any AI agent — Claude Code, Cursor, Copilot, Codex, anything that can run a command — into your course-scheduling advisor for KSU. Tell it your constraints — *15 credits, nothing before 10am, I work MWF afternoons, clear my major's prereq bottlenecks* — and it builds your **exact next semester**: specific sections with days, times, CRNs, instructors, and open seats, every prerequisite chain verified against your real degree audit. It's strictly **read-only** — it plans the schedule, you register.

The moat is a deterministic **8-phase schedule-planning protocol** plus fully parsed prerequisite logic and live section data, so the agent verifies every course instead of hallucinating one. Graduation-audit questions ("am I on track?", "what's left?") work too — but the point is the schedule.

<p align="center"><em>Tell your agent your constraints, get a real schedule — one good enough to pass advisor review<a href="#advisor-note">*</a>.</em></p>

## Set up in one message

Paste this into your AI agent:

```text
Fetch and follow the instructions from
https://raw.githubusercontent.com/Aaryan-Kapoor/degreeworks-cli/main/INSTALL_FOR_AGENTS.md
Set up degreeworks-cli for me end to end — install it, sign me in, and verify
it works. Then help me plan my next semester: ask me for my constraints and
build a real schedule with exact sections and CRNs.
```

That's the whole setup. The agent installs the CLI, installs its own degreeworks skill, opens a browser for your normal KSU SSO login (it never sees your password — the CLI just captures a read-only session and auto-detects your degree), verifies everything with `dw doctor`, and then gets to work on your schedule.

After that, your login refreshes itself: the CLI silently renews the session from your saved browser profile, so you'll rarely be asked to sign in again.

## Then just ask

> *"Plan my spring semester — 15 credits, nothing before 10am, I work MWF afternoons. Give me exact sections with CRNs."*

> *"Which single course, if I skip it next semester, delays my graduation the most?"*

### Prompts worth stealing

The point of an agent is autonomy — don't ask for data, ask for a schedule. Copy these:

**Build my exact next semester** *(the headline use)*

```text
Plan my spring semester: 15 credits, nothing before 10am, I work MWF afternoons,
and I want to prioritize clearing prerequisite bottlenecks for my major. Pull my
audit, then verify every candidate with `dw course` for prereqs, offering term,
and open sections — and give me exact sections with CRNs, days/times, instructors,
and seats. No time conflicts. Include a fallback section for each course.
```

**Break my prereq bottleneck**

```text
Look at everything I still need and find the prerequisite bottlenecks — the
courses that gate the most downstream courses. Tell me which ones to take next
semester to unlock my critical path, with the specific sections that fit a
schedule with no classes before 10am.
```

**Plan two semesters to graduation**

```text
Plan my next two semesters to graduation. Ask me for my credit load and any
day/time constraints, verify every course with `dw course` for prereqs and real
offerings, and give me a term-by-term schedule with CRNs, rationale, risks, and
fallbacks. Flag anything only offered every other term.
```

**The one-course deep dive**

```text
I'm considering CS 4720 next term. Check its prerequisites against what I've
completed, tell me whether I'm eligible, and list every scheduled section with
days, times, campus, instructor, and open seats.
```

**Am I on track to graduate?** *(the audit view)*

```text
Am I actually on track to graduate by my target date? Pull my progress and
remaining requirements, map out how many terms of what credit load it takes to
finish, and flag any bottleneck — a course only offered every other term, a long
prereq chain, or a requirement I keep deferring.
```

## How it works

1. **Your agent runs `dw`** — a small Python CLI that talks to DegreeWorks' own student API. Every call is a GET; the client has no POST/PUT/DELETE methods, so the tool physically cannot register, drop, or change anything.
2. **Auth is your normal browser login.** `dw login` opens a real browser to KSU SSO, you sign in like always, and the CLI captures the short-lived session cookies. The auth token expires roughly every 90 minutes, but the CLI silently refreshes it from your saved browser session — you sign in about once per device, not once per class.
3. **The agent carries a skill.** The bundled skill (`dw skill install`) teaches any agent the commands, the read-only rules, and a deterministic **8-phase schedule-planning protocol**, so a brand-new session plans reliably instead of hallucinating prereqs.

## Manual setup (no agent)

```bash
pipx install "degreeworks-cli[login]"
dw login          # browser opens — log in with KSU SSO
dw progress       # how close to graduation?
```

No pipx? Use `python -m pip install --user "degreeworks-cli[login]"` (on Windows: `py -m pip install --user "degreeworks-cli[login]"`) and make sure Python's user scripts directory is on your PATH — pip prints its exact location in a warning if it isn't.

`dw login` uses Playwright's bundled Chromium if present, and automatically falls back to your installed Chrome or Edge — so no 150 MB browser download is required on most machines.

## Commands

```
dw [--json | --md] <command>

Setup:
  doctor                    Diagnose install/PATH/auth/API state + next step
  skill install DIR         Install the bundled agent skill

Identity:
  login [--headless]        Browser-based KSU SSO login (cookies captured)
  whoami                    Student identity + token expiry

Academics:
  progress                  % to graduation, per-requirement progress bars
  remaining                 Every course still needed, grouped by requirement
  completed [--transfers]   Completed + in-progress courses, grouped by term
  audit                     Full degree-audit tree with per-rule status
  course DISCIPLINE NUMBER  Description, parsed prereqs, scheduled sections

AI snapshot:
  dump [--shallow]          Full academic snapshot (best paired with --md)
```

Output is human tables by default, `--json` for machines, `--md` for AI consumption — put the flag before the command: `dw --md course CS 3305`.

## For agent developers

- `AGENTS.md` at the repo root is the standing instruction file picked up by Claude Code, Cursor, Copilot, Codex, Windsurf, Aider, and friends — it holds the full 8-phase schedule-planning protocol.
- `dw skill install <dir>` emits the bundled portable skill (SKILL.md + references) into any skill system — no repo checkout needed.
- `dw --json doctor` reports every setup check with a `next_step` command, so agents never guess state.
- Every command is machine-readable with `--json`; `dw --md dump` is the one-shot full-context snapshot.

## Configuration

Config lives in `~/.degreeworks/` (all auto-populated during `dw login`):

- `cookies.txt` — session cookies (keep private)
- `config.json` — auto-detected `school` / `degree` / `audit_type`
- `browser_profile/` — Playwright's persistent SSO session (powers silent refresh)

Override any value per-run with `DEGREEWORKS_SCHOOL`, `DEGREEWORKS_DEGREE`, `DEGREEWORKS_AUDIT_TYPE`.

## Scope

Currently wired to `degreeworks.kennesaw.edu`. DegreeWorks is an Ellucian product used by many universities — generalizing to other schools by making the base URL configurable is possible but not done yet. If you're at another school and want this to work, open an issue.

## Strictly read-only

Every API call this tool makes is a GET. It cannot register or drop courses, modify the audit, or change anything in DegreeWorks — by design, not by policy. The `DegreeworksClient` class has no method other than `_get()`, `get_audit()`, and `get_course()`. Your agent gets eyes, not hands. Any plan it produces is advisory — confirm with your academic advisor and register through Owl Express.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This is a personal project and is not affiliated with, endorsed by, or associated with Ellucian, DegreeWorks, or Kennesaw State University. Just something I built for myself and thought was worth sharing.

---

<a name="advisor-note"></a>
<sub>* A Spring/Fall 2026 semester plan generated using this tool together with Claude Opus in Claude Code was reviewed and approved by a KSU academic advisor. The advisor was not affiliated with this project and was not informed that the plan was AI-generated; it was presented as my own work. This note exists to share a real-world validation signal and does not imply any endorsement by the advisor or the university. — Aaryan Kapoor</sub>
