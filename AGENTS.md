# DegreeWorks CLI – Agent Instructions

This CLI provides read-only access to a KSU student's DegreeWorks degree audit and course catalog. Use it to help students plan their remaining semesters.

## Setup

The student must run `dw login` once to capture browser cookies. After that, all commands work until cookies expire (~90 minutes). When they expire, run `dw login` again.

## Commands

| Command | What it does |
|---------|-------------|
| `dw --md dump` | **Start here.** Full academic snapshot in markdown. |
| `dw --md dump --shallow` | Quick overview: progress + in-progress courses only. |
| `dw --md progress` | Degree progress by requirement area. |
| `dw --md remaining` | All courses still needed for graduation. |
| `dw --md completed` | All courses completed with grades. |
| `dw --md completed --transfers` | Include transfer credits. |
| `dw --md course CS 3305` | Course info: description, prereqs, sections, schedules. |
| `dw whoami` | Verify auth is working. |

Always use `--md` for markdown output (easiest to parse). Use `--json` if you need structured data.

## Workflow for Schedule Planning

1. Run `dw --md dump` to get the full picture
2. Identify remaining requirements with `dw --md remaining`
3. Look up specific courses with `dw --md course <DISCIPLINE> <NUMBER>` to check prereqs and available sections
4. Build a semester plan considering:
   - Prerequisites (check with `dw course`)
   - Credit load (typically 12-15 per semester)
   - Course availability (not all courses offered every semester)
   - Schedule conflicts (check days/times from course sections)

## Safety: Read-Only by Design

This tool is **strictly read-only**. It can only make GET requests to the DegreeWorks API.
It **cannot** and **must not**:
- Register or drop courses
- Modify the degree audit
- Change any student data
- Submit any forms
- Make POST, PUT, PATCH, or DELETE requests

If a student asks you to register for a course, direct them to do it manually through Owl Express or their advisor.

## Other Notes

- Cookie sessions expire. If you get auth errors, ask the student to run `dw login` again.
- The audit reflects DegreeWorks' view, which may lag behind very recent registrations.
- Course sections shown are for the current/upcoming term only.
