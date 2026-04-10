"""Parse DegreeWorks audit JSON into structured data."""

TERM_SEASONS = {"01": "Spring", "05": "Summer", "08": "Fall"}


def _term_label(term: str) -> str:
    """Convert '202501' → 'Spring 2025'."""
    if not term or len(term) < 6:
        return term or ""
    year = term[:4]
    month = term[4:6]
    return f"{TERM_SEASONS.get(month, month)} {year}"


def _walk_courses_applied(rule: dict, out: list):
    """Recursively collect all courses applied to rules."""
    applied = rule.get("classesAppliedToRule", {})
    for c in applied.get("classArray", []):
        out.append({
            "course": f"{c['discipline']} {c['number']}",
            "discipline": c["discipline"],
            "number": c["number"],
            "credits": c.get("credits", ""),
            "grade": c.get("letterGrade", ""),
            "term": c.get("term", ""),
            "term_label": _term_label(c.get("term", "")),
            "rule_label": rule.get("label", ""),
        })
    for sub in rule.get("ruleArray", []):
        _walk_courses_applied(sub, out)


def _walk_advice(rule: dict, out: list):
    """Recursively collect all advised (needed) courses from rules."""
    advice = rule.get("advice", {})
    for c in advice.get("courseArray", []):
        if c.get("hideFromAdvice") == "Yes":
            continue
        out.append({
            "course": f"{c['discipline']} {c['number']}",
            "discipline": c["discipline"],
            "number": c["number"],
            "title": c.get("title", ""),
            "credits": c.get("credits", ""),
            "has_prereqs": c.get("prerequisiteExists", "") == "Y",
            "rule_label": rule.get("label", ""),
        })
    # Also collect proxy advice (free-text)
    proxy = rule.get("proxyAdvice", {})
    if proxy.get("textList"):
        out.append({
            "course": "",
            "text": " ".join(proxy["textList"]),
            "rule_label": rule.get("label", ""),
        })
    for sub in rule.get("ruleArray", []):
        _walk_advice(sub, out)


def parse_header(audit: dict) -> dict:
    """Extract high-level student/degree info."""
    h = audit.get("auditHeader", {})
    deg_info = audit.get("degreeInformation", {})
    deg_data = {}
    if deg_info.get("degreeDataArray"):
        deg_data = deg_info["degreeDataArray"][0]
    return {
        "student_id": h.get("studentId", ""),
        "name": h.get("studentName", ""),
        "email": h.get("studentEmail", ""),
        "gpa": h.get("degreeworksGpa", ""),
        "percent_complete": h.get("percentComplete", ""),
        "credits_applied": _sum_credits(h),
        "level": deg_data.get("studentLevelLiteral", ""),
        "degree": deg_data.get("degreeLiteral", ""),
        "catalog_year": deg_data.get("catalogYearLit", ""),
        "active_term": deg_data.get("activeTermLiteral", ""),
    }


def _sum_credits(header: dict) -> str:
    """Sum resident + transfer applied credits."""
    try:
        res = int(header.get("residentApplied", 0))
        res_ip = int(header.get("residentAppliedInProgress", 0))
        tr = int(header.get("transferApplied", 0))
        return str(res + res_ip + tr)
    except (ValueError, TypeError):
        return ""


def parse_blocks(audit: dict) -> list[dict]:
    """Parse blockArray into a flat list of requirement blocks."""
    blocks = []
    for b in audit.get("blockArray", []):
        block = {
            "id": b.get("requirementId", ""),
            "type": b.get("requirementType", ""),
            "value": b.get("requirementValue", ""),
            "title": b.get("title", ""),
            "percent_complete": b.get("percentComplete", ""),
            "gpa": b.get("gpa", ""),
            "credits_applied": b.get("creditsApplied", ""),
            "rules": _parse_rules(b.get("ruleArray", [])),
        }
        blocks.append(block)
    return blocks


def _parse_rules(rules: list) -> list[dict]:
    """Parse ruleArray into structured rules."""
    out = []
    for r in rules:
        rule = {
            "label": r.get("label", ""),
            "percent_complete": r.get("percentComplete", ""),
            "rule_type": r.get("ruleType", ""),
            "in_progress": r.get("inProgressIncomplete", "") == "Yes",
            "classes_applied": r.get("classesApplied", "0"),
            "credits_applied": r.get("creditsApplied", "0"),
        }
        # Completed courses for this rule
        applied = r.get("classesAppliedToRule", {})
        rule["courses_applied"] = []
        for c in applied.get("classArray", []):
            rule["courses_applied"].append({
                "course": f"{c['discipline']} {c['number']}",
                "credits": c.get("credits", ""),
                "grade": c.get("letterGrade", ""),
                "term": c.get("term", ""),
                "term_label": _term_label(c.get("term", "")),
            })
        # Advised (needed) courses
        advice = r.get("advice", {})
        rule["courses_needed"] = []
        for c in advice.get("courseArray", []):
            if c.get("hideFromAdvice") == "Yes":
                continue
            rule["courses_needed"].append({
                "course": f"{c['discipline']} {c['number']}",
                "title": c.get("title", ""),
                "credits": c.get("credits", ""),
                "has_prereqs": c.get("prerequisiteExists", "") == "Y",
            })
        # Proxy advice
        proxy = r.get("proxyAdvice", {})
        if proxy.get("textList"):
            rule["proxy_advice"] = " ".join(proxy["textList"])
        # Sub-rules
        rule["sub_rules"] = _parse_rules(r.get("ruleArray", []))
        out.append(rule)
    return out


def parse_completed(audit: dict) -> list[dict]:
    """Extract all completed/in-progress courses from classInformation."""
    classes = audit.get("classInformation", {})
    out = []
    for c in classes.get("classArray", []):
        out.append({
            "course": f"{c.get('discipline', '')} {c.get('number', '')}",
            "discipline": c.get("discipline", ""),
            "number": c.get("number", ""),
            "title": c.get("courseTitle", ""),
            "credits": c.get("credits", ""),
            "grade": c.get("letterGrade", ""),
            "term": c.get("term", ""),
            "term_label": _term_label(c.get("term", "")),
            "in_progress": c.get("inProgress", "") == "Y",
            "transfer": c.get("transfer", "") == "T",
            "transfer_school": c.get("transferSchool", ""),
        })
    return out


def parse_in_progress(audit: dict) -> list[dict]:
    """Extract currently in-progress courses, enriched with titles from classInformation."""
    ip = audit.get("inProgress", {})
    # Build id -> title lookup from classInformation
    titles_by_id = {}
    for c in audit.get("classInformation", {}).get("classArray", []):
        if c.get("id"):
            titles_by_id[c["id"]] = c.get("courseTitle", "")

    out = []
    for c in ip.get("classArray", []):
        cid = c.get("id", "")
        out.append({
            "course": f"{c.get('discipline', '')} {c.get('number', '')}",
            "discipline": c.get("discipline", ""),
            "number": c.get("number", ""),
            "title": titles_by_id.get(cid, c.get("courseTitle", "")),
            "credits": c.get("credits", ""),
            "term": c.get("term", ""),
            "term_label": _term_label(c.get("term", "")),
        })
    return out


def parse_remaining(audit: dict) -> list[dict]:
    """Collect all remaining/needed courses across all blocks."""
    remaining = []
    for block in audit.get("blockArray", []):
        pct = block.get("percentComplete", "100")
        try:
            if float(pct) >= 100:
                continue
        except ValueError:
            pass
        for rule in block.get("ruleArray", []):
            _walk_advice(rule, remaining)
    return remaining


def parse_progress(audit: dict) -> dict:
    """Build a progress summary."""
    h = audit.get("auditHeader", {})
    blocks = audit.get("blockArray", [])

    block_progress = []
    for b in blocks:
        if b.get("requirementType") == "DEGREE":
            continue
        block_progress.append({
            "title": b.get("title", ""),
            "percent": b.get("percentComplete", "0"),
            "credits_applied": b.get("creditsApplied", "0"),
        })

    return {
        "percent_complete": h.get("percentComplete", ""),
        "gpa": h.get("degreeworksGpa", ""),
        "credits_applied": _sum_credits(h),
        "credits_needed": "120",
        "blocks": block_progress,
    }
