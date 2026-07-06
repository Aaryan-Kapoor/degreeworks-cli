# dw command reference

Global flags go **before** the subcommand. `--md` = markdown (best for AI),
`--json` = structured, no flag = human tables with Unicode progress bars.

## Auth
- `dw login` — capture cookies via KSU SSO (opens a Chromium browser via Playwright). Auto-detects the student's `school` and `degree` codes from the first audit request and saves them to `~/.degreeworks/config.json`.
- `dw login --headless` — refresh cookies from the saved browser profile with no visible window (needs a prior interactive login).
- `dw whoami` — name, student ID, token expiry timestamp, time remaining, status (`ACTIVE`/`EXPIRED`). Works with expired tokens.
- `dw doctor` — checks install, PATH, Playwright/Chromium, saved session, token validity, and a live read-only API call; prints the exact next command. `dw --json doctor` for machine output.

## Academic state
- `dw progress` — overall degree % and per-block completion (Degree, State Legislative Requirements, Honors if applicable, each Gen Ed area, Major, etc.).
- `dw remaining` — every course still needed, grouped by requirement; includes specific courses and free-text requirements ("Complete 9 credits of CS 3000–4000 level").
- `dw completed` — completed + in-progress courses grouped by term, with grades. `--transfers` includes transfer credits.
- `dw audit` — full degree-audit tree: every requirement block, sub-rule, status (`DONE`/`IP`/`NEED`/%), applied and needed courses. Use to understand *why* a course counts toward a requirement.

## Courses
- `dw course DISCIPLINE NUMBER` (e.g. `dw course CS 3305`) — description, prerequisites as parsed boolean logic, and all scheduled sections for published terms.
  - Prereqs render like: `((MATH 2345 (min C) OR CSE 2300 (min C)) AND ((CSE 1322 (min C) AND CSE 1322L (min C)) OR MTRE 2710 (min B)))`
  - Sections include: term, CRN, days (`MWF`, `TR`), time, building/room, instructor, campus, enrollment (current/max), waitlist.

## Snapshot
- `dw dump` — full academic snapshot in one command (use in Phase 1 of the planning protocol). `--shallow` = progress + in-progress only. `--json` = structured snapshot.

## Configuration
Reads `~/.degreeworks/config.json` (auto-populated during `dw login`). Override with env vars (priority: env > config.json > defaults):

| Env var | Purpose | Default |
|---|---|---|
| `DEGREEWORKS_SCHOOL` | Banner school code | `US` (undergrad) |
| `DEGREEWORKS_DEGREE` | Degree code (`BS`, `BA`, `BBA`, `BFA`, …) | `BS` |
| `DEGREEWORKS_AUDIT_TYPE` | Audit type | `AA` |

Files under `~/.degreeworks/`: `cookies.txt` (session cookies — keep private),
`config.json` (school/degree/audit_type), `browser_profile/` (Playwright's
persistent SSO session).
