"""Constants and paths."""

import json
import os
from pathlib import Path

BASE_URL = "https://degreeworks.kennesaw.edu"
AUDIT_ENDPOINT = "/api/audit"
COURSE_ENDPOINT = "/api/course-link"

CONFIG_DIR = Path.home() / ".degreeworks"
COOKIES_FILE = CONFIG_DIR / "cookies.txt"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "DNT": "1",
    "Referer": f"{BASE_URL}/worksheets/WEB31",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

AUDIT_ACCEPT = "application/vnd.net.hedtech.degreeworks.dashboard.audit.v1+json"

# Fallback defaults if no config file and no env overrides
DEFAULT_SCHOOL = "US"  # Undergraduate Semester
DEFAULT_DEGREE = "BS"  # Bachelor of Science
DEFAULT_AUDIT_TYPE = "AA"


def load_config() -> dict:
    """Load CLI config (school, degree, audit_type).

    Priority: env vars > config.json > hardcoded defaults.
    """
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}

    return {
        "school": os.environ.get("DEGREEWORKS_SCHOOL", data.get("school", DEFAULT_SCHOOL)),
        "degree": os.environ.get("DEGREEWORKS_DEGREE", data.get("degree", DEFAULT_DEGREE)),
        "audit_type": os.environ.get("DEGREEWORKS_AUDIT_TYPE", data.get("audit_type", DEFAULT_AUDIT_TYPE)),
    }


def save_config(school: str, degree: str, audit_type: str = DEFAULT_AUDIT_TYPE):
    """Persist config to ~/.degreeworks/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"school": school, "degree": degree, "audit_type": audit_type}, indent=2)
    )
