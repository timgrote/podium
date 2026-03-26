"""Resolve project assignments for activity items using overrides, path mappings, and project data_path."""


def resolve_projects(items: list[dict], employee_id: str, db) -> list[dict]:
    """Annotate activity items with project info based on matching hierarchy."""
    # Load overrides for this employee
    overrides = {}
    rows = db.execute(
        "SELECT source, source_key, project_id, dismissed FROM activity_overrides WHERE employee_id = %s",
        (employee_id,),
    ).fetchall()
    for r in rows:
        overrides[(r["source"], r["source_key"])] = r

    # Load active path mappings
    mappings = db.execute(
        "SELECT pattern, source, project_id FROM activity_path_mappings WHERE deleted_at IS NULL"
    ).fetchall()

    # Load all projects with data_path for implicit matching
    projects = db.execute(
        "SELECT id, name, data_path FROM projects WHERE deleted_at IS NULL AND data_path IS NOT NULL AND data_path != ''"
    ).fetchall()

    # Build project name lookup
    all_projects = db.execute(
        "SELECT id, name FROM projects WHERE deleted_at IS NULL"
    ).fetchall()
    names = {p["id"]: p["name"] for p in all_projects}

    for item in items:
        source_key = item["id"]
        source = item["source"]
        source_path = (item.get("source_path") or "").replace("\\", "/").lower()

        # 1. Check overrides (exact match)
        override = overrides.get((source, source_key))
        if override:
            if override["dismissed"]:
                item["project_id"] = None
                item["project_name"] = None
                item["mapping_source"] = "dismissed"
                continue
            item["project_id"] = override["project_id"]
            item["project_name"] = names.get(override["project_id"])
            item["mapping_source"] = "manual"
            continue

        # 2. Check path mappings (substring match)
        matched = False
        for m in mappings:
            if m["source"] == source and m["pattern"].replace("\\", "/").lower() in source_path:
                item["project_id"] = m["project_id"]
                item["project_name"] = names.get(m["project_id"])
                item["mapping_source"] = "auto"
                matched = True
                break

        if matched:
            continue

        # 3. Check project data_path (implicit match)
        for p in projects:
            dp = (p["data_path"] or "").replace("\\", "/").lower()
            if dp and dp in source_path:
                item["project_id"] = p["id"]
                item["project_name"] = p["name"]
                item["mapping_source"] = "auto"
                matched = True
                break

        if not matched:
            item["project_id"] = None
            item["project_name"] = None
            item["mapping_source"] = None

    return items
