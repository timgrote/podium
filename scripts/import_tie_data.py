#!/usr/bin/env python3
"""Import TIE irrigation projects into local Podium database via API.

Phase A: Import project structure (clients + contacts + projects with notes).
Targets localhost:3000 ONLY. TIE folder is read-only.

Clients = companies (RVi Planning, DR Horton, TBG, etc.)
Contacts = people at those companies (John Beggs, Jenn Simmons, etc.)
"""

import json
import os
import sys
import requests
import psycopg2
import psycopg2.extras

API_BASE = "http://localhost:3000/api"
TIE_BASE = "/mnt/d/Dropbox/TIE"
DB_URL = os.environ.get(
    "CONDUCTOR_DATABASE_URL",
    "postgresql://conductor:conductor@localhost:5432/conductor",
)

# ── Client definitions (companies) ───────────────────────────────────
CLIENTS = [
    {"name": "Birdsall"},
    {"name": "Bonfire"},
    {"name": "Cheyenne"},
    {"name": "DR Horton"},
    {"name": "Kelly"},
    {"name": "Landmark"},
    {"name": "Legacy Park"},
    {"name": "Mosaic"},
    {"name": "Pacific Rim"},
    {"name": "RVi Planning"},
    {"name": "Scotchboy"},
    {"name": "TBG"},
]

# ── Contact definitions (people at companies) ────────────────────────
# Each contact is linked to a client company and has a default role.
CONTACTS = [
    {"name": "John Beggs", "email": "jbeggs@rviplanning.com", "client": "RVi Planning", "role": "Project Manager"},
    {"name": "Melanie Carpenter", "client": "RVi Planning", "role": "Project Manager"},
    {"name": "Shelley LaMastra", "client": "RVi Planning", "role": "Project Manager"},
    {"name": "Jenn Simmons", "client": "DR Horton", "role": "Project Manager"},
    {"name": "Kelly Hyzy", "client": "Kelly", "role": "Project Manager"},
]

# ── Default PM per client (used when project MD doesn't specify) ─────
DEFAULT_PM = {
    "RVi Planning": "John Beggs",
    "DR Horton": "Jenn Simmons",
    "Kelly": "Kelly Hyzy",
}

# ── Per-project PM overrides (from markdown frontmatter) ─────────────
PROJECT_PM_OVERRIDES = {
    "Evans PD": "Melanie Carpenter",
    "The Mark": "John Beggs",
}

# ── Project definitions ──────────────────────────────────────────────
# (client_name, project_name, dropbox_path_relative, status, md_file_relative_or_None)
PROJECTS = [
    ("Birdsall", "Gateway at Prospect", "Birdsall/Gateway at Prospect", "invoiced", "Birdsall/Gateway at Prospect/Gateway at Prospect.md"),
    ("Birdsall", "HL 21", "Birdsall/HL 21", "invoiced", "Birdsall/HL 21/HL 21.md"),
    ("Birdsall", "HL Community Center", "Birdsall/HL Community Center", "invoiced", "Birdsall/HL Community Center/HL Community.md"),
    ("Birdsall", "River Trails", "Birdsall/River Trails", "invoiced", "Birdsall/River Trails/River Trails.md"),
    ("Bonfire", "Bonfire", "Bonfire", "invoiced", "Bonfire/Bonfire.md"),
    ("Cheyenne", "Arboretum", "Cheyenne/Arboretum", "invoiced", "Cheyenne/Arboretum/Cheyenne Arboretum.md"),
    ("DR Horton", "Lee Farm Phase 1", "DR Horton/Lee Farm/Phase 1", "invoiced", "DR Horton/Lee Farm/Phase 1/Lee Farm Phase 1 Project.md"),
    ("DR Horton", "Lee Farm Phase 2", "DR Horton/Lee Farm/Phase 2", "invoiced", "DR Horton/Lee Farm/Phase 2/Lee Farm Filing 2.md"),
    ("DR Horton", "Mead Village", "DR Horton/Mead Village", "invoiced", "DR Horton/Mead Village/Mead Village.md"),
    ("DR Horton", "Silver Peaks", "DR Horton/Silver Peaks", "invoiced", None),
    ("Kelly", "Cross Family Church", "Kelly/Cross Family Church", "invoiced", "Kelly/Cross Family Church/Project Overview.md"),
    ("Kelly", "MMR", "Kelly/MMR", "invoiced", "Kelly/MMR/MMR.md"),
    ("Landmark", "Pena Station", "Landmark/Pena Station", "invoiced", "Landmark/Pena Station/Pena Station F2-4 Project.md"),
    ("Landmark", "Timnath 8th", "Landmark/Timnath 8th", "invoiced", None),
    ("Legacy Park", "Legacy Park", "Legacy Park", "invoiced", "Legacy Park/Legacy Park Project.md"),
    ("Mosaic", "Willox Lane", "Mosaic/Willox Lane", "invoiced", None),
    ("Pacific Rim", "GUAM", "Pacific Rim/GUAM", "proposal", None),
    ("RVi Planning", "Aurora Animal Shelter", "RVi Planning/Aurora Animal Shelter", "invoiced", "RVi Planning/Aurora Animal Shelter/Aurora Animal Shelter.md"),
    ("RVi Planning", "Ave South", "RVi Planning/Ave South", "invoiced", None),
    ("RVi Planning", "Buxton Hotel", "RVi Planning/Buxton Hotel", "invoiced", "RVi Planning/Buxton Hotel/Buxton Hotel.md"),
    ("RVi Planning", "CPMP", "RVi Planning/CPMP", "invoiced", "RVi Planning/CPMP/CPMP.md"),
    ("RVi Planning", "CPW", "RVi Planning/CPW", "invoiced", "RVi Planning/CPW/CPW.md"),
    ("RVi Planning", "Cheyenne Botanic Garden", "RVi Planning/Cheyenne Botanic Garden", "invoiced", "RVi Planning/Cheyenne Botanic Garden/Cheyenne Botanic Garden.md"),
    ("RVi Planning", "Erie PD", "RVi Planning/Erie PD", "invoiced", "RVi Planning/Erie PD/Erie PD.md"),
    ("RVi Planning", "Evans PD", "RVi Planning/Evans PD", "invoiced", "RVi Planning/Evans PD/Evans PD.md"),
    ("RVi Planning", "JDS", "RVi Planning/JDS", "invoiced", "RVi Planning/JDS/JDS.md"),
    ("RVi Planning", "The Mark", "RVi Planning/The Mark", "invoiced", "RVi Planning/The Mark/The Mark.md"),
    ("RVi Planning", "UW", "RVi Planning/UW", "invoiced", "RVi Planning/UW/UW.md"),
    ("Scotchboy", "Columbaria", "Scotchboy/Columbaria", "invoiced", None),
    ("Scotchboy", "Pershing Point", "Scotchboy/Pershing Point", "invoiced", "Scotchboy/Pershing Point/Pershing Point.md"),
    ("TBG", "Aurora Storage", "TBG/Aurora Storage", "invoiced", None),
    ("TBG", "Baseline 760", "TBG/Baseline 760", "invoiced", None),
    ("TBG", "FNB Bank", "TBG/FNB Bank", "invoiced", None),
    ("TBG", "Heartside Hill", "TBG/Heartside Hill", "invoiced", "TBG/Heartside Hill/Heartside Gardens.md"),
    ("TBG", "Hunter's Run", "TBG/Hunter's Run", "invoiced", None),
    ("TBG", "Monument Fire 3", "TBG/Monument Fire 3", "invoiced", "TBG/Monument Fire 3/Monument Fire 3.md"),
    ("TBG", "Monument Garage Condo", "TBG/Monument Garage Condo", "invoiced", None),
    ("TBG", "Respite", "TBG/Respite", "invoiced", None),
    ("TBG", "VC Cheyenne", "TBG/VC Cheyenne", "invoiced", "TBG/VC Cheyenne/VC Cheyenne.md"),
]


def read_md_notes(relative_path):
    """Read an MD file and return its contents as notes, or None."""
    if not relative_path:
        return None
    full_path = os.path.join(TIE_BASE, relative_path)
    if not os.path.exists(full_path):
        print(f"  [note] MD file not found: {relative_path}")
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated)"
        return content
    except Exception as e:
        print(f"  [warn] Could not read {relative_path}: {e}")
        return None


def generate_id(prefix):
    """Generate an 8-char UUID with prefix, matching app/utils.py."""
    import uuid
    return prefix + uuid.uuid4().hex[:8]


def create_clients_direct(conn, db):
    """Create client companies directly in DB, return name->id mapping."""
    client_map = {}
    for client in CLIENTS:
        cid = generate_id("c-")
        db.execute(
            "INSERT INTO clients (id, name, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
            (cid, client["name"]),
        )
        client_map[client["name"]] = cid
        print(f"  + Client (company): {client['name']} -> {cid}")
    conn.commit()
    return client_map


def create_contacts_direct(conn, db, client_map):
    """Create contact people directly in DB, return name->id mapping."""
    contact_map = {}
    for contact in CONTACTS:
        client_id = client_map.get(contact["client"])
        if not client_id:
            print(f"  ! No client for contact {contact['name']}, skipping")
            continue
        cid = generate_id("ct-")
        db.execute(
            "INSERT INTO contacts (id, name, email, role, client_id, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
            (cid, contact["name"], contact.get("email"), contact["role"], client_id),
        )
        contact_map[contact["name"]] = {"id": cid, "email": contact.get("email")}
        print(f"  + Contact: {contact['name']} ({contact['role']}) -> {cid} [client: {contact['client']}]")
    conn.commit()
    return contact_map


def create_projects_via_api(client_map, contact_map):
    """Create projects via API, then update pm_name/pm_email directly."""
    created = 0
    project_ids = {}

    for client_name, project_name, data_rel, status, md_rel in PROJECTS:
        client_id = client_map.get(client_name)
        if not client_id:
            print(f"  ! No client_id for {client_name}, skipping {project_name}")
            continue

        notes = read_md_notes(md_rel)

        payload = {
            "project_name": project_name,
            "client_id": client_id,
            "status": status,
            "dropbox_path": data_rel,
        }
        if notes:
            payload["notes"] = notes

        resp = requests.post(f"{API_BASE}/projects", json=payload)
        if resp.status_code in (200, 201):
            pid = resp.json()["id"]
            has_notes = "with notes" if notes else "no notes"
            project_ids[project_name] = pid

            # Determine PM for this project
            pm_name = PROJECT_PM_OVERRIDES.get(project_name) or DEFAULT_PM.get(client_name)
            pm_suffix = ""
            if pm_name:
                pm_contact = contact_map.get(pm_name, {})
                pm_email = pm_contact.get("email")
                update = {"pm_name": pm_name}
                if pm_email:
                    update["pm_email"] = pm_email
                requests.patch(f"{API_BASE}/projects/{pid}", json=update)
                pm_suffix = f", PM: {pm_name}"

            print(f"  + Project: {project_name} -> {pid} ({status}, {has_notes}{pm_suffix})")
            created += 1
        else:
            print(f"  ! Project {project_name} failed: {resp.status_code} {resp.text}")

    return created, project_ids


def main():
    # Verify server is running
    try:
        resp = requests.get(f"{API_BASE}/clients", timeout=3)
        resp.raise_for_status()
    except Exception as e:
        print(f"Server not reachable at {API_BASE}: {e}")
        sys.exit(1)

    # Connect directly for client/contact creation (no API for contacts yet)
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    db = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print(f"\n{'='*60}")
    print("TIE -> Podium Import (Phase A: Structure + Contacts + Notes)")
    print(f"{'='*60}\n")

    print(f"Creating {len(CLIENTS)} client companies...")
    client_map = create_clients_direct(conn, db)
    print(f"\n  Total clients: {len(client_map)}\n")

    print(f"Creating {len(CONTACTS)} contacts...")
    contact_map = create_contacts_direct(conn, db, client_map)
    print(f"\n  Total contacts: {len(contact_map)}\n")

    print(f"Creating {len(PROJECTS)} projects...")
    count, project_ids = create_projects_via_api(client_map, contact_map)
    print(f"\n  Total projects created: {count}")

    conn.close()

    # Verify
    print(f"\n{'='*60}")
    print("Verification")
    print(f"{'='*60}\n")

    clients = requests.get(f"{API_BASE}/clients").json()
    projects = requests.get(f"{API_BASE}/projects").json()
    print(f"  Clients in DB: {len(clients)}")
    print(f"  Projects in DB: {len(projects)}")

    # Show PM coverage
    with_pm = sum(1 for p in projects if p.get("pm_name"))
    print(f"  Projects with PM: {with_pm}/{len(projects)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
