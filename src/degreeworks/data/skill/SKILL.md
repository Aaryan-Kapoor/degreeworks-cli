---
name: degreeworks
description: Plan a KSU student's exact next semester — real sections, times, CRNs, and verified prerequisite chains — via the deterministic 8-phase schedule-planning protocol, backed by read-only DegreeWorks audit and course-catalog data. Use when the student asks to plan a semester, pick courses, build a schedule, break a prereq bottleneck, or check degree progress / remaining requirements.
allowed-tools: Bash(dw *) Bash(dw) Read
metadata: {"openclaw":{"emoji":"🎓","requires":{"bins":["dw"]}}}
---

# KSU DegreeWorks — Schedule Planning & Degree Audit

You have access to the `dw` CLI, which pulls **strictly read-only** data from a
KSU student's DegreeWorks degree audit and course catalog. Your headline job:
**build the student's exact next semester** — pick real sections that fit their
constraints (credit load, no-early-classes, work days, campus, prof preferences),
with CRNs, days/times, instructors, and open seats, every prerequisite verified —
using the 8-phase protocol below. It also answers degree-progress and
remaining-requirement questions, but scheduling is the point.

## Quick Reference

```bash
# Auth
dw login                 # opens a browser for KSU SSO — student logs in normally
dw login --headless      # silently refresh from the saved browser session
dw whoami                # student identity + token expiry (works even when expired)

# Diagnosis
dw doctor                # setup/auth/API state with the exact next command to run
dw --json doctor         # machine-readable

# Academic state
dw progress              # % to graduation, per-requirement progress bars
dw remaining             # every course still needed, grouped by requirement
dw completed             # completed + in-progress courses, grouped by term, with grades
dw completed --transfers # include transfer credits
dw audit                 # full degree-audit tree with per-rule status

# Courses
dw course CS 3305        # description, parsed prereqs, and scheduled sections
dw course MATH 2202      # (DISCIPLINE NUMBER)

# Full snapshot (best for AI)
dw --md dump             # everything: progress + in-progress + completed + remaining
dw --md dump --shallow   # quick: progress + in-progress only
```

Global flags go **before** the subcommand: `dw --md course CS 3305`. Use `--md`
(markdown, best for AI) or `--json` (structured) whenever you process output.

## Decision Tree

- **Simple informational question** ("what's my GPA?", "am I registered for MATH 2202?",
  "how many credits left?") → run one `dw` command and answer. No protocol needed.
- **Plan a semester / pick courses / build a schedule / "am I on track to graduate?"**
  → follow the **8-phase Schedule Planning Protocol** below, exactly. Do not skip
  phases, do not substitute memory for CLI verification, do not assume constraints.
- **Auth error or unclear state** → run `dw doctor` (or `dw whoami`) and follow the
  recovery step it names.

## Schedule Planning Protocol

Schedule planning with an LLM is failure-prone — models skip verification,
hallucinate prereqs, assume constraints, and confuse terms. This protocol
forces verification at every step to produce consistent, reproducible plans.

**Rules of engagement:** Do not skip or reorder phases. Do not substitute memory
for the CLI — always re-verify with `dw course`. Do not assume constraints; if
you don't know, ask. Do not present a plan that fails any validation check.

### Phase 0 — Verify Auth
```bash
dw whoami
```
Stop if status is `EXPIRED` (tell the student the recovery command from
**Auth Recovery** below and wait). Proceed if `ACTIVE`.

### Phase 1 — Gather Ground Truth
```bash
dw --md dump
```
This is the student's complete current state: identity, degree progress,
in-progress courses, completed courses, remaining requirements. Everything
downstream is grounded in this output. Do not fill gaps from memory or prior
conversation — even if the student says "you already know my situation."
DegreeWorks is authoritative and may have changed since last session.

### Phase 2 — Gather Constraints Explicitly
Before planning, these **must** be known. Ask the student directly for anything
missing — do not assume:
1. **Target term(s)** — which semester(s)?
2. **Credit load target** — 12 (full-time floor), 15 (standard), 18 (heavy), other
3. **Time window** — earliest start, latest end
4. **Unavailable days** — work, commute, obligations
5. **Campus preference** — Marietta, Kennesaw, or either
6. **Online cap** — any limit on online credits
7. **Locked-in courses** — honors contracts, advisor mandates, co-ops, existing registrations
8. **Graduation target** — when they plan or must graduate

A plan built on unstated constraints is a wrong plan. Ask and wait before Phase 3.

### Phase 3 — Identify Candidate Courses
From the `remaining` section of the Phase 1 dump, categorize every course:
- **Ready** — prereqs already met by completed/in-progress courses
- **Blocked** — depends on a course not yet taken (note which)
- **Free-text** — generic requirement ("9 credits of CS 3000–4000 level")

Candidate list = all Ready courses + any Blocked courses whose prereqs will be
in-progress the immediately preceding term + Free-text requirements resolved
into specific courses via the catalog.

### Phase 4 — Verify Each Candidate With `dw course`
**Most important phase. Do not skip.** For **every** candidate:
```bash
dw --md course <DISCIPLINE> <NUMBER>
```
Verify against the CLI output (not memory):
- [ ] Prerequisites met by the student's completed + in-progress courses
- [ ] Offered in the target term (check section term codes — many are every-other-term)
- [ ] A section's days/times fall within the availability window
- [ ] That section has seats (or is waitlistable if the student accepts the risk)
- [ ] That section respects campus preference and the online cap

Drop any course failing any check. Record the passing section's CRN, days, time,
campus, instructor.

### Phase 5 — Draft the Plan
From the verified shortlist: no time conflicts, total credits within ±3 of the
target load, corequisites included (labs with lectures), constraint-aware
(minimize campus days for commuters, respect online caps). Record per course:
CRN, discipline, number, title, credits, days, time, campus, instructor, seats.

### Phase 6 — Validate the Plan
Before presenting, confirm every item:
- [ ] Every course has an explicit CRN from a real, currently-open section
- [ ] No time conflicts (re-check days × times across the whole plan)
- [ ] Total credits matches the target load
- [ ] Every course satisfies a specific `remaining` requirement
- [ ] All prereq chains resolved (including for future-term courses)
- [ ] Every Phase 2 constraint honored

If any item fails, return to the phase that owns it. Do not present a failing plan.

### Phase 7 — Present with Decisions
1. **The Plan** — table: Code, Title, Credits, CRN, Days/Time, Campus, Instructor
2. **Rationale** — one line per course: which requirement it satisfies, why this section
3. **Risks & Trade-offs** — seats, waitlists, dependencies
4. **Fallbacks** — a backup section per course if the first closes
5. **What's Not in the Plan** — any Ready course deferred, with the reason

### Phase 8 — Defer to the Advisor
Close with: *"This plan is based on DegreeWorks data from Phase 1. Confirm with
your academic advisor before registering. The CLI cannot register for anything —
use Owl Express at your registration window."*

## Read-Only by Design

This tool is **strictly read-only** — it can only make GET requests. It cannot
and must not register/drop courses, modify the audit, change student data, or
submit forms. The `DegreeworksClient` has no method other than `_get()`,
`get_audit()`, and `get_course()` — enforced in code, not policy.

If a student asks you to register for a course, direct them to Owl Express or
their advisor. Never imply the CLI can take registration actions.

## Auth Recovery

`dw` maintains its own session: on an expired auth token it silently attempts a
headless refresh from the saved browser profile before failing. You'll rarely
see an auth error. When you do:

| Error | Meaning | What to do |
|---|---|---|
| `No cookies found` | First use, or cookies deleted | Ask to run `dw login` (opens browser) |
| `Auth token expired…refresh token still valid` | 90 min lapsed, silent refresh unavailable | `dw login --headless` |
| `Session fully expired` | Both tokens dead (>8 hrs) | Ask to run `dw login` |

Run `dw whoami` or `dw doctor` anytime to see token status without an API call.
Browser login is for **authentication only** — never scrape DegreeWorks through
the browser; all data comes from `dw` commands.

## Grade Codes

`A`–`F` letter grade · `REGD` registered/in-progress · `K` credit by exam ·
`W` withdrawn · `I` incomplete · `TR` transfer credit (see `--transfers`).

## Notes

- The audit reflects DegreeWorks' view, which can lag recent registrations by up to ~24h.
- `dw course` sections show only terms the registrar has published (current + next 1–2).
- `dw --md dump` is idempotent and cheap — re-run it to re-ground your understanding.
- Config env overrides: `DEGREEWORKS_SCHOOL`, `DEGREEWORKS_DEGREE`, `DEGREEWORKS_AUDIT_TYPE`.
- Deeper detail lives in `references/` (commands, safety) — read only when needed.
