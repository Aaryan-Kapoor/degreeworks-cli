"""DegreeWorks API client.

STRICTLY READ-ONLY. This client only makes GET requests.
No POST, PUT, PATCH, or DELETE methods exist by design.
This tool cannot register for courses, modify audits, or change any data.
"""

import requests

from .config import (
    AUDIT_ACCEPT,
    AUDIT_ENDPOINT,
    BASE_URL,
    COURSE_ENDPOINT,
    DEFAULT_AUDIT_TYPE,
    DEFAULT_DEGREE,
    DEFAULT_SCHOOL,
)
from .errors import raise_for_status


class DegreeworksClient:
    """Read-only DegreeWorks API client. Only GET requests are supported."""

    def __init__(
        self,
        session: requests.Session,
        school: str = DEFAULT_SCHOOL,
        degree: str = DEFAULT_DEGREE,
        audit_type: str = DEFAULT_AUDIT_TYPE,
    ):
        self._session = session
        self._school = school
        self._degree = degree
        self._audit_type = audit_type

    def _get(self, path: str, params: dict = None, headers: dict = None) -> dict:
        """Make a GET request. This is the ONLY HTTP method this client supports."""
        resp = self._session.get(f"{BASE_URL}{path}", params=params, headers=headers or {})
        raise_for_status(resp)
        return resp.json()

    def get_audit(self, student_id: str) -> dict:
        """Fetch the full degree audit."""
        return self._get(
            AUDIT_ENDPOINT,
            params={
                "studentId": student_id,
                "school": self._school,
                "degree": self._degree,
                "is-process-new": "false",
                "audit-type": self._audit_type,
                "auditId": "",
                "include-inprogress": "true",
                "include-preregistered": "true",
                "aid-term": "",
            },
            headers={"accept": AUDIT_ACCEPT},
        )

    def get_course(self, discipline: str, number: str) -> dict:
        """Fetch course info (prereqs, sections, schedules)."""
        return self._get(
            COURSE_ENDPOINT,
            params={"discipline": discipline, "number": number},
        )
