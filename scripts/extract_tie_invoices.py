#!/usr/bin/env python3
"""Extract invoice data from TIE project PDF files.

Scans each imported project's data_path for invoice PDFs, extracts
text via pdfplumber, parses both invoice formats (simple + professional
services), and outputs a JSON report with confidence levels.

Run with --import flag to actually push to the API after review.
Run with --import-high to only import 90%+ confidence invoices.
"""

import json
import os
import re
import sys
import pdfplumber
import requests

API_BASE = "http://localhost:3000/api"
TIE_BASE = "/mnt/d/Dropbox/TIE"


def find_invoice_pdfs(data_path: str) -> list[str]:
    """Find all invoice PDF files under a project's data_path."""
    pdfs = []
    for root, dirs, files in os.walk(data_path):
        for f in files:
            if f.lower().endswith(".pdf") and "invoice" in f.lower():
                full = os.path.join(root, f)
                pdfs.append(full)
    return sorted(pdfs)


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages)
    except Exception as e:
        return f"ERROR: {e}"


def parse_money(s: str) -> float | None:
    """Parse a money string like '$1,500.00' or '$ 1 ,500.00' to float.

    pdfplumber often inserts spaces in dollar amounts from these PDFs,
    e.g. '$ 1 ,353.50' or '$ 6 00.00'. We strip ALL spaces first.
    """
    if not s:
        return None
    # Remove $, ALL spaces, commas
    cleaned = re.sub(r'[$\s,]', '', s.strip())
    # Handle the '-' case (zero amount)
    if cleaned == '-' or cleaned == '':
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_dollar_amount(text: str, pattern: str) -> float | None:
    """Extract a dollar amount following a pattern, handling spaced amounts.

    The key insight: pdfplumber renders amounts like '$ 1 ,353.50'
    so after the pattern match, we grab everything up to the newline
    and parse it as money.
    """
    m = re.search(pattern + r'\s*\$?\s*([\d\s,]+\.?\d*)', text)
    if m:
        return parse_money(m.group(1))
    return None


def parse_professional_format(text: str) -> dict | None:
    """Parse the professional services invoice format."""
    result = {
        "format": "professional",
        "confidence": 0.9,
        "tasks": [],
    }

    inv_num = re.search(r'Invoice Number:\s*(\S+)', text)
    inv_date = re.search(r'Invoice Date:\s*(\S+)', text)
    project_id = re.search(r'Project ID:\s*(\S+)', text)
    client_project = re.search(r'Client Project #:\s*(\S+)', text)
    pm = re.search(r'Project Manager:\s*(.+?)(?:\n|$)', text)
    bill_to = re.search(r'Bill To:\s*(.+?)(?:\n|$)', text)

    if inv_num:
        result["invoice_number"] = inv_num.group(1)
    if inv_date:
        result["date"] = inv_date.group(1)
    if project_id:
        result["project_ref"] = project_id.group(1)
    if client_project:
        result["client_project_number"] = str(client_project.group(1))
    if pm:
        result["pm"] = pm.group(1).strip()
    if bill_to:
        result["bill_to"] = bill_to.group(1).strip()

    # Extract task lines
    # Pattern: TaskName $Fee Percent $PrevBilling $CurrentBilling
    task_pattern = re.compile(
        r'^(.+?)\s+\$?([\d,]+\.?\d*)\s+([\d.]+)%?\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)\s*$',
        re.MULTILINE
    )

    for m in task_pattern.finditer(text):
        name = m.group(1).strip()
        if name.lower() in ('task', 'total', 'previous fee', 'current fee'):
            continue
        task = {
            "name": name,
            "fee": parse_money(m.group(2)),
            "percent_complete": float(m.group(3)),
            "previous_billing": parse_money(m.group(4)),
            "current_billing": parse_money(m.group(5)),
        }
        result["tasks"].append(task)

    # Invoice total
    total_match = re.search(r'Invoice Total\s+\$?([\d,]+\.?\d*)', text)
    if total_match:
        result["total_due"] = parse_money(total_match.group(1))

    # Contract total
    contract_total = re.search(r'^Total\s+\$?([\d,]+\.?\d*)', text, re.MULTILINE)
    if contract_total:
        result["contract_total"] = parse_money(contract_total.group(1))

    if not result.get("invoice_number"):
        result["confidence"] -= 0.2
    if not result.get("total_due"):
        result["confidence"] -= 0.3
    if not result["tasks"]:
        result["confidence"] -= 0.2

    return result


def parse_simple_format(text: str) -> dict | None:
    """Parse the simple invoice format.

    Key challenge: pdfplumber inserts spaces in dollar amounts,
    e.g. '$ 1 ,353.50' or '$ 6 00.00'.
    """
    result = {
        "format": "simple",
        "confidence": 0.85,
        "tasks": [],
    }

    # Header fields
    inv_num = re.search(r'INVOICE\s*#\s*(\S+)', text)
    date_match = re.search(r'DATE:\s*(.+?)(?:\n|$)', text)
    bill_to_match = re.search(r'Bill To:\s*\n?(.+?)(?:\n|$)', text)
    for_match = re.search(r'FOR:\s*(.+?)(?:\n|$)', text)

    if inv_num:
        result["invoice_number"] = inv_num.group(1)
    if date_match:
        result["date"] = date_match.group(1).strip()
    if bill_to_match:
        result["bill_to"] = bill_to_match.group(1).strip()
    if for_match:
        result["description"] = for_match.group(1).strip()

    # Extract TOTAL DUE - the amount has spaces in it from pdfplumber
    # Pattern: "TOTAL DUE $ 1 ,353.50" or "TOTAL DUE $ 6 25.00"
    total_match = re.search(r'TOTAL\s+DUE\s+(\$[\s\d,]+\.?\d*)', text)
    if total_match:
        result["total_due"] = parse_money(total_match.group(1))

    # Extract PROJECT TOTAL
    project_total = re.search(r'PROJECT\s+TOTAL(?:\s+TO\s+DATE)?:?\s+(\$[\s\d,]+\.?\d*)', text)
    if project_total:
        result["contract_total"] = parse_money(project_total.group(1))

    # Extract line items from simple format
    # Lines look like: "PE Hour 5.00 $125.00 $ 6 25.00"
    # or: "Design Tech Hour 5.00 $120.00 $ 6 00.00"
    # The amounts have spaces, so we match the last two dollar patterns on a line
    line_pattern = re.compile(
        r'^(.+?)\s+([\d.]+)\s+(\$[\s\d,]+\.?\d*)\s+(\$[\s\d,]+\.?\d*)\s*$',
        re.MULTILINE
    )

    for m in line_pattern.finditer(text):
        name = m.group(1).strip()
        if name.lower() in ('description', 'previous invoices'):
            continue
        if 'quantity' in name.lower() or 'rate' in name.lower():
            continue
        qty = float(m.group(2))
        rate = parse_money(m.group(3))
        amount = parse_money(m.group(4))
        if amount is not None and amount > 0:
            task = {
                "name": name,
                "quantity": qty,
                "rate": rate,
                "amount": amount,
            }
            result["tasks"].append(task)

    # Also try to catch the task header line (e.g., "Task 1: Design Development...")
    # which appears before the line items
    task_header = re.search(r'(Task\s*\d*:?\s*.+?)(?:\n|$)', text)
    if task_header and result["tasks"]:
        header = task_header.group(1).strip()
        # Attach as the group name for the line items
        result["task_group"] = header

    if not result.get("invoice_number"):
        result["confidence"] -= 0.2
    if not result.get("total_due"):
        result["confidence"] -= 0.3

    return result


def parse_invoice(text: str, pdf_path: str) -> dict:
    """Detect format and parse an invoice from extracted text."""
    if "ERROR:" in text:
        return {
            "pdf_path": pdf_path,
            "format": "error",
            "confidence": 0.0,
            "error": text,
        }

    is_professional = (
        "% Complete" in text or
        "Previous Fee" in text or
        "Current Fee" in text or
        "Professional Services" in text
    )

    if is_professional:
        result = parse_professional_format(text)
    else:
        result = parse_simple_format(text)

    if result is None:
        result = {"format": "unknown", "confidence": 0.0}

    result["pdf_path"] = pdf_path
    result["filename"] = os.path.basename(pdf_path)
    result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.0)))

    return result


def get_imported_projects() -> list[dict]:
    """Get all projects from the API with full details."""
    resp = requests.get(f"{API_BASE}/projects")
    resp.raise_for_status()
    projects = resp.json()
    # Get full details for each (includes data_path)
    detailed = []
    for p in projects:
        detail = requests.get(f"{API_BASE}/projects/{p['id']}").json()
        detailed.append(detail)
    return detailed


def import_invoice(inv: dict) -> dict | None:
    """Import a single invoice via the API."""
    project_id = inv["project_id"]
    total_due = inv.get("total_due", 0) or 0
    inv_number = inv.get("invoice_number", "")
    description = inv.get("description", "") or f"Imported from {inv['filename']}"

    # Use the project invoices endpoint (query params)
    params = {
        "invoice_number": inv_number,
        "invoice_type": "task" if inv.get("tasks") else "list",
        "description": description,
        "total_due": total_due,
    }

    resp = requests.post(f"{API_BASE}/projects/{project_id}/invoices", params=params)
    if resp.status_code in (200, 201):
        result = resp.json()
        inv_id = result.get("id", "?")

        # Update with pdf_path and sent_status
        update_payload = {
            "pdf_path": inv["pdf_path"],
            "sent_status": "sent",
        }
        requests.patch(f"{API_BASE}/invoices/{inv_id}", json=update_payload)

        return result
    else:
        print(f"  ! {inv_number} failed: {resp.status_code} {resp.text[:200]}")
        return None


def main():
    do_import_all = "--import" in sys.argv
    do_import_high = "--import-high" in sys.argv

    projects = get_imported_projects()
    print(f"Found {len(projects)} projects in database\n")

    all_invoices = []

    for proj in projects:
        data_path = proj.get("data_path")
        if not data_path or not os.path.isdir(data_path):
            continue

        pdfs = find_invoice_pdfs(data_path)
        if not pdfs:
            continue

        project_name = proj.get("project_name") or proj.get("name", "?")
        print(f"\n{'─'*60}")
        print(f"📁 {project_name} ({proj['id']})")
        print(f"   Found {len(pdfs)} invoice PDF(s)")

        for pdf_path in pdfs:
            text = extract_text(pdf_path)
            parsed = parse_invoice(text, pdf_path)
            parsed["project_id"] = proj["id"]
            parsed["project_name"] = project_name
            parsed["client_name"] = proj.get("client_name", "")

            conf = parsed['confidence']
            total = parsed.get('total_due')
            inv_num = parsed.get('invoice_number', '?')
            task_count = len(parsed.get('tasks', []))
            total_str = f"${total:,.2f}" if total else "?"

            print(f"   📄 {parsed['filename']}")
            print(f"      #{inv_num} | {total_str} | {task_count} tasks | {conf*100:.0f}%")
            if parsed.get("tasks"):
                for t in parsed["tasks"]:
                    if "current_billing" in t:
                        print(f"        - {t['name']}: fee=${t.get('fee','?')}, {t.get('percent_complete','?')}%, current=${t.get('current_billing','?')}")
                    else:
                        print(f"        - {t['name']}: {t.get('quantity','?')} x ${t.get('rate','?')} = ${t.get('amount','?')}")

            all_invoices.append(parsed)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")

    total_invoices = len(all_invoices)
    high_conf = [i for i in all_invoices if i["confidence"] >= 0.85]
    med_conf = [i for i in all_invoices if 0.5 <= i["confidence"] < 0.85]
    low_conf = [i for i in all_invoices if i["confidence"] < 0.5]
    total_amount = sum(i.get("total_due", 0) or 0 for i in all_invoices)

    print(f"Total invoice PDFs: {total_invoices}")
    print(f"  High confidence (>=85%): {len(high_conf)}")
    print(f"  Medium confidence (50-84%): {len(med_conf)}")
    print(f"  Low confidence (<50%): {len(low_conf)}")
    print(f"Total amount: ${total_amount:,.2f}")

    # Show what needs manual attention
    if med_conf or low_conf:
        print(f"\n{'─'*60}")
        print("⚠️  NEEDS MANUAL REVIEW:")
        print(f"{'─'*60}")
        for inv in med_conf + low_conf:
            total = inv.get('total_due')
            total_str = f"${total:,.2f}" if total else "NO TOTAL"
            print(f"  {inv['project_name']}: {inv['filename']} ({inv['confidence']*100:.0f}%) — {total_str}")

    # Write report
    report_path = "/mnt/d/repos/podium/scripts/invoice_extraction_report.json"
    with open(report_path, "w") as f:
        json.dump(all_invoices, f, indent=2, default=str)
    print(f"\nReport: {report_path}")

    # Import
    if do_import_all or do_import_high:
        min_conf = 0.85 if do_import_high else 0.3
        to_import = [i for i in all_invoices if i["confidence"] >= min_conf and (i.get("total_due") or 0) > 0]
        print(f"\n{'='*60}")
        print(f"IMPORTING {len(to_import)} invoices (min confidence {min_conf*100:.0f}%)")
        print(f"{'='*60}")

        imported = 0
        for inv in to_import:
            result = import_invoice(inv)
            if result:
                total_str = f"${inv.get('total_due', 0):,.2f}"
                print(f"  + {inv.get('invoice_number','?')}: {total_str} -> {result.get('id','?')} ({inv['project_name']})")
                imported += 1

        print(f"\nImported: {imported}")
    else:
        print(f"\nRun with --import-high to import {len(high_conf)} high-confidence invoices.")
        print(f"Run with --import to import all with total > $0.")


if __name__ == "__main__":
    main()
