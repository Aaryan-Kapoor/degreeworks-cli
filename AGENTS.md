# DegreeWorks CLI – Agent Instructions

This CLI provides **strictly read-only** access to a KSU student's DegreeWorks degree audit and course catalog. Use it to help students plan their remaining semesters.

## Setup

The student runs `dw login` once to capture browser cookies via KSU SSO. After that, all commands work until cookies expire.

- **Auth token**: 90-minute lifetime
- **Refresh token**: 8-hour lifetime (allows `dw login --headless` to refresh without re-login)
- When the auth token expires but the refresh token is alive, the CLI tells the student to run `dw login --headless`.
- When both expire, the student must run `dw login` interactively.

## Global Flags

Every command accepts these flags, placed **before** the subcommand:

| Flag | Purpose |
|---|---|
| `--json` | Structured JSON output (best for programmatic parsing) |
| `--md` | Markdown output (best for AI agents — easiest to read) |
| `--help` | Show help text (works without auth) |

**Default output** is human-readable tables with Unicode progress bars. For agent use, prefer `--md`.

## Complete Command Reference

### `dw login`
Capture cookies via KSU SSO. Opens a Chromium browser via Playwright.

```bash
dw login              # interactive – student logs in via SSO
dw login --headless   # refresh using saved browser profile (no UI)
```

During login, the CLI auto-detects the student's `school` and `degree` codes by intercepting the first audit API request and saves them to `~/.degreeworks/config.json`.

### `dw whoami`
Show current student info and token expiry. Works with expired tokens (useful for debugging auth).

```bash
dw whoami
```

Output: student name, ID, token expiration timestamp, time remaining, and auth status (`ACTIVE` or `EXPIRED`).

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

Each row: course code, title, credits, whether it has prerequisites, the requirement it satisfies.

### `dw completed`
Courses completed or in-progress, grouped by term.

```bash
dw --md completed               # KSU courses only
dw --md completed --transfers   # include transfer credits
```

Each row: course code, title, credits, grade (or `REGD` for in-progress), term.

### `dw audit`
Full degree audit tree with nested rules. Shows every requirement block, every sub-rule, the status of each rule (`DONE`/`IP`/`NEED`/percentage), applied courses, and needed courses. This is the most detailed view.

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
`((MATH 2345 (min C) OR CSE 2300 (min C)) AND ((CSE 1322 (min C) AND CSE 1322L (min C)) OR MTRE 2710 (min B) OR CPE 3000 (min B)))`

Sections include: term, CRN, days (e.g., `MWF`, `TR`), time, building/room, instructor, campus, enrollment (current/max), waitlist.

### `dw dump`
Full academic snapshot in a single command. **Start here** when you're new to the student's situation.

```bash
dw --md dump             # everything: progress + in-progress + completed + remaining + blocks
dw --md dump --shallow   # quick: progress + in-progress only
dw --json dump           # structured JSON snapshot
```

## Recommended Workflow for Schedule Planning

1. **Orient**: `dw --md dump` — get the full picture in one command
2. **Identify gaps**: `dw --md remaining` — focus on what's needed
3. **Check prereqs**: `dw --md course <DISC> <NUM>` for each candidate course — verify you can actually take it this semester
4. **Check availability**: Same `dw course` output shows which terms/sections are offered
5. **Plan the sequence**: Build a semester-by-semester plan respecting:
   - Prerequisite chains (if A requires B, take B first)
   - Credit load (12 = minimum full-time, 15 = typical, 18 = heavy)
   - Schedule conflicts (check days/times from section data)
   - Student-specific constraints (max online credits, campus preference, morning class limits, etc. — check `CLAUDE.md` if present)

## Safety: Read-Only by Design

This tool is **strictly read-only**. It can only make GET requests to the DegreeWorks API. It **cannot** and **must not**:
- Register or drop courses
- Modify the degree audit
- Change any student data
- Submit any forms
- Make POST, PUT, PATCH, or DELETE requests

The `DegreeworksClient` class in `src/degreeworks/client.py` literally has no method other than `_get()`, `get_audit()`, and `get_course()`. This is enforced in code, not just policy.

**If a student asks you to register for a course, direct them to Owl Express or their advisor.** Never imply the CLI can take registration actions.

## Configuration

The CLI reads config from `~/.degreeworks/config.json`, which is auto-populated during `dw login`. You can override any value with environment variables:

| Env var | Purpose | Default |
|---|---|---|
| `DEGREEWORKS_SCHOOL` | Banner school code (e.g., `US` for undergrad) | `US` |
| `DEGREEWORKS_DEGREE` | Degree code (`BS`, `BA`, `BBA`, `BFA`, etc.) | `BS` |
| `DEGREEWORKS_AUDIT_TYPE` | Audit type | `AA` |

Priority: env vars > config.json > hardcoded defaults.

The config file and cookies live at:
- `~/.degreeworks/cookies.txt` — session cookies
- `~/.degreeworks/config.json` — school/degree/audit_type
- `~/.degreeworks/browser_profile/` — Playwright's persistent browser state

## Auth Error Recovery

| Error | What it means | What to do |
|---|---|---|
| `No cookies found` | First time use, or cookies deleted | Run `dw login` |
| `Auth token expired, but refresh token is still valid` | 90 min lapsed | Run `dw login --headless` |
| `Session fully expired` | Both tokens dead (>8 hrs) | Run `dw login` |

Check `dw whoami` anytime to see exact token status without triggering an API call.

## Other Notes

- The audit reflects DegreeWorks' view, which may lag behind very recent registrations (sometimes up to 24 hours).
- `dw course` sections are only shown for terms the registrar has published — typically the current term and the next 1-2 upcoming terms.
- `REGD` as a grade means "registered/in-progress" — the student hasn't finished the course yet.
- `K` as a grade typically means "credit by exam" (AP credit, transfer with P/NP, etc.).
- Transfer courses have a `transfer: true` flag in `--json` output.
