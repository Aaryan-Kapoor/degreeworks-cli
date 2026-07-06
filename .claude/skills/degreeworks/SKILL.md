---
name: degreeworks
description: Plan a KSU student's exact next semester — real sections, times, CRNs, and verified prerequisite chains — via the deterministic 8-phase schedule-planning protocol, backed by read-only DegreeWorks audit and course-catalog data. Use when the student asks to plan a semester, pick courses, build a schedule, break a prereq bottleneck, or check degree progress / remaining requirements.
allowed-tools: Bash(dw *) Read
---

# DegreeWorks Skill

You have access to the read-only `dw` CLI which pulls KSU DegreeWorks data. Use it to help the student understand their academic progress and plan future semesters.

## Before anything else: read AGENTS.md

**Your first action when this skill is invoked is to read [`AGENTS.md`](../../../AGENTS.md) in the project root.** It contains:

- The full **8-phase Schedule Planning Protocol** — follow it exactly when the student asks you to plan a semester, pick courses, or build a schedule
- The complete `dw` command reference with every flag
- Auth recovery procedures, config env vars, grade codes, and read-only safety rules

`AGENTS.md` is the single source of truth for this project and is shared across every agent harness. It supersedes anything you think you remember about the CLI.

## Quick decision tree

- **Student asks a simple informational question** (e.g. "what's my GPA?", "am I registered for MATH 2202?") → run one `dw` command and answer. No protocol needed.
- **Student asks to plan a semester, pick courses, or build a schedule** → follow the 8-phase protocol in `AGENTS.md` exactly. Do not skip phases, do not substitute memory for CLI verification, do not assume constraints.
- **Auth errors or unclear state** → `dw whoami` first, then follow the recovery procedure in `AGENTS.md`.

## Why read AGENTS.md instead of embedding the instructions here

There is one source of truth so agent instructions don't drift across harnesses. `CLAUDE.md` imports `AGENTS.md` at session start (so it's already in context in Claude Code), and this skill explicitly reads it too — both because skills can be invoked inside forked subagent contexts where `CLAUDE.md` may not be loaded, and so that any update to `AGENTS.md` is picked up immediately without needing to touch this file.

**Do not add instructions here. Update `AGENTS.md` in the project root.**
