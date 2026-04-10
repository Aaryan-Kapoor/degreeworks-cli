---
description: Access KSU DegreeWorks data – degree audit, remaining requirements, course info, schedule planning
allowed-tools: Bash(dw *)
---

# DegreeWorks Skill

You have access to the `dw` CLI which pulls data from KSU DegreeWorks.

## Getting Started

Run `dw --md dump` to get a full academic snapshot including:
- Student info and GPA
- Degree progress by requirement area
- Currently in-progress courses
- All completed courses with grades
- All remaining requirements

## Key Commands

```bash
dw --md dump                    # Full snapshot (start here)
dw --md dump --shallow          # Quick overview only
dw --md progress                # Progress bars by requirement
dw --md remaining               # Courses still needed
dw --md completed               # Courses done with grades
dw --md completed --transfers   # Include transfer credits
dw --md course CS 3305          # Course prereqs + sections
dw --json dump                  # Structured JSON output
```

## Schedule Planning

When helping plan semesters:
1. Start with `dw --md dump` for the full picture
2. Use `dw --md remaining` to identify what's needed
3. Look up prereqs with `dw --md course <DISC> <NUM>`
4. Consider: prereq chains, credit load (12-15/sem), section availability, schedule conflicts

## Auth Issues

If commands fail with auth errors, the student needs to run `dw login` to refresh cookies. Sessions last ~90 minutes.
