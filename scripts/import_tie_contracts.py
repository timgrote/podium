#!/usr/bin/env python3
"""Import contracts for TIE projects into Podium database.

This script creates contract records from two sources:
1. Professional format invoices (which contain the full contract breakdown)
2. Proposal PDFs (for projects without professional invoices)

The dashboard pipeline value = SUM(contracts.total_amount), so we need
contracts to make the pipeline stat work.

Run: python3 scripts/import_tie_contracts.py
Add --import to actually create records (default is preview-only).
"""

import json
import os
import re
import sys
import pdfplumber
import requests

API_BASE = "http://localhost:3000/api"
TIE_BASE = "/mnt/d/Dropbox/TIE"


# ── Phase 1: Extract contracts from professional format invoices ─────
#
# Professional format invoices contain the full contract task breakdown:
#   Task / Fee / % Complete / Previous Billing / Current Billing
#
# The LAST invoice for a project has the most complete picture of the
# contract (may include added tasks/changes). We use that one.
#
# Data we extract per project:
#   - contract_total (sum of all task fees)
#   - tasks: [{name, amount}] for contract_tasks
#
# Projects with professional format invoices (from extraction report):
#   Evans PD:           $4,000 (3 tasks)
#   Erie PD:            $4,000 (3 tasks)
#   CPMP:               $2,700 (3 tasks)
#   Mead Village:       $42,000 (7 tasks)
#   MMR:                $2,370 (2 tasks)
#   Monument Fire 3:    $2,400 (3 tasks)
#   The Mark Courtyards: $1,900 (3 tasks)
#   Aurora Animal Shelter: $3,415 (1 task)
#   FNB Bank:           $900 (1 task)
#   Pershing Point:     $1,800 (1 task)
#   Pena Station E2:    $5,303 (4 tasks)  -- 70% confidence, no invoice#
#   Pena Station F1F3:  $3,903 (3 tasks)  -- 70% confidence, no invoice#


def parse_money(s):
    if not s:
        return None
    cleaned = re.sub(r'[$\\s,]', '', str(s).strip())
    if cleaned in ('-', ''):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return None


def get_projects():
    """Get all projects with their invoice data."""
    resp = requests.get(f"{API_BASE}/projects")
    resp.raise_for_status()
    return resp.json()


def get_project_detail(project_id):
    """Get full project detail including invoices."""
    resp = requests.get(f"{API_BASE}/projects/{project_id}")
    resp.raise_for_status()
    return resp.json()


def extract_contract_from_invoices(data_path):
    """Find professional format invoices and extract contract data.

    Returns the contract data from the LAST professional invoice
    (most complete picture of the contract).
    """
    if not data_path or not os.path.isdir(data_path):
        return None

    # Find all invoice PDFs
    pdfs = []
    for root, dirs, files in os.walk(data_path):
        for f in files:
            if f.lower().endswith(".pdf") and "invoice" in f.lower():
                pdfs.append(os.path.join(root, f))

    if not pdfs:
        return None

    best_contract = None

    for pdf_path in sorted(pdfs):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            continue

        # Only process professional format
        if not any(kw in text for kw in ("% Complete", "Previous Fee", "Current Fee", "Professional Services")):
            continue

        # Extract task lines
        task_pattern = re.compile(
            r'^(.+?)\s+\$?([\d,]+\.?\d*)\s+([\d.]+)%?\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)\s*$',
            re.MULTILINE
        )

        tasks = []
        for m in task_pattern.finditer(text):
            name = m.group(1).strip()
            if name.lower() in ('task', 'total', 'previous fee', 'current fee'):
                continue
            fee = parse_money(m.group(2))
            if fee and fee > 0:
                tasks.append({"name": name, "amount": fee})

        if tasks:
            total = sum(t["amount"] for t in tasks)
            best_contract = {
                "total_amount": total,
                "tasks": tasks,
                "source": os.path.basename(pdf_path),
                "source_path": pdf_path,
            }
            # Keep going — last invoice wins (most complete)

    return best_contract


def find_proposal_total(data_path):
    """Look for proposal PDFs and try to extract a total fee.

    Fallback for projects without professional invoices.
    """
    if not data_path or not os.path.isdir(data_path):
        return None

    # Find proposal PDFs
    pdfs = []
    for root, dirs, files in os.walk(data_path):
        for f in files:
            if f.lower().endswith(".pdf") and "proposal" in f.lower():
                pdfs.append(os.path.join(root, f))

    for pdf_path in sorted(pdfs):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            continue

        # Look for total fee patterns
        total_match = re.search(r'(?:Total|TOTAL)\s+(?:Fee|FEE|Amount|AMOUNT)\s*:?\s*\$?([\d,]+\.?\d*)', text)
        if total_match:
            total = parse_money(total_match.group(1))
            if total and total > 0:
                return {
                    "total_amount": total,
                    "tasks": [],
                    "source": os.path.basename(pdf_path),
                    "source_path": pdf_path,
                }

    return None


def create_contract(project_id, contract_data, dry_run=True):
    """Create a contract + contract_tasks via the API (inline tasks)."""
    if dry_run:
        return {"id": "DRY-RUN", "total_amount": contract_data["total_amount"]}

    # Build inline tasks for the API
    api_tasks = []
    for task in contract_data.get("tasks", []):
        api_tasks.append({"name": task["name"], "amount": task["amount"]})

    payload = {
        "project_id": project_id,
        "total_amount": contract_data["total_amount"],
        "notes": f"Imported from: {contract_data.get('source', 'T&M invoices')}",
    }
    if api_tasks:
        payload["tasks"] = api_tasks

    resp = requests.post(f"{API_BASE}/contracts", json=payload)
    if resp.status_code not in (200, 201):
        print(f"  ! Contract creation failed: {resp.status_code} {resp.text[:200]}")
        return None

    return resp.json()


def main():
    dry_run = "--import" not in sys.argv

    projects = get_projects()
    print(f"Found {len(projects)} projects\n")

    contracts_from_invoices = []
    contracts_from_proposals = []
    needs_manual = []
    already_has_contract = []

    for proj in projects:
        detail = get_project_detail(proj["id"])
        project_name = proj.get("project_name", "?")

        # Skip if already has a contract
        if detail.get("contracts") and len(detail["contracts"]) > 0:
            already_has_contract.append(project_name)
            continue

        data_path = detail.get("data_path")

        # Phase 1: Try professional invoice extraction
        contract = extract_contract_from_invoices(data_path)
        if contract:
            contract["project_id"] = proj["id"]
            contract["project_name"] = project_name
            contracts_from_invoices.append(contract)
            continue

        # Phase 2: Try proposal extraction
        proposal = find_proposal_total(data_path)
        if proposal:
            proposal["project_id"] = proj["id"]
            proposal["project_name"] = project_name
            contracts_from_proposals.append(proposal)
            continue

        # Phase 3: Check if we have invoices (T&M fallback)
        total_invoiced = proj.get("total_invoiced", 0)
        if total_invoiced > 0:
            needs_manual.append({
                "project_name": project_name,
                "project_id": proj["id"],
                "total_invoiced": total_invoiced,
                "note": "T&M project — no contract or proposal found. Could create contract = sum of invoices.",
            })
        # else: no invoices, no contract, no proposal — skip

    # Report
    print(f"{'='*60}")
    print(f"CONTRACT IMPORT PLAN")
    print(f"{'='*60}\n")

    print(f"Phase 1 — From professional invoices: {len(contracts_from_invoices)}")
    for c in contracts_from_invoices:
        task_count = len(c.get("tasks", []))
        print(f"  {c['project_name']}: ${c['total_amount']:,.2f} ({task_count} tasks) — from {c['source']}")

    print(f"\nPhase 2 — From proposal PDFs: {len(contracts_from_proposals)}")
    for c in contracts_from_proposals:
        print(f"  {c['project_name']}: ${c['total_amount']:,.2f} — from {c['source']}")

    print(f"\nPhase 3 — T&M / needs manual: {len(needs_manual)}")
    for m in needs_manual:
        print(f"  {m['project_name']}: total invoiced ${m['total_invoiced']:,.2f}")

    if already_has_contract:
        print(f"\nAlready has contract: {len(already_has_contract)}")
        for name in already_has_contract:
            print(f"  {name}")

    # Phase 3 → create contracts from T&M invoiced totals
    contracts_from_tm = []
    for m in needs_manual:
        contracts_from_tm.append({
            "project_id": m["project_id"],
            "project_name": m["project_name"],
            "total_amount": m["total_invoiced"],
            "tasks": [],
            "source": "T&M (total from invoices)",
        })

    print(f"\nPhase 3 — T&M contracts (from invoice totals): {len(contracts_from_tm)}")
    for c in contracts_from_tm:
        print(f"  {c['project_name']}: ${c['total_amount']:,.2f}")

    all_contracts = contracts_from_invoices + contracts_from_proposals + contracts_from_tm
    total_pipeline = sum(c["total_amount"] for c in all_contracts)
    print(f"\nProjected pipeline value: ${total_pipeline:,.2f}")

    if not dry_run:
        print(f"\n{'='*60}")
        print(f"IMPORTING CONTRACTS")
        print(f"{'='*60}\n")

        for c in all_contracts:
            result = create_contract(c["project_id"], c, dry_run=False)
            if result:
                print(f"  + {c['project_name']}: ${c['total_amount']:,.2f} -> {result.get('id', '?')}")
    else:
        print(f"\nRun with --import to create these contracts.")


if __name__ == "__main__":
    main()
