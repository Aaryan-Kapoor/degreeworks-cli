# degreeworks safety rules

- Use DegreeWorks **read-only**. The `dw` client makes only GET requests.
- Never register or drop courses, modify the audit, change student data, submit forms, or make POST/PUT/PATCH/DELETE requests. The client has no such methods — this is enforced in code, not policy.
- If a student asks to register for a course, direct them to Owl Express or their advisor. Never imply the CLI can take registration actions.
- Browser login (`dw login`) is for **authentication only**. Never scrape DegreeWorks through the browser — all data comes from `dw` commands.
- Prefer `--md` or `--json` for analysis; human tables are for display only.
- Always re-verify prereqs, offerings, and sections with `dw course` — never from memory or prior conversation. Catalogs and offerings change.
- If required data is blocked by auth, permissions, missing access, or command failure, stop and report the blocker. Do not answer from stale, partial, or guessed data unless the student explicitly accepts that tradeoff.
- Any schedule plan is advisory — always tell the student to confirm with their academic advisor before registering.
- Keep `~/.degreeworks/cookies.txt` and the browser profile out of public repositories.
