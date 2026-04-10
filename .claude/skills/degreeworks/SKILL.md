---
description: Access KSU DegreeWorks data – degree audit, remaining requirements, completed courses, course info with prereqs and sections, progress tracking, and AI schedule planning
allowed-tools: Bash(dw *)
---

# DegreeWorks Skill

You have access to the `dw` CLI which pulls strictly read-only data from KSU DegreeWorks. Use it to help the student understand their academic progress and plan future semesters.

## Start Here

```bash
dw --md dump
```

This one command gives you:
- Student info (name, ID, GPA)
- Degree progress by requirement area (with percentages)
- Currently in-progress courses (including pre-registered for future terms)
- All completed courses with grades and terms
- All remaining requirements with credits and prereq flags

If you just need a quick orientation, use `dw --md dump --shallow` (progress + in-progress only).

## Complete Command List

All commands accept `--md` (markdown, recommended for AI) or `--json` (structured) as global flags placed **before** the subcommand.

```bash
# --- Auth ---
dw login                          # Interactive SSO login (Playwright browser)
dw login --headless               # Refresh cookies without UI (needs prior login)
dw whoami                         # Show student info + token expiry (works when expired)

# --- Snapshot ---
dw --md dump                      # Full academic snapshot (everything)
dw --md dump --shallow            # Quick: progress + in-progress only
dw --json dump                    # Same as above but structured JSON

# --- Progress ---
dw --md progress                  # Progress bars by requirement area
dw --md audit                     # Full nested audit tree with per-rule status
                                  #   (use this when you need to understand WHY
                                  #    a course counts toward a specific requirement)

# --- Courses ---
dw --md remaining                 # All courses still needed for graduation
dw --md completed                 # All completed/in-progress courses, grouped by term
dw --md completed --transfers     # Include transfer credits

# --- Course lookup ---
dw --md course CS 3305            # Description, parsed prereqs, all scheduled sections
dw --md course MATH 2202          # Same for any course
```

## Global Flags

| Flag | Purpose |
|---|---|
| `--md` | Markdown output — **use this by default** for agent work |
| `--json` | Structured JSON — use when you need to parse programmatically |
| `--help` | Show help for any command (works without auth) |

## Schedule Planning Workflow

1. **Orient**: `dw --md dump` — get the full picture
2. **Identify gaps**: `dw --md remaining` — see what's needed
3. **Check prereqs**: `dw --md course <DISC> <NUM>` for each candidate — verify you can take it now
4. **Check availability**: Same command shows all upcoming sections with days, times, CRNs, instructors, enrollment
5. **Use `dw --md audit`** if you need to understand why a specific course counts where, or to see the full rule tree
6. **Respect constraints**: check `CLAUDE.md` in the project root for student-specific rules (max online credits, preferred campus, morning class limits, etc.)

## Course Output Details

`dw course` returns:
- **Description**: full catalog text
- **Prerequisites**: parsed into a readable boolean expression, e.g.
  `((MATH 2345 (min C) OR CSE 2300 (min C)) AND (CSE 1322 (min C) AND CSE 1322L (min C)))`
- **Sections**: term, CRN, days (M/T/W/R/F/S/U), time, building+room, instructor, campus (Marietta/Kennesaw/Online), enrollment (current/max), waitlist

## Grade Codes You'll See

| Code | Meaning |
|---|---|
| `A`–`F` | Standard letter grade |
| `REGD` | Registered/in-progress (hasn't finished yet) |
| `K` | Credit by exam (AP, transfer with P/NP, etc.) |
| `W` | Withdrawn |
| `I` | Incomplete |

## Auth Recovery

If any command fails with auth errors:

- **"Auth token expired, but refresh token is still valid"** → student runs `dw login --headless` (no UI, ~5 seconds)
- **"Session fully expired"** → student runs `dw login` (interactive, requires SSO)
- Check status anytime with `dw whoami` (works even when expired)

## Read-Only Enforcement

The `dw` CLI is **strictly read-only by design**. The underlying HTTP client only has `_get()` — no POST, PUT, PATCH, or DELETE methods exist. It **cannot** register for courses, drop courses, modify the audit, or change any data in any way.

If the student asks you to register for something, direct them to Owl Express or their advisor. Do not imply the CLI can take registration actions.

## Config (Advanced)

The CLI auto-detects the student's `school`/`degree` codes during `dw login` and saves them to `~/.degreeworks/config.json`. You can override with env vars:

```bash
DEGREEWORKS_SCHOOL=US     # Banner school code
DEGREEWORKS_DEGREE=BS     # Degree code (BS, BA, BBA, BFA, BSN, etc.)
DEGREEWORKS_AUDIT_TYPE=AA # Audit type
```

Students shouldn't normally need to touch these.
