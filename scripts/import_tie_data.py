#!/usr/bin/env python3
"""Import TIE irrigation projects into local Podium database via API.

Phase A: Import project structure (clients + projects with notes).
Targets localhost:3000 ONLY. TIE folder is read-only.
"""

import json
import os
import sys
import requests

API_BASE = "http://localhost:3000/api"
TIE_BASE = "/mnt/d/Dropbox/TIE"

# Existing RVi client ID (John Beggs)
RVI_CLIENT_ID = "c-276ed920"

# ── Client definitions ──────────────────────────────────────────────
CLIENTS = [
    "Birdsall",
    "Bonfire",
    "Cheyenne",
    "DR Horton",
    "Kelly",
    "Landmark",
    "Legacy Park",
    "Mosaic",
    "Pacific Rim",
    # RVi Planning — already exists as c-276ed920
    "Scotchboy",
    "TBG",
]

# ── Project definitions ─────────────────────────────────────────────
# (client_name, project_name, data_path_relative, status, md_file_relative_or_None)
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
    # Ave South SKIPPED — already exists
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
        # Truncate very long notes to 10KB
        if len(content) > 10000:
            content = content[:10000] + "\n\n... (truncated)"
        return content
    except Exception as e:
        print(f"  [warn] Could not read {relative_path}: {e}")
        return None


def create_clients():
    """Create clients via API, return name->id mapping."""
    client_map = {"RVi Planning": RVI_CLIENT_ID}

    for name in CLIENTS:
        resp = requests.post(f"{API_BASE}/clients", json={"name": name})
        if resp.status_code == 201:
            cid = resp.json()["id"]
            client_map[name] = cid
            print(f"  + Client: {name} -> {cid}")
        else:
            print(f"  ! Client {name} failed: {resp.status_code} {resp.text}")
            sys.exit(1)

    return client_map


def create_projects(client_map):
    """Create projects via API with client links and notes."""
    created = 0
    for client_name, project_name, data_rel, status, md_rel in PROJECTS:
        client_id = client_map.get(client_name)
        if not client_id:
            print(f"  ! No client_id for {client_name}, skipping {project_name}")
            continue

        data_path = os.path.join(TIE_BASE, data_rel)
        notes = read_md_notes(md_rel)

        payload = {
            "project_name": project_name,
            "client_id": client_id,
            "status": status,
            "data_path": data_path,
        }
        if notes:
            payload["notes"] = notes

        resp = requests.post(f"{API_BASE}/projects", json=payload)
        if resp.status_code == 200 or resp.status_code == 201:
            pid = resp.json()["id"]
            has_notes = "with notes" if notes else "no notes"
            print(f"  + Project: {project_name} -> {pid} ({status}, {has_notes})")
            created += 1
        else:
            print(f"  ! Project {project_name} failed: {resp.status_code} {resp.text}")

    return created


def main():
    # Verify server is running
    try:
        resp = requests.get(f"{API_BASE}/clients", timeout=3)
        resp.raise_for_status()
    except Exception as e:
        print(f"Server not reachable at {API_BASE}: {e}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("TIE -> Podium Import (Phase A: Structure + Notes)")
    print(f"{'='*60}\n")

    print("Creating 11 clients...")
    client_map = create_clients()
    print(f"\n  Total clients mapped: {len(client_map)}\n")

    print(f"Creating {len(PROJECTS)} projects...")
    count = create_projects(client_map)
    print(f"\n  Total projects created: {count}")

    # Verify
    print(f"\n{'='*60}")
    print("Verification")
    print(f"{'='*60}\n")

    clients = requests.get(f"{API_BASE}/clients").json()
    projects = requests.get(f"{API_BASE}/projects").json()
    print(f"  Clients in DB: {len(clients)}")
    print(f"  Projects in DB: {len(projects)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
