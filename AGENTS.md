# AGENTS.md — DegreeWorks CLI

**This file is the single source of truth for agent instructions in this project.** Every protocol, every command, every constraint is documented here. `CLAUDE.md` imports this file so Claude Code loads it natively; `.claude/skills/degreeworks/SKILL.md` points here so Claude skill invocations read it. Update **this file** when you change agent instructions — never the pointers.

The `dw` CLI provides **strictly read-only** access to a KSU student's DegreeWorks degree audit and course catalog. Your headline job is **schedule planning**: build the student's exact next semester — real sections that fit their constraints, with CRNs, days/times, instructors, and open seats, every prerequisite chain verified — via the [Schedule Planning Protocol](#schedule-planning-protocol) below. Degree-audit questions ("am I on track?", "what's left?") are supported too, but the schedule is the product.

## TL;DR

Planning a semester (the main event) → follow the [Schedule Planning Protocol](#schedule-planning-protocol) exactly:

```bash
dw whoami              # verify auth — always first
dw --md dump           # full snapshot: progress + completed + in-progress + remaining
dw --md course CS 3305 # parsed prereqs + real sections (days/times/CRN/seats) for one course
dw --json doctor       # setup/auth/API state + the exact next command to run
```

For one-off queries ("what's my GPA?", "show my completed courses"), a single command is fine — no protocol needed.

---

## Schedule Planning Protocol

**When to use this protocol**: any time the student asks you to help plan a semester, pick courses, build a schedule, or decide what to take next. Not needed for simple informational queries.

**Why this protocol exists**: schedule planning with an LLM is failure-prone. Models skip verification, hallucinate prereqs, assume constraints, and confuse terms. This protocol is designed to produce **consistent, reproducible plans across different LLMs, different users, and different conversations** by forcing verification at every step.

**Rules of engagement**:

- **Do not skip phases.** Each phase depends on the previous.
- **Do not reorder.** Planning before gathering produces hallucinated output.
- **Do not substitute memory for the CLI.** Always re-verify with `dw course` — catalogs change, offerings vary, prior conversation is stale.
- **Do not assume constraints.** Missing constraints ⇒ wrong plan. If you don't know, ask.
- **Do not present a plan that fails any validation check.** Return to the failing phase instead.

### Phase 0 — Verify Auth

```bash
dw whoami
```

- **Stop if** status is `EXPIRED`. Tell the student the exact recovery command (see [Auth Error Recovery](#auth-error-recovery)) and wait. Do not attempt to describe the student's state from memory.
- **Proceed if** status is `ACTIVE`.

### Phase 1 — Gather Ground Truth

```bash
dw --md dump
```

This is the student's complete current state: identity, degree progress, in-progress courses, completed courses, and remaining requirements. **Everything downstream is grounded in this output.**

- **Do not** fill in gaps from memory, prior conversation, or assumptions. DegreeWorks is authoritative.
- **Do not** skip this even if the student says "you already know my situation." The snapshot may have changed since the last session (new grades posted, registrations dropped, audit re-evaluated).

### Phase 2 — Gather Constraints Explicitly

Before planning, these constraints **must** be known. Check the project `CLAUDE.md` and the current conversation for pre-set values. For anything missing, **ask the student directly** — do not assume.

1. **Target term(s)** — which semester(s) are we planning? (e.g., "Fall 2026", "Spring–Fall 2026")
2. **Credit load target** — minimum full-time (12), standard (15), heavy (18), or other
3. **Time window** — earliest acceptable class start, latest acceptable class end
4. **Unavailable days** — work, commute distance, family obligations, etc.
5. **Campus preference** — Marietta, Kennesaw, or either
6. **Online cap** — any limit on online credits per semester
7. **Locked-in courses** — honors contracts, advisor mandates, co-ops, existing registrations, transfer credits in flight
8. **Graduation target** — when the student plans or must graduate (visa constraints, financial aid, etc.)

A plan built on unstated constraints is a wrong plan. If any item above is unknown, **ask and wait for the answer** before proceeding to Phase 3.

### Phase 3 — Identify Candidate Courses

From the `remaining` section of the Phase 1 dump, categorize every listed course:

- **Ready** — prerequisites are already met by completed or in-progress courses
- **Blocked** — depends on a course not yet taken (note which)
- **Free-text** — generic requirement like "9 credits of CS 3000–4000 level"

For the target term, your candidate list is:

- All **Ready** courses
- Any **Blocked** courses whose prereqs will be in-progress during the immediately preceding term (so they'll be satisfied by the target term's start)
- **Free-text** requirements resolved into specific courses by consulting the catalog

### Phase 4 — Verify Each Candidate With `dw course`

**This is the most important phase. Do not skip.**

For **every** course on the candidate list, run:

```bash
dw --md course <DISCIPLINE> <NUMBER>
```

For each course, verify **all** of the following against the CLI output (not memory):

- [ ] Prerequisites are met by the student's completed + in-progress courses
- [ ] Course is offered in the target term (check section term codes — many courses are every-other-term)
- [ ] At least one section has days and times within the student's availability window
- [ ] That section has available seats, or is waitlistable if the student accepts the risk
- [ ] That section respects campus preference and the online-credit cap

Drop any course that fails any check. Record the passing section's CRN, days, time, campus, and instructor.

- **Do not** recall prereqs from memory or prior conversation.
- **Do not** assume a course is offered every term.
- **Do not** assume a section's meeting pattern — check.

### Phase 5 — Draft the Plan

From the verified shortlist, assemble the semester:

- **No time conflicts** across selected sections (overlapping meetings disqualify a pair)
- **Total credits** within ±3 of the student's target load
- **Corequisites included** (e.g., a lab required with a lecture — the CLI will flag these)
- **Constraint-aware** — minimize campus days for commuters, group classes on the same days if preferred, respect online caps

Record per course: CRN, discipline, number, title, credits, days, time, campus, instructor, seats remaining.

### Phase 6 — Validate the Plan

Run the full plan against this checklist before presenting:

- [ ] Every course has an explicit CRN from a real, currently-open section
- [ ] No time conflicts — re-check days × times across the whole plan
- [ ] Total credits matches the student's target load
- [ ] Every course satisfies a specific requirement in `remaining`
- [ ] All prereq chains are resolved (including prereqs for future-term courses)
- [ ] Every Phase 2 constraint is honored

If any item fails, return to the phase that owns it. **Do not present a failing plan.**

### Phase 7 — Present with Decisions

Structure the final output exactly like this so the student can review it:

1. **The Plan** — table with columns: Code, Title, Credits, CRN, Days/Time, Campus, Instructor
2. **Rationale** — one line per course: which `remaining` requirement it satisfies, and why this section was picked over others
3. **Risks & Trade-offs** — seats remaining, waitlist situations, any known instructor concerns (only if the student supplied a source like RMP), dependencies on other courses
4. **Fallbacks** — for each course, a backup section to use if the first closes before the student registers
5. **What's Not in the Plan** — any "Ready" course deferred to a later term, with the reason

### Phase 8 — Defer to the Advisor

Close with:

> This plan is based on DegreeWorks data from Phase 1. **Confirm with your academic advisor before registering.** The CLI cannot register for anything — use Owl Express at the student's registration window.

---

## Complete Command Reference

### Global Flags

Every command accepts these flags, placed **before** the subcommand:

| Flag | Purpose |
|---|---|
| `--json` | Structured JSON output (best for programmatic parsing) |
| `--md` | Markdown output (best for AI agents — easiest to read) |
| `--help` | Show help text (works without auth) |

**Default output** is human-readable tables with Unicode progress bars. For agent use, prefer `--md`.

### `dw doctor`

Diagnose setup state: install, PATH, Playwright, config, saved session, token validity, and a live read-only API call. Reports each check with a `next_step` command and exits non-zero when a required check fails. No auth required — it diagnoses auth itself.

```bash
dw doctor
dw --json doctor   # machine-readable; follow result.next_step
```

Run this first whenever setup state is unclear — during onboarding or months later. It is the single source of truth for "what do I need to do next."

### `dw skill install DIR`

Install the bundled agent skill (SKILL.md + references) into a skill directory, so any pip/pipx install is productive without a repo checkout.

```bash
dw skill install ~/.claude/skills/degreeworks   # Claude Code (user)
dw skill install .claude/skills/degreeworks     # Claude Code (project)
dw skill cat                                    # print SKILL.md to stdout
```

### `dw login`

Capture cookies via KSU SSO. Opens a Chromium browser via Playwright.

```bash
dw login              # interactive — student logs in via SSO
dw login --headless   # refresh using saved browser profile (no UI)
```

During login, the CLI auto-detects the student's `school` and `degree` codes by intercepting the first audit API request and saves them to `~/.degreeworks/config.json`.

### `dw whoami`

Show current student info and token expiry. Works with expired tokens (useful for debugging auth).

```bash
dw whoami
dw --json whoami   # machine-parseable
```

Output: name, student ID, token expiration timestamp, time remaining, status (`ACTIVE` or `EXPIRED`).

### `dw progress`

Progress bars by requirement area. Shows overall degree % and per-block completion.

```bash
dw --md progress
dw --json progress
```

Blocks shown: Degree, State Legislative Requirements, Honors (if applicable), each Gen Ed area (I/M/P/A/C/T/S), Major, etc.

### `dw remaining`

All courses still needed for graduation. Includes both specific course advice and free-text requirements (e.g., "Complete 9 credits of CS 3000-4000 level coursework").

```bash
dw --md remaining
```

Each row: course code, title, credits, whether it has prerequisites (`Yes`/empty), the requirement it satisfies.

### `dw completed`

Courses completed or in-progress, grouped by term.

```bash
dw --md completed               # KSU courses only
dw --md completed --transfers   # include transfer credits
```

Each row: course code, title, credits, grade (or `REGD` for in-progress), term.

### `dw audit`

Full degree audit tree with nested rules. Shows every requirement block, every sub-rule, the status of each rule (`DONE` / `IP` / `NEED` / percentage), applied courses, and needed courses. This is the most detailed view.

```bash
dw --md audit
```

Use this when you need to understand **why** a specific course counts toward a specific requirement, or to see the full structure of the degree plan.

### `dw course DISCIPLINE NUMBER`

Look up a specific course: description, prerequisites (as parsed boolean logic), and all scheduled sections for upcoming terms.

```bash
dw --md course CS 3305
dw --md course MATH 2202
dw --md course HIST 2112
```

Prerequisites are returned as a logical expression like:

```
((MATH 2345 (min C) OR CSE 2300 (min C)) AND ((CSE 1322 (min C) AND CSE 1322L (min C)) OR MTRE 2710 (min B) OR CPE 3000 (min B)))
```

Sections include: term, CRN, days (e.g., `MWF`, `TR`), time, building/room, instructor, campus, enrollment (current/max), waitlist.

### `dw dump`

Full academic snapshot in a single command. **Use this in Phase 1 of the schedule planning protocol.**

```bash
dw --md dump             # everything: progress + in-progress + completed + remaining + blocks
dw --md dump --shallow   # quick: progress + in-progress only
dw --json dump           # structured JSON snapshot
```

---

## Configuration

The CLI reads config from `~/.degreeworks/config.json`, auto-populated during `dw login`. Override any value with environment variables:

| Env var | Purpose | Default |
|---|---|---|
| `DEGREEWORKS_SCHOOL` | Banner school code (e.g., `US` for undergrad) | `US` |
| `DEGREEWORKS_DEGREE` | Degree code (`BS`, `BA`, `BBA`, `BFA`, etc.) | `BS` |
| `DEGREEWORKS_AUDIT_TYPE` | Audit type | `AA` |

Priority: env vars > config.json > hardcoded defaults.

Files:

- `~/.degreeworks/cookies.txt` — session cookies
- `~/.degreeworks/config.json` — school/degree/audit_type
- `~/.degreeworks/browser_profile/` — Playwright's persistent browser state

---

## Auth Error Recovery

Auth normally maintains itself: the auth token expires about every 90 minutes,
but before any command fails, the CLI **silently** attempts a headless refresh
from the saved browser profile (`~/.degreeworks/browser_profile`). You will
rarely see an auth error. When the silent refresh can't recover, you'll get:

| Error | What it means | What to do |
|---|---|---|
| `No DegreeWorks session found` | First use, or cookies deleted, and no saved session to refresh from | Ask the user, then run `dw login` |
| `Your DegreeWorks session needs a fresh sign-in` | Silent refresh failed — the saved SSO session has fully expired | Ask the user, then run `dw login` |

The user completes the browser/SSO login interactively; never ask them to copy
tokens or open DevTools. Set `DEGREEWORKS_NO_AUTO_LOGIN=1` to disable the silent
refresh (rarely needed). Check `dw whoami` or `dw doctor` anytime to see token
status without triggering a refresh.

---

## Read-Only by Design

This tool is **strictly read-only**. It can only make GET requests to the DegreeWorks API. It **cannot** and **must not**:

- Register or drop courses
- Modify the degree audit
- Change any student data
- Submit any forms
- Make POST, PUT, PATCH, or DELETE requests

The `DegreeworksClient` class in `src/degreeworks/client.py` has no method other than `_get()`, `get_audit()`, and `get_course()`. This is enforced in code, not just policy.

**If a student asks you to register for a course, direct them to Owl Express or their advisor.** Never imply the CLI can take registration actions.

---

## Grade Codes

| Code | Meaning |
|---|---|
| `A`–`F` | Standard letter grade |
| `REGD` | Registered / in-progress (hasn't finished the course yet) |
| `K` | Credit by exam (AP credit, transfer with P/NP, etc.) |
| `W` | Withdrawn |
| `I` | Incomplete |
| `TR` | Transfer credit (see `--transfers` flag) |

---

## Other Notes

- The audit reflects DegreeWorks' view, which may lag behind very recent registrations (sometimes up to 24 hours).
- `dw course` sections are only shown for terms the registrar has published — typically the current term and the next 1–2 upcoming terms.
- Transfer courses have a `transfer: true` flag in `--json` output.
- `dw --md dump` is idempotent and cheap — run it whenever you need to re-ground your understanding of the student's state.

---

## For Agent Harnesses

This file follows the [AGENTS.md](https://agents.md) open standard and is natively discovered by most coding-agent harnesses:

- **AGENTS.md-native**: OpenAI Codex, Cursor, Aider, GitHub Copilot, Windsurf, Google Jules, JetBrains Junie, Factory, Devin, VS Code agents
- **Claude Code**: loaded via `CLAUDE.md` which imports this file with `@AGENTS.md`, plus the `.claude/skills/degreeworks/` skill which instructs the agent to read this file

**Single source of truth**: if you are updating agent instructions, update **this file**. The pointer files (`CLAUDE.md`, `SKILL.md`) exist only to route different harnesses here and should never contain instructions of their own.
