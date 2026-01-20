#!/usr/bin/env python3
"""
Initialize the Podium database with schema and optional seed data.

Usage:
    python init_db.py              # Create fresh DB with seed data
    python init_db.py --no-seed    # Create fresh DB without seed data
    python init_db.py --seed-only  # Add seed data to existing DB
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), 'podium.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def generate_id(prefix=''):
    """Generate a short unique ID"""
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}{short_id}" if prefix else short_id

def init_schema(conn):
    """Initialize database with schema"""
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    conn.executescript(schema)
    print("Schema initialized")

def seed_data(conn):
    """Add sample data for development/testing"""
    cur = conn.cursor()
    now = datetime.now().isoformat()

    # --- Clients ---
    clients = [
        ('c-birdsall', 'Jim Birdsall', 'jim@birdsallhomes.com', 'Birdsall Homes', '555-100-1000', '100 Builder Way', None, now, now, None),
        ('c-tbg', 'Tom Garcia', 'tom@tbgpartners.com', 'TBG Partners', '555-200-2000', '200 Landscape Blvd', None, now, now, None),
        ('c-heron', 'Sarah Chen', 'sarah@heronlakes.com', 'Heron Lakes HOA', '555-300-3000', '300 Lakeside Dr', None, now, now, None),
    ]
    cur.executemany('''
        INSERT INTO clients (id, name, email, company, phone, address, notes, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', clients)
    print(f"Added {len(clients)} clients")

    # --- Contacts ---
    contacts = [
        ('ct-jbirdsall', 'Jim Birdsall', 'jim@birdsallhomes.com', '555-100-1001', 'Owner', 'c-birdsall', now, now, None),
        ('ct-mbirdsall', 'Mary Birdsall', 'mary@birdsallhomes.com', '555-100-1002', 'Project Manager', 'c-birdsall', now, now, None),
        ('ct-tgarcia', 'Tom Garcia', 'tom@tbgpartners.com', '555-200-2001', 'Principal', 'c-tbg', now, now, None),
        ('ct-schen', 'Sarah Chen', 'sarah@heronlakes.com', '555-300-3001', 'HOA Manager', 'c-heron', now, now, None),
    ]
    cur.executemany('''
        INSERT INTO contacts (id, name, email, phone, role, client_id, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', contacts)
    print(f"Added {len(contacts)} contacts")

    # --- Projects ---
    projects = [
        ('JBHL21', 'Heron Lakes Phase 2', 'c-heron', 'ct-schen', 'contract', 'TBG/HeronLakes', '## Project Notes\n\nPhase 2 irrigation for lots 50-100.', now, now, None),
        ('JBTH22', 'Birdsall Thompson House', 'c-birdsall', 'ct-mbirdsall', 'invoiced', 'Birdsall/Thompson', '## Notes\n\nResidential irrigation design.', now, now, None),
        ('JBTBG23', 'TBG Office Campus', 'c-tbg', 'ct-tgarcia', 'proposal', 'TBG/OfficeCampus', '## Notes\n\nCommercial landscape irrigation.', now, now, None),
    ]
    cur.executemany('''
        INSERT INTO projects (id, name, client_id, client_pm_id, status, data_path, notes, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', projects)
    print(f"Added {len(projects)} projects")

    # --- Contracts ---
    contracts = [
        ('con-001', 'JBHL21', '/dropbox/TBG/HeronLakes/contract-signed.pdf', 45000.00, '2024-03-15', None, now, now, None),
        ('con-002', 'JBTH22', '/dropbox/Birdsall/Thompson/contract-signed.pdf', 8500.00, '2024-06-01', None, now, now, None),
    ]
    cur.executemany('''
        INSERT INTO contracts (id, project_id, file_path, total_amount, signed_at, notes, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', contracts)
    print(f"Added {len(contracts)} contracts")

    # --- Proposals ---
    proposals = [
        ('prop-001', 'JBTBG23', '/dropbox/TBG/OfficeCampus/proposal.docx', '/dropbox/TBG/OfficeCampus/proposal.pdf', 'TBG Partners', 'tom@tbgpartners.com', 125000.00, now, 'sent', now, now, None),
    ]
    cur.executemany('''
        INSERT INTO proposals (id, project_id, data_path, pdf_path, client_company, client_contact_email, total_fee, sent_at, status, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', proposals)
    print(f"Added {len(proposals)} proposals")

    # --- Proposal Tasks ---
    proposal_tasks = [
        ('pt-001', 'prop-001', 1, 'Irrigation Design', 'Complete irrigation design for campus', 75000.00, now),
        ('pt-002', 'prop-001', 2, 'Construction Documents', 'CD set for bidding', 35000.00, now),
        ('pt-003', 'prop-001', 3, 'Construction Admin', 'CA services during installation', 15000.00, now),
    ]
    cur.executemany('''
        INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', proposal_tasks)
    print(f"Added {len(proposal_tasks)} proposal tasks")

    # --- Invoices ---
    invoices = [
        ('inv-001', 'JBHL21-1', 'JBHL21', 'con-001', 'task', None, '/sheets/JBHL21-1', '/dropbox/TBG/HeronLakes/invoices/JBHL21-1.pdf', 'sent', 'paid', 22500.00, '2024-04-01', '2024-04-15', now, now, None),
        ('inv-002', 'JBHL21-2', 'JBHL21', 'con-001', 'task', None, '/sheets/JBHL21-2', '/dropbox/TBG/HeronLakes/invoices/JBHL21-2.pdf', 'sent', 'unpaid', 22500.00, '2024-07-01', None, now, now, None),
        ('inv-003', 'JBTH22-1', 'JBTH22', 'con-002', 'task', None, '/sheets/JBTH22-1', '/dropbox/Birdsall/Thompson/invoices/JBTH22-1.pdf', 'sent', 'unpaid', 4250.00, '2024-08-01', None, now, now, None),
        ('inv-004', 'JBTH22-R1', 'JBTH22', None, 'list', 'Additional site visits - hourly', '/sheets/JBTH22-R1', None, 'unsent', 'unpaid', 1200.00, None, None, now, now, None),
    ]
    cur.executemany('''
        INSERT INTO invoices (id, invoice_number, project_id, contract_id, type, description, data_path, pdf_path, sent_status, paid_status, total_due, sent_at, paid_at, created_at, updated_at, deleted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', invoices)
    print(f"Added {len(invoices)} invoices")

    # --- Invoice Line Items ---
    line_items = [
        ('li-001', 'inv-001', 1, 'Design - 50%', 'Irrigation design phase 1', 1, 22500.00, 22500.00, now),
        ('li-002', 'inv-002', 1, 'Design - 50%', 'Irrigation design phase 2', 1, 22500.00, 22500.00, now),
        ('li-003', 'inv-003', 1, 'Design - 50%', 'Residential irrigation design', 1, 4250.00, 4250.00, now),
        ('li-004', 'inv-004', 1, 'Site Visit', 'Additional site visit 7/15', 4, 150.00, 600.00, now),
        ('li-005', 'inv-004', 2, 'Site Visit', 'Additional site visit 7/22', 4, 150.00, 600.00, now),
    ]
    cur.executemany('''
        INSERT INTO invoice_line_items (id, invoice_id, sort_order, name, description, quantity, unit_price, amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', line_items)
    print(f"Added {len(line_items)} invoice line items")

    conn.commit()
    print("\nSeed data committed")

def verify_data(conn):
    """Verify the data was inserted correctly"""
    cur = conn.cursor()

    print("\n--- Verification ---")

    # Count records
    tables = ['clients', 'contacts', 'projects', 'contracts', 'proposals', 'invoices']
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count} records")

    # Test the project summary view
    print("\n--- Project Summary View ---")
    cur.execute("SELECT id, name, status, total_invoiced, total_paid, total_outstanding FROM v_project_summary")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} ({row[2]}) - Invoiced: ${row[3]:,.2f}, Paid: ${row[4]:,.2f}, Outstanding: ${row[5]:,.2f}")

def main():
    args = sys.argv[1:]
    seed_only = '--seed-only' in args
    no_seed = '--no-seed' in args

    if os.path.exists(DB_PATH) and not seed_only:
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        if not seed_only:
            init_schema(conn)

        if not no_seed:
            seed_data(conn)

        verify_data(conn)

        print(f"\nDatabase ready: {DB_PATH}")
        print(f"Size: {os.path.getsize(DB_PATH):,} bytes")

    finally:
        conn.close()

if __name__ == '__main__':
    main()
