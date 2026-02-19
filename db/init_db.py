#!/usr/bin/env python3
"""
Initialize the Conductor database with schema and optional seed data.

Usage:
    python init_db.py              # Create fresh DB with seed data
    python init_db.py --no-seed    # Create fresh DB, schema only
    python init_db.py --seed-only  # Add seed data to existing DB
"""

import os
import sys
from datetime import datetime
import uuid

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    'CONDUCTOR_DATABASE_URL',
    'postgresql://conductor:conductor@localhost:5432/conductor',
)
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def generate_id(prefix=''):
    """Generate a short unique ID"""
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}{short_id}" if prefix else short_id

def init_schema(conn):
    """Initialize database with schema"""
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    cur = conn.cursor()
    cur.execute(schema)
    conn.commit()
    print("Schema initialized")

def drop_all(conn):
    """Drop all tables and views for a fresh start"""
    cur = conn.cursor()
    cur.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
            FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    conn.commit()
    print("Dropped all existing tables and views")

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
    for c in clients:
        cur.execute('''
            INSERT INTO clients (id, name, email, company, phone, address, notes, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', c)
    print(f"Added {len(clients)} clients")

    # --- Contacts ---
    contacts = [
        ('ct-jbirdsall', 'Jim Birdsall', 'jim@birdsallhomes.com', '555-100-1001', 'Owner', 'c-birdsall', now, now, None),
        ('ct-mbirdsall', 'Mary Birdsall', 'mary@birdsallhomes.com', '555-100-1002', 'Project Manager', 'c-birdsall', now, now, None),
        ('ct-tgarcia', 'Tom Garcia', 'tom@tbgpartners.com', '555-200-2001', 'Principal', 'c-tbg', now, now, None),
        ('ct-schen', 'Sarah Chen', 'sarah@heronlakes.com', '555-300-3001', 'HOA Manager', 'c-heron', now, now, None),
    ]
    for c in contacts:
        cur.execute('''
            INSERT INTO contacts (id, name, email, phone, role, client_id, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', c)
    print(f"Added {len(contacts)} contacts")

    # --- Projects ---
    projects = [
        ('JBHL21', 'Heron Lakes Phase 2', 'c-heron', 'ct-schen', 'contract', 'TBG/HeronLakes', '## Project Notes\n\nPhase 2 irrigation for lots 50-100.', now, now, None),
        ('JBTH22', 'Birdsall Thompson House', 'c-birdsall', 'ct-mbirdsall', 'invoiced', 'Birdsall/Thompson', '## Notes\n\nResidential irrigation design.', now, now, None),
        ('JBTBG23', 'TBG Office Campus', 'c-tbg', 'ct-tgarcia', 'proposal', 'TBG/OfficeCampus', '## Notes\n\nCommercial landscape irrigation.', now, now, None),
    ]
    for p in projects:
        cur.execute('''
            INSERT INTO projects (id, name, client_id, client_pm_id, status, data_path, notes, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', p)
    print(f"Added {len(projects)} projects")

    # --- Contracts ---
    contracts = [
        ('con-001', 'JBHL21', '/dropbox/TBG/HeronLakes/contract-signed.pdf', 45000.00, '2024-03-15', None, now, now, None),
        ('con-002', 'JBTH22', '/dropbox/Birdsall/Thompson/contract-signed.pdf', 8500.00, '2024-06-01', None, now, now, None),
    ]
    for c in contracts:
        cur.execute('''
            INSERT INTO contracts (id, project_id, file_path, total_amount, signed_at, notes, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', c)
    print(f"Added {len(contracts)} contracts")

    # --- Contract Tasks ---
    contract_tasks = [
        ('ctask-001', 'con-001', 1, 'Preliminary Design', 'Schematic irrigation design and layout', 15000.00, 15000.00, 100.0, now, now),
        ('ctask-002', 'con-001', 2, 'Construction Documents', 'Full CD set for bidding', 20000.00, 7500.00, 37.5, now, now),
        ('ctask-003', 'con-001', 3, 'Construction Administration', 'CA services during installation', 10000.00, 0.00, 0.0, now, now),
        ('ctask-004', 'con-002', 1, 'Irrigation Design', 'Residential irrigation design', 6000.00, 4250.00, 70.8, now, now),
        ('ctask-005', 'con-002', 2, 'As-Built Documentation', 'Final as-built drawings', 2500.00, 0.00, 0.0, now, now),
    ]
    for ct in contract_tasks:
        cur.execute('''
            INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, billed_amount, billed_percent, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', ct)
    print(f"Added {len(contract_tasks)} contract tasks")

    # --- Proposals ---
    proposals = [
        ('prop-001', 'JBTBG23', '/dropbox/TBG/OfficeCampus/proposal.docx', '/dropbox/TBG/OfficeCampus/proposal.pdf',
         'TBG Partners', 'tom@tbgpartners.com', 125000.00,
         'tim', 'Tim Grote', 'P.E., Owner', 'site meeting', '2024-01-15',
         now, 'sent', now, now, None),
    ]
    for p in proposals:
        cur.execute('''
            INSERT INTO proposals (id, project_id, data_path, pdf_path, client_company, client_contact_email, total_fee,
             engineer_key, engineer_name, engineer_title, contact_method, proposal_date,
             sent_at, status, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', p)
    print(f"Added {len(proposals)} proposals")

    # --- Proposal Tasks ---
    proposal_tasks = [
        ('pt-001', 'prop-001', 1, 'Irrigation Design', 'Complete irrigation design for campus', 75000.00, now),
        ('pt-002', 'prop-001', 2, 'Construction Documents', 'CD set for bidding', 35000.00, now),
        ('pt-003', 'prop-001', 3, 'Construction Admin', 'CA services during installation', 15000.00, now),
    ]
    for pt in proposal_tasks:
        cur.execute('''
            INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', pt)
    print(f"Added {len(proposal_tasks)} proposal tasks")

    # --- Invoices ---
    invoices = [
        ('inv-001', 'JBHL21-1', 'JBHL21', 'con-001', None, 'task', None, '/sheets/JBHL21-1', '/dropbox/TBG/HeronLakes/invoices/JBHL21-1.pdf', 'sent', 'paid', 22500.00, '2024-04-01', '2024-04-15', now, now, None),
        ('inv-002', 'JBHL21-2', 'JBHL21', 'con-001', None, 'task', None, '/sheets/JBHL21-2', '/dropbox/TBG/HeronLakes/invoices/JBHL21-2.pdf', 'sent', 'unpaid', 22500.00, '2024-07-01', None, now, now, None),
        ('inv-003', 'JBTH22-1', 'JBTH22', 'con-002', None, 'task', None, '/sheets/JBTH22-1', '/dropbox/Birdsall/Thompson/invoices/JBTH22-1.pdf', 'sent', 'unpaid', 4250.00, '2024-08-01', None, now, now, None),
        ('inv-004', 'JBTH22-R1', 'JBTH22', None, None, 'list', 'Additional site visits - hourly', '/sheets/JBTH22-R1', None, 'unsent', 'unpaid', 1200.00, None, None, now, now, None),
    ]
    for inv in invoices:
        cur.execute('''
            INSERT INTO invoices (id, invoice_number, project_id, contract_id, previous_invoice_id, type, description, data_path, pdf_path, sent_status, paid_status, total_due, sent_at, paid_at, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', inv)
    print(f"Added {len(invoices)} invoices")

    # --- Invoice Line Items ---
    line_items = [
        ('li-001', 'inv-001', 1, 'Design - 50%', 'Irrigation design phase 1', 1, 22500.00, 22500.00, 0, now),
        ('li-002', 'inv-002', 1, 'Design - 50%', 'Irrigation design phase 2', 1, 22500.00, 22500.00, 0, now),
        ('li-003', 'inv-003', 1, 'Design - 50%', 'Residential irrigation design', 1, 4250.00, 4250.00, 0, now),
        ('li-004', 'inv-004', 1, 'Site Visit', 'Additional site visit 7/15', 4, 150.00, 600.00, 0, now),
        ('li-005', 'inv-004', 2, 'Site Visit', 'Additional site visit 7/22', 4, 150.00, 600.00, 0, now),
    ]
    for li in line_items:
        cur.execute('''
            INSERT INTO invoice_line_items (id, invoice_id, sort_order, name, description, quantity, unit_price, amount, previous_billing, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', li)
    print(f"Added {len(line_items)} invoice line items")

    # --- Employees ---
    employees = [
        ('emp-tim', 'Tim', 'Grote', 'tim@irrigationengineers.com', None, True, now, now, None),
        ('emp-ally', 'Ally', 'Liebow', 'ally@irrigationengineers.com', None, True, now, now, None),
        ('emp-matara', 'Matara', 'Liebow', 'matara@irrigationengineers.com', None, True, now, now, None),
    ]
    for e in employees:
        cur.execute('''
            INSERT INTO employees (id, first_name, last_name, email, bot_id, is_active, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', e)
    print(f"Added {len(employees)} employees")

    # --- Project Tasks ---
    today = now[:10]
    project_tasks = [
        ('task-001', 'JBHL21', None, 'Review irrigation layout for lots 50-75', 'Check spacing and head coverage for the first half of phase 2', 'in_progress', None, '2024-08-01', '2024-09-15', None, 1, 'emp-tim', None, now, now, None),
        ('task-002', 'JBHL21', None, 'Submit CD set to county for review', None, 'todo', None, today, '2024-10-01', None, 2, None, None, now, now, None),
        ('task-003', 'JBHL21', 'task-001', 'Update head schedule for lots 60-65', None, 'todo', None, today, None, None, 1, None, None, now, now, None),
        ('task-004', 'JBTH22', None, 'Finalize as-built documentation', 'Measure installed heads and update drawings', 'todo', None, '2024-08-15', '2024-08-30', None, 1, 'emp-ally', None, now, now, None),
    ]
    for t in project_tasks:
        cur.execute('''
            INSERT INTO project_tasks (id, project_id, parent_id, title, description, status, priority, start_date, due_date, reminder_at, sort_order, created_by, completed_at, created_at, updated_at, deleted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', t)
    print(f"Added {len(project_tasks)} project tasks")

    # --- Task Assignees ---
    task_assignees = [
        ('task-001', 'emp-tim'),
        ('task-001', 'emp-ally'),
        ('task-002', 'emp-tim'),
        ('task-004', 'emp-ally'),
    ]
    for ta in task_assignees:
        cur.execute('''
            INSERT INTO project_task_assignees (task_id, employee_id) VALUES (%s, %s)
        ''', ta)
    print(f"Added {len(task_assignees)} task assignees")

    # --- Task Notes ---
    task_notes = [
        ('note-001', 'task-001', 'emp-tim', 'Started review - lots 50-55 look good, need to check 56-60 for pressure issues', now),
        ('note-002', 'task-001', 'emp-ally', 'Confirmed pressure calcs for 56-60 are within spec', now),
    ]
    for tn in task_notes:
        cur.execute('''
            INSERT INTO project_task_notes (id, task_id, author_id, content, created_at) VALUES (%s, %s, %s, %s, %s)
        ''', tn)
    print(f"Added {len(task_notes)} task notes")

    # --- Company Settings ---
    company_settings = [
        ('company_name', 'Irrigation Engineers, Inc.'),
        ('company_email', 'info@irrigationengineers.com'),
        ('company_phone', '(555) 987-6543'),
        ('company_address', '456 Design Blvd\nAustin, TX 78701'),
        ('tagline', 'Professional Irrigation Design'),
        ('primary_color', '#6c63ff'),
    ]
    for key, value in company_settings:
        cur.execute(
            "INSERT INTO company_settings (key, value) VALUES (%s, %s)",
            (key, value)
        )
    print(f"Added {len(company_settings)} company settings")

    conn.commit()
    print("\nSeed data committed")

def verify_data(conn):
    """Verify the data was inserted correctly"""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("\n--- Verification ---")

    # Count records
    tables = ['clients', 'contacts', 'projects', 'contracts', 'contract_tasks', 'proposals', 'invoices', 'employees', 'project_tasks', 'project_task_assignees', 'project_task_notes', 'project_notes']
    for table in tables:
        cur.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cur.fetchone()['count']
        print(f"{table}: {count} records")

    # Test the project summary view
    print("\n--- Project Summary View ---")
    cur.execute("SELECT id, name, status, total_invoiced, total_paid, total_outstanding FROM v_project_summary")
    for row in cur.fetchall():
        print(f"  {row['id']}: {row['name']} ({row['status']}) - Invoiced: ${float(row['total_invoiced']):,.2f}, Paid: ${float(row['total_paid']):,.2f}, Outstanding: ${float(row['total_outstanding']):,.2f}")

def main():
    args = sys.argv[1:]
    seed_only = '--seed-only' in args
    no_seed = '--no-seed' in args

    print(f"Connecting to: {DATABASE_URL}")
    conn = psycopg2.connect(DATABASE_URL)

    try:
        if not seed_only:
            drop_all(conn)
            init_schema(conn)

        if not no_seed:
            seed_data(conn)

        verify_data(conn)

        print(f"\nDatabase ready: {DATABASE_URL}")

    finally:
        conn.close()

if __name__ == '__main__':
    main()
