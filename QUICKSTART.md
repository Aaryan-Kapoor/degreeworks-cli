# Quickstart

## Install

```bash
git clone https://github.com/Aaryan-Kapoor/degreeworks-cli.git
cd degreeworks-cli
pip install -e ".[login]"
playwright install chromium
```

## Authenticate

```bash
dw login
```

This opens a browser. Log in with your KSU credentials. Cookies are saved automatically.

## Use

```bash
dw progress              # How close am I to graduating?
dw remaining             # What do I still need?
dw course CS 3305        # Prereqs, sections, schedules
dw --md dump             # Full snapshot (for AI agents)
```

## Use with AI

Point your AI tool at this project directory. The `AGENTS.md` file tells it how to use the CLI.

For Claude Code, the skill is pre-configured – just start asking about your schedule.
