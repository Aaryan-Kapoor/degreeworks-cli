"""The 8-phase Schedule Planning Protocol, served as an MCP prompt.

This is the single source of truth for the protocol. The MCP server's
`plan_semester` prompt returns the SCHEDULE_PLANNING_PROTOCOL constant
verbatim. Agents invoke that prompt at the start of any planning task
to load the rules into context. There is no parallel copy in any other
file — update this constant when you want to change the protocol.
"""

SCHEDULE_PLANNING_PROTOCOL = """# Schedule Planning Protocol

A deterministic 8-phase protocol designed to produce consistent results across different LLMs, different users, and different conversations when planning a KSU student's semester.

## Rules of engagement

- **Do not skip phases.** Each phase depends on the previous.
- **Do not reorder.** Planning before gathering produces hallucinated output.
- **Do not substitute memory for the CLI.** Always re-verify with the `course` tool — catalogs change, offerings vary, prior conversation is stale.
- **Do not assume constraints.** Missing constraints ⇒ wrong plan. If you don't know, ask.
- **Do not present a plan that fails any validation check.** Return to the failing phase instead.

## Phase 0 — Verify Auth

Call the `whoami` tool.

- **Stop if** status is `EXPIRED`. Tell the student to run `dw login` in a terminal (the MCP server cannot perform SSO login — it requires a real browser with KSU credentials). Wait for them to come back.
- **Proceed if** status is `ACTIVE`.

## Phase 1 — Gather Ground Truth

Call the `dump` tool.

This is the student's complete current state: identity, degree progress, in-progress courses, completed courses, and remaining requirements. **Everything downstream is grounded in this output.**

- **Do not** fill in gaps from memory, prior conversation, or assumptions. DegreeWorks is authoritative.
- **Do not** skip this even if the student says "you already know my situation." The snapshot may have changed since the last session (new grades posted, registrations dropped, audit re-evaluated).

## Phase 2 — Gather Constraints Explicitly

Before planning, these constraints **must** be known. For anything missing, **ask the student directly** — do not assume.

1. **Target term(s)** — which semester(s) are we planning? (e.g., "Fall 2026", "Spring–Fall 2026")
2. **Credit load target** — minimum full-time (12), standard (15), heavy (18), or other
3. **Time window** — earliest acceptable class start, latest acceptable class end
4. **Unavailable days** — work, commute, family obligations, etc.
5. **Campus preference** — Marietta, Kennesaw, or either
6. **Online cap** — any limit on online credits per semester
7. **Locked-in courses** — honors contracts, advisor mandates, co-ops, existing registrations, transfer credits in flight
8. **Graduation target** — when the student plans or must graduate (visa constraints, financial aid, etc.)

A plan built on unstated constraints is a wrong plan. If any item above is unknown, **ask and wait for the answer** before proceeding to Phase 3.

## Phase 3 — Identify Candidate Courses

From the `remaining` section of the Phase 1 dump, categorize every listed course:

- **Ready** — prerequisites are already met by completed or in-progress courses
- **Blocked** — depends on a course not yet taken (note which)
- **Free-text** — generic requirement like "9 credits of CS 3000–4000 level"

For the target term, your candidate list is:

- All **Ready** courses
- Any **Blocked** courses whose prereqs will be in-progress during the immediately preceding term (so they'll be satisfied by the target term's start)
- **Free-text** requirements resolved into specific courses by consulting the catalog

## Phase 4 — Verify Each Candidate With `course`

**This is the most important phase. Do not skip.**

For **every** course on the candidate list, call the `course` tool with the discipline and number.

For each course, verify **all** of the following against the tool output (not memory):

- [ ] Prerequisites are met by the student's completed + in-progress courses
- [ ] Course is offered in the target term (check section term codes — many courses are every-other-term)
- [ ] At least one section has days and times within the student's availability window
- [ ] That section has available seats, or is waitlistable if the student accepts the risk
- [ ] That section respects campus preference and the online-credit cap

Drop any course that fails any check. Record the passing section's CRN, days, time, campus, and instructor.

- **Do not** recall prereqs from memory or prior conversation.
- **Do not** assume a course is offered every term.
- **Do not** assume a section's meeting pattern — check.

## Phase 5 — Draft the Plan

From the verified shortlist, assemble the semester:

- **No time conflicts** across selected sections (overlapping meetings disqualify a pair)
- **Total credits** within ±3 of the student's target load
- **Corequisites included** (e.g., a lab required with a lecture — the tool will flag these)
- **Constraint-aware** — minimize campus days for commuters, group classes on the same days if preferred, respect online caps

Record per course: CRN, discipline, number, title, credits, days, time, campus, instructor, seats remaining.

## Phase 6 — Validate the Plan

Run the full plan against this checklist before presenting:

- [ ] Every course has an explicit CRN from a real, currently-open section
- [ ] No time conflicts — re-check days × times across the whole plan
- [ ] Total credits matches the student's target load
- [ ] Every course satisfies a specific requirement in `remaining`
- [ ] All prereq chains are resolved (including prereqs for future-term courses)
- [ ] Every Phase 2 constraint is honored

If any item fails, return to the phase that owns it. **Do not present a failing plan.**

## Phase 7 — Present with Decisions

Structure the final output exactly like this so the student can review it:

1. **The Plan** — table with columns: Code, Title, Credits, CRN, Days/Time, Campus, Instructor
2. **Rationale** — one line per course: which `remaining` requirement it satisfies, and why this section was picked over others
3. **Risks & Trade-offs** — seats remaining, waitlist situations, any known instructor concerns (only if the student supplied a source like RMP), dependencies on other courses
4. **Fallbacks** — for each course, a backup section to use if the first closes before the student registers
5. **What's Not in the Plan** — any "Ready" course deferred to a later term, with the reason

## Phase 8 — Defer to the Advisor

Close with:

> This plan is based on DegreeWorks data from Phase 1. **Confirm with your academic advisor before registering.** The MCP server cannot register for anything — use Owl Express at the student's registration window.
"""
