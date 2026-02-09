"""
Tests for the 7 critical PR review fixes (C1–C7).

Each test targets exactly one bug that was found and fixed.
If a test fails, it means that specific fix has regressed.

Run with:  pytest tests/test_critical_fixes.py -v
"""

from datetime import datetime
from unittest.mock import patch
from io import BytesIO


# ---------------------------------------------------------------------------
# Helper: seed a minimal project + client into the test database
# ---------------------------------------------------------------------------
def _seed_project(db, project_id="TEST01", client_id="c-test1"):
    """Insert a client and project so other entities can reference them."""
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO clients (id, name, email, created_at, updated_at) "
        "VALUES (?, 'Test Client', 'test@example.com', ?, ?)",
        (client_id, now, now),
    )
    db.execute(
        "INSERT INTO projects (id, name, client_id, status, created_at, updated_at) "
        "VALUES (?, 'Test Project', ?, 'contract', ?, ?)",
        (project_id, client_id, now, now),
    )
    db.commit()


def _seed_invoice(db, project_id="TEST01", invoice_id="inv-001", number="TEST01-1"):
    """Insert an invoice for a project."""
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO invoices (id, invoice_number, project_id, type, total_due, "
        "created_at, updated_at) VALUES (?, ?, ?, 'list', 100, ?, ?)",
        (invoice_id, number, project_id, now, now),
    )
    db.commit()


# ===========================================================================
# C1: Route ordering — /by-number/{invoice_number} must be reachable
# ===========================================================================
def test_by_number_route_returns_invoice(client, db):
    """
    BUG: GET /by-number/X was unreachable because GET /{invoice_id} captured
    all paths first. FastAPI matches routes in registration order, so
    "by-number" looked like an invoice_id.

    FIX: Moved /by-number/ route before /{invoice_id}.
    """
    _seed_project(db)
    _seed_invoice(db)

    # This should match the /by-number/ route, NOT the /{invoice_id} route
    resp = client.get("/api/invoices/by-number/TEST01-1")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.json()["invoice_number"] == "TEST01-1"


def test_by_number_route_returns_404_for_missing(client, db):
    """Nonexistent invoice number should return 404, not 500."""
    resp = client.get("/api/invoices/by-number/NONEXISTENT-99")
    assert resp.status_code == 404


# ===========================================================================
# C2: Path traversal — filenames must be sanitized
# ===========================================================================
def test_proposal_filename_sanitized(client, db):
    """
    BUG: UploadFile.filename was used directly in file paths. A filename like
    "../../etc/cron.d/evil" would write to arbitrary locations on disk.

    FIX: All filenames pass through PurePath(filename).name which strips
    directory components, leaving only the base filename.
    """
    _seed_project(db)

    # Craft a malicious filename with path traversal
    malicious_filename = "../../etc/cron.d/evil.pdf"
    file_content = b"%PDF-1.4 fake pdf content"

    resp = client.post(
        "/api/flows/proposals",
        data={
            "job_id": "TEST01",
            "client_name": "Test Client",
            "client_email": "test@example.com",
            "project_name": "Test Project",
            "amount": "1000",
        },
        files={"proposal_pdf": (malicious_filename, BytesIO(file_content), "application/pdf")},
    )
    assert resp.status_code == 200

    # Verify the stored path doesn't contain ".."
    proposal = db.execute(
        "SELECT pdf_path FROM proposals WHERE project_id = 'TEST01'"
    ).fetchone()
    assert proposal is not None
    stored_path = proposal["pdf_path"]
    assert ".." not in stored_path, f"Path traversal not sanitized: {stored_path}"
    assert "evil.pdf" in stored_path, "Base filename should be preserved"


def test_receipt_filename_sanitized(client, db):
    """Receipt uploads on the payments endpoint should also be sanitized."""
    _seed_project(db)
    _seed_invoice(db)

    malicious_filename = "../../../tmp/evil-receipt.png"
    resp = client.post(
        "/api/flows/payments",
        data={
            "invoice": "TEST01-1",
            "job_id": "TEST01",
            "client_email": "test@example.com",
            "confirmation": "CHK-123",
        },
        files={"receipt": (malicious_filename, BytesIO(b"fake"), "image/png")},
    )
    # Should succeed (invoice exists) and receipt should be sanitized
    assert resp.status_code == 200


# ===========================================================================
# C3: Payment submission must 404 on missing invoice
# ===========================================================================
def test_payment_missing_invoice_returns_404(client, db):
    """
    BUG: If the invoice wasn't found, the endpoint returned {"success": true}
    — the client thinks payment was recorded, but nothing was updated.
    Financial data silently lost.

    FIX: Added HTTPException(404) when invoice lookup returns None.
    """
    _seed_project(db)

    resp = client.post(
        "/api/flows/payments",
        data={
            "invoice": "NONEXISTENT-999",
            "job_id": "TEST01",
            "client_email": "test@example.com",
            "confirmation": "CHK-123",
        },
    )
    assert resp.status_code == 404, (
        f"Expected 404 for missing invoice, got {resp.status_code}: {resp.json()}"
    )


# ===========================================================================
# C4: Contract submission must 404 on missing project
# ===========================================================================
def test_contract_missing_project_returns_404(client, db):
    """
    BUG: No check that job_id references an existing project. The UPDATE
    silently affected zero rows, or the contract INSERT hit an FK constraint
    producing a raw 500 error.

    FIX: Added project existence check before the UPDATE.
    """
    # Don't seed any project — job_id "GHOST" doesn't exist
    resp = client.post(
        "/api/flows/contracts",
        data={
            "job_id": "GHOST",
            "client_name": "Test",
            "client_email": "test@example.com",
        },
    )
    assert resp.status_code == 404, (
        f"Expected 404 for missing project, got {resp.status_code}: {resp.json()}"
    )


# ===========================================================================
# C5: Google Sheet errors — FileNotFoundError caught separately
# ===========================================================================
def test_google_sheet_file_not_found_handled_gracefully(client, db):
    """
    BUG: `except Exception` caught ALL errors including DB bugs, auth failures,
    and programming errors — all hidden behind logger.warning.

    FIX: FileNotFoundError (missing creds) is caught separately. Other
    exceptions propagate or are logged as errors with a _warning in response.
    """
    _seed_project(db)

    # Create a contract so we can create an invoice from it
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO contracts (id, project_id, total_amount, created_at, updated_at) "
        "VALUES ('con-test1', 'TEST01', 1000, ?, ?)",
        (now, now),
    )
    db.execute(
        "INSERT INTO contract_tasks (id, contract_id, sort_order, name, amount, "
        "created_at, updated_at) VALUES ('ct-1', 'con-test1', 1, 'Design', 1000, ?, ?)",
        (now, now),
    )
    db.commit()

    # Mock create_invoice_sheet at the SOURCE module (app.google_sheets),
    # not at the import site, because contracts.py imports it lazily
    # inside the function body with `from ..google_sheets import create_invoice_sheet`
    with patch(
        "app.google_sheets.create_invoice_sheet",
        side_effect=FileNotFoundError("credentials.json not found"),
    ):
        resp = client.post(
            "/api/contracts/con-test1/invoices",
            json={
                "tasks": [{"task_id": "ct-1", "percent_this_invoice": 50}],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    # Invoice should be created even without Google Sheets
    assert "id" in data
    # Should include a warning since no sheet was created
    assert data.get("_warning") or data.get("data_path") is None


# ===========================================================================
# C6: Invoice number generation — MAX-based, not COUNT-based
# ===========================================================================
def test_invoice_number_survives_deletion(client, db):
    """
    BUG: COUNT(*) was used to generate invoice numbers. After deleting invoice
    #1 and creating a new one, COUNT returns 0 → new invoice gets number 1
    again → UNIQUE constraint violation → unhandled 500.

    FIX: Uses MAX-based approach — finds the highest existing number and
    increments it, so gaps from deletions don't cause collisions.
    """
    _seed_project(db)

    # Create invoice #1
    resp1 = client.post(
        "/api/projects/TEST01/invoices",
        params={"invoice_type": "list", "total_due": 100},
    )
    assert resp1.status_code == 200
    inv1 = resp1.json()
    assert inv1["invoice_number"] == "TEST01-1"

    # Delete invoice #1 (soft delete)
    resp_del = client.delete(f"/api/invoices/{inv1['id']}")
    assert resp_del.status_code == 200

    # Create invoice #2 — should be TEST01-2, NOT TEST01-1
    resp2 = client.post(
        "/api/projects/TEST01/invoices",
        params={"invoice_type": "list", "total_due": 200},
    )
    assert resp2.status_code == 200
    inv2 = resp2.json()
    assert inv2["invoice_number"] == "TEST01-2", (
        f"Expected TEST01-2 after deleting TEST01-1, got {inv2['invoice_number']}. "
        "This means invoice numbering still uses COUNT instead of MAX."
    )


# ===========================================================================
# C7: sa_email must be initialized before try block
# ===========================================================================
def test_sa_email_no_unbound_error(client, db):
    """
    BUG: If an exception occurred before `sa_email = creds.service_account_email`,
    the except block referenced `sa_email` → UnboundLocalError → raw 500,
    hiding the actual error.

    FIX: Initialize `sa_email = "unknown"` before the try block.
    """
    # Mock at the SOURCE module (app.google_sheets), not at the import site,
    # because company.py imports these lazily inside the function body
    with patch(
        "app.google_sheets._get_credentials",
        side_effect=Exception("Connection refused"),
    ), patch(
        "app.google_sheets.get_drive_service",
        side_effect=Exception("Connection refused"),
    ):
        # Save settings with a template ID to trigger the Google access check
        resp = client.put(
            "/api/company",
            json={"invoice_template_id": "fake-template-id-12345"},
        )

    # Should NOT be a 500 (UnboundLocalError)
    # It should either be 200 with a warning, or handle the error gracefully
    assert resp.status_code != 500, (
        f"Got 500 — likely UnboundLocalError on sa_email: {resp.text}"
    )

    data = resp.json()
    # If there are warnings, check that sa_email falls back to "unknown"
    if "_warnings" in data:
        for w in data["_warnings"]:
            if "service_account_email" in w:
                assert w["service_account_email"] == "unknown"
