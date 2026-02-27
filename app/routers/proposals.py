import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from ..activity_log import log_activity
from ..config import settings
from ..database import get_db
from ..engineers import CHANGES_TASK, ENGINEERS, RATES, load_default_tasks
from ..models.proposal import (
    ProposalCreate,
    ProposalGenerate,
    ProposalTaskCreate,
    ProposalTaskUpdate,
    ProposalUpdate,
)
from ..utils import generate_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Defaults (fixed route before parameterized ones)
# ---------------------------------------------------------------------------

@router.get("/defaults")
def get_defaults():
    """Return default tasks, engineers, and rates for the proposal form."""
    return {
        "tasks": load_default_tasks(),
        "changes_task": CHANGES_TASK,
        "engineers": ENGINEERS,
        "rates": RATES,
    }


# ---------------------------------------------------------------------------
# List proposals
# ---------------------------------------------------------------------------

@router.get("")
def list_proposals(
    project_id: str | None = Query(None),
    status: str | None = Query(None),
    db=Depends(get_db),
):
    query = "SELECT * FROM proposals WHERE deleted_at IS NULL"
    params: list = []
    if project_id:
        query += " AND project_id = %s"
        params.append(project_id)
    if status:
        query += " AND status = %s"
        params.append(status)
    query += " ORDER BY created_at DESC"

    rows = db.execute(query, params).fetchall()
    results = []
    for row in rows:
        p = dict(row)
        tasks = db.execute(
            "SELECT * FROM proposal_tasks WHERE proposal_id = %s ORDER BY sort_order",
            (p["id"],),
        ).fetchall()
        p["tasks"] = [dict(t) for t in tasks]
        results.append(p)
    return results


# ---------------------------------------------------------------------------
# Generate (all-in-one) — fixed route before {proposal_id}
# ---------------------------------------------------------------------------

@router.post("/generate", status_code=201)
def generate_proposal(data: ProposalGenerate, db=Depends(get_db)):
    """All-in-one: auto-create client/project if needed, create proposal + tasks,
    optionally render template and upload Google Doc."""
    now = datetime.now().isoformat()

    # --- Resolve or create client ---
    client_id = None
    if data.client_email:
        row = db.execute(
            "SELECT id FROM clients WHERE email = %s AND deleted_at IS NULL",
            (data.client_email,),
        ).fetchone()
        if row:
            client_id = row["id"]

    if not client_id and data.client_company:
        row = db.execute(
            "SELECT id FROM clients WHERE company = %s AND deleted_at IS NULL",
            (data.client_company,),
        ).fetchone()
        if row:
            client_id = row["id"]

    if not client_id:
        client_id = generate_id("c-")
        address_parts = []
        if data.client_address:
            address_parts.append(data.client_address)
        city_line = ", ".join(
            p for p in [data.client_city, data.client_state] if p
        )
        if data.client_zip:
            city_line = f"{city_line} {data.client_zip}" if city_line else data.client_zip
        if city_line:
            address_parts.append(city_line)
        address = "\n".join(address_parts) if address_parts else None

        db.execute(
            "INSERT INTO clients (id, name, email, company, address, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (client_id, data.client_name, data.client_email,
             data.client_company, address, now, now),
        )

        # Also create a contact for this client
        contact_id = generate_id("ct-")
        db.execute(
            "INSERT INTO contacts (id, name, email, client_id, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (contact_id, data.client_name, data.client_email, client_id, now, now),
        )

    # --- Resolve or create project ---
    project_id = data.project_id
    if project_id:
        existing = db.execute(
            "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL",
            (project_id,),
        ).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO projects (id, name, client_id, status, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'proposal', %s, %s)",
                (project_id, data.project_name, client_id, now, now),
            )
    else:
        project_id = generate_id("J")
        db.execute(
            "INSERT INTO projects (id, name, client_id, status, created_at, updated_at) "
            "VALUES (%s, %s, %s, 'proposal', %s, %s)",
            (project_id, data.project_name, client_id, now, now),
        )

    # --- Resolve engineer ---
    engineer = ENGINEERS.get(data.engineer_key or "tim", ENGINEERS["tim"])
    engineer_key = data.engineer_key or "tim"

    proposal_date = data.proposal_date or datetime.now().strftime("%B %d, %Y")

    # --- Create proposal ---
    proposal_id = generate_id("prop-")
    total_fee = sum(t.amount for t in data.tasks)

    db.execute(
        "INSERT INTO proposals (id, project_id, client_company, client_contact_email, "
        "total_fee, engineer_key, engineer_name, engineer_title, contact_method, "
        "proposal_date, status, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', %s, %s)",
        (proposal_id, project_id, data.client_company, data.client_email,
         total_fee, engineer_key, engineer["name"], engineer["title"],
         data.contact_method, proposal_date, now, now),
    )

    for i, task in enumerate(data.tasks):
        task_id = generate_id("ptask-")
        db.execute(
            "INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (task_id, proposal_id, i + 1, task.name, task.description, task.amount, now),
        )

    log_activity(db, action="created", entity_type="proposal", entity_id=proposal_id, project_id=project_id,
                 metadata={"total_fee": float(total_fee), "engineer": engineer_key})
    db.commit()

    # --- Optionally generate Google Doc ---
    result = _get_proposal_with_tasks(db, proposal_id)
    result["_warning"] = None

    if data.generate_doc:
        try:
            from ..proposal_renderer import generate_proposal_doc

            doc_url = generate_proposal_doc(
                project_name=data.project_name,
                client_name=data.client_name,
                client_company=data.client_company or "",
                client_address=data.client_address or "",
                client_city=data.client_city or "",
                client_state=data.client_state or "",
                client_zip=data.client_zip or "",
                engineer_key=engineer_key,
                contact_method=data.contact_method or "conversation",
                proposal_date=proposal_date,
                tasks=[{"name": t.name, "description": t.description, "amount": t.amount} for t in data.tasks],
            )

            db.execute(
                "UPDATE proposals SET data_path = %s, updated_at = %s WHERE id = %s",
                (doc_url, datetime.now().isoformat(), proposal_id),
            )
            db.commit()
            result["data_path"] = doc_url
        except Exception as e:
            logger.warning("Google Doc generation failed: %s", e)
            result["_warning"] = "Proposal created but Google Doc generation failed. Check server logs."

    if result["_warning"] is None:
        del result["_warning"]

    return result


# ---------------------------------------------------------------------------
# Get single proposal — after fixed routes
# ---------------------------------------------------------------------------

@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, db=Depends(get_db)):
    return _get_proposal_with_tasks(db, proposal_id)


# ---------------------------------------------------------------------------
# Create proposal (standard CRUD)
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def create_proposal(data: ProposalCreate, db=Depends(get_db)):
    # Verify project exists
    project = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (data.project_id,)
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()
    proposal_id = generate_id("prop-")

    total_fee = data.total_fee
    if total_fee == 0 and data.tasks:
        total_fee = sum(t.amount for t in data.tasks)

    db.execute(
        "INSERT INTO proposals (id, project_id, client_company, client_contact_email, "
        "total_fee, engineer_key, engineer_name, engineer_title, contact_method, "
        "proposal_date, status, data_path, pdf_path, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (proposal_id, data.project_id, data.client_company, data.client_contact_email,
         total_fee, data.engineer_key, data.engineer_name, data.engineer_title,
         data.contact_method, data.proposal_date,
         data.status, data.data_path, data.pdf_path, now, now),
    )

    if data.tasks:
        for i, task in enumerate(data.tasks):
            task_id = generate_id("ptask-")
            db.execute(
                "INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (task_id, proposal_id, i + 1, task.name, task.description, task.amount, now),
            )

    db.commit()
    return _get_proposal_with_tasks(db, proposal_id)


# ---------------------------------------------------------------------------
# Update proposal
# ---------------------------------------------------------------------------

@router.patch("/{proposal_id}")
def update_proposal(
    proposal_id: str,
    data: ProposalUpdate,
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposals WHERE id = %s AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return _get_proposal_with_tasks(db, proposal_id)

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [proposal_id]
    db.execute(f"UPDATE proposals SET {set_clause} WHERE id = %s", values)
    db.commit()
    return _get_proposal_with_tasks(db, proposal_id)


# ---------------------------------------------------------------------------
# Delete proposal
# ---------------------------------------------------------------------------

@router.delete("/{proposal_id}")
def delete_proposal(proposal_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM proposals WHERE id = %s AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Proposal not found")

    now = datetime.now().isoformat()
    db.execute("UPDATE proposals SET deleted_at = %s WHERE id = %s", (now, proposal_id))
    log_activity(db, action="deleted", entity_type="proposal", entity_id=proposal_id,
                 project_id=existing["project_id"])
    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Generate Doc for existing proposal
# ---------------------------------------------------------------------------

@router.post("/{proposal_id}/generate-doc")
def generate_doc(proposal_id: str, db=Depends(get_db)):
    """Generate a Google Doc for an existing proposal."""
    proposal = _get_proposal_dict(db, proposal_id)
    tasks = db.execute(
        "SELECT * FROM proposal_tasks WHERE proposal_id = %s ORDER BY sort_order",
        (proposal_id,),
    ).fetchall()
    if not tasks:
        raise HTTPException(status_code=400, detail="Proposal has no tasks")

    project = db.execute(
        "SELECT p.*, c.name as client_name, c.company as client_company, "
        "c.email as client_email, c.address as client_address "
        "FROM projects p LEFT JOIN clients c ON p.client_id = c.id "
        "WHERE p.id = %s AND p.deleted_at IS NULL",
        (proposal["project_id"],),
    ).fetchone()

    client_address = ""
    client_city = ""
    client_state = ""
    client_zip = ""
    if project and project["client_address"]:
        lines = project["client_address"].split("\n")
        client_address = lines[0] if lines else ""
        if len(lines) > 1:
            parts = lines[1].split(",", 1)
            client_city = parts[0].strip()
            if len(parts) > 1:
                rest = parts[1].strip().split()
                client_state = rest[0] if rest else ""
                client_zip = rest[1] if len(rest) > 1 else ""

    try:
        from ..proposal_renderer import generate_proposal_doc

        project_name = project["name"] if project else "Untitled"
        doc_url = generate_proposal_doc(
            project_name=project_name,
            client_name=project["client_name"] if project else "",
            client_company=proposal["client_company"] or (project["client_company"] if project else ""),
            client_address=client_address,
            client_city=client_city,
            client_state=client_state,
            client_zip=client_zip,
            engineer_key=proposal["engineer_key"] or "tim",
            contact_method=proposal["contact_method"] or "conversation",
            proposal_date=proposal["proposal_date"] or datetime.now().strftime("%B %d, %Y"),
            tasks=[{"name": dict(t)["name"], "description": dict(t).get("description"), "amount": dict(t)["amount"]} for t in tasks],
        )

        now = datetime.now().isoformat()
        db.execute(
            "UPDATE proposals SET data_path = %s, updated_at = %s WHERE id = %s",
            (doc_url, now, proposal_id),
        )
        db.commit()

        result = _get_proposal_with_tasks(db, proposal_id)
        result["data_path"] = doc_url
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Export PDF
# ---------------------------------------------------------------------------

@router.post("/{proposal_id}/export-pdf")
def export_pdf(proposal_id: str, db=Depends(get_db)):
    """Export proposal Google Doc as PDF, upload to Drive."""
    proposal = _get_proposal_dict(db, proposal_id)

    if not proposal["data_path"] or "docs.google.com" not in (proposal["data_path"] or ""):
        raise HTTPException(status_code=400, detail="No Google Doc URL found. Generate doc first.")

    doc_id = _extract_google_doc_id(proposal["data_path"])
    if not doc_id:
        raise HTTPException(status_code=400, detail="Could not parse Google Doc ID from URL")

    try:
        from ..proposal_renderer import export_google_doc_as_pdf
        from ..google_sheets import upload_pdf_to_drive

        pdf_bytes = export_google_doc_as_pdf(doc_id)

        project = db.execute(
            "SELECT name FROM projects WHERE id = %s AND deleted_at IS NULL", (proposal["project_id"],)
        ).fetchone()
        pdf_filename = f"Proposal - {project['name'] if project else proposal_id}.pdf"

        pdf_url = upload_pdf_to_drive(pdf_bytes, pdf_filename, folder_id=settings.proposal_drive_folder_id)

        now = datetime.now().isoformat()
        db.execute(
            "UPDATE proposals SET pdf_path = %s, updated_at = %s WHERE id = %s",
            (pdf_url, now, proposal_id),
        )
        db.commit()

        result = _get_proposal_with_tasks(db, proposal_id)
        result["pdf_path"] = pdf_url
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Send proposal via email
# ---------------------------------------------------------------------------

@router.post("/{proposal_id}/send")
def send_proposal(proposal_id: str, db=Depends(get_db)):
    """Export PDF and email to client."""
    proposal = _get_proposal_dict(db, proposal_id)

    if not proposal["data_path"] or "docs.google.com" not in (proposal["data_path"] or ""):
        raise HTTPException(status_code=400, detail="No Google Doc found. Generate doc first.")

    doc_id = _extract_google_doc_id(proposal["data_path"])
    if not doc_id:
        raise HTTPException(status_code=400, detail="Could not parse Google Doc ID")

    to_email = proposal["client_contact_email"]
    if not to_email:
        row = db.execute(
            "SELECT c.email FROM projects p JOIN clients c ON p.client_id = c.id "
            "WHERE p.id = %s AND p.deleted_at IS NULL",
            (proposal["project_id"],),
        ).fetchone()
        if row:
            to_email = row["email"]
    if not to_email:
        raise HTTPException(status_code=400, detail="No client email found")

    try:
        from ..proposal_renderer import export_google_doc_as_pdf
        from ..google_sheets import upload_pdf_to_drive, send_invoice_email

        pdf_bytes = export_google_doc_as_pdf(doc_id)

        project = db.execute(
            "SELECT name FROM projects WHERE id = %s AND deleted_at IS NULL", (proposal["project_id"],)
        ).fetchone()
        project_name = project["name"] if project else "Project"
        pdf_filename = f"Proposal - {project_name}.pdf"

        pdf_url = upload_pdf_to_drive(pdf_bytes, pdf_filename, folder_id=settings.proposal_drive_folder_id)

        company_email_row = db.execute(
            "SELECT value FROM company_settings WHERE key = 'company_email'"
        ).fetchone()
        from_email = company_email_row["value"] if company_email_row else None

        subject = f"Proposal - {project_name}"
        body = (
            f"Please find attached our proposal for {project_name}.\n\n"
            f"If you have any questions, please don't hesitate to reach out.\n\n"
            f"Thank you,\n{proposal['engineer_name'] or 'The Irrigation Engineers'}"
        )

        send_invoice_email(
            to_emails=[to_email],
            subject=subject,
            body_text=body,
            pdf_bytes=pdf_bytes,
            pdf_filename=pdf_filename,
            from_email=from_email,
        )

        now = datetime.now().isoformat()
        db.execute(
            "UPDATE proposals SET pdf_path = %s, sent_at = %s, status = 'sent', updated_at = %s WHERE id = %s",
            (pdf_url, now, now, proposal_id),
        )
        log_activity(db, action="sent", entity_type="proposal", entity_id=proposal_id,
                     project_id=proposal["project_id"], metadata={"sent_to": to_email})
        db.commit()

        result = _get_proposal_with_tasks(db, proposal_id)
        result["sent_to"] = [to_email]
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---------------------------------------------------------------------------
# Proposal Tasks CRUD
# ---------------------------------------------------------------------------

@router.post("/{proposal_id}/tasks")
def add_proposal_task(
    proposal_id: str,
    data: ProposalTaskCreate,
    db=Depends(get_db),
):
    _get_proposal_dict(db, proposal_id)

    now = datetime.now().isoformat()
    task_id = generate_id("ptask-")

    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) as max_order FROM proposal_tasks WHERE proposal_id = %s",
        (proposal_id,),
    ).fetchone()["max_order"]

    db.execute(
        "INSERT INTO proposal_tasks (id, proposal_id, sort_order, name, description, amount, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (task_id, proposal_id, max_order + 1, data.name, data.description, data.amount, now),
    )

    _update_proposal_total(db, proposal_id)
    db.commit()
    return _get_proposal_with_tasks(db, proposal_id)


@router.patch("/{proposal_id}/tasks/{task_id}")
def update_proposal_task(
    proposal_id: str,
    task_id: str,
    data: ProposalTaskUpdate,
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposal_tasks WHERE id = %s AND proposal_id = %s",
        (task_id, proposal_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        return _get_proposal_with_tasks(db, proposal_id)

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [task_id]
    db.execute(f"UPDATE proposal_tasks SET {set_clause} WHERE id = %s", values)

    _update_proposal_total(db, proposal_id)
    db.commit()
    return _get_proposal_with_tasks(db, proposal_id)


@router.delete("/{proposal_id}/tasks/{task_id}")
def delete_proposal_task(
    proposal_id: str,
    task_id: str,
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM proposal_tasks WHERE id = %s AND proposal_id = %s",
        (task_id, proposal_id),
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Task not found")

    db.execute("DELETE FROM proposal_tasks WHERE id = %s", (task_id,))
    _update_proposal_total(db, proposal_id)
    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Promote to Contract
# ---------------------------------------------------------------------------

@router.post("/{proposal_id}/promote")
def promote_to_contract(
    proposal_id: str,
    signed_at: str | None = None,
    file_path: str | None = None,
    db=Depends(get_db),
):
    proposal = _get_proposal_dict(db, proposal_id)

    now = datetime.now().isoformat()
    contract_id = generate_id("con-")
    project_id = proposal["project_id"]

    db.execute(
        "INSERT INTO contracts (id, project_id, total_amount, signed_at, file_path, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (contract_id, project_id, proposal["total_fee"],
         signed_at or now, file_path, now, now),
    )

    tasks = db.execute(
        "SELECT * FROM proposal_tasks WHERE proposal_id = %s ORDER BY sort_order",
        (proposal_id,),
    ).fetchall()

    for task in tasks:
        ctask_id = generate_id("ctask-")
        db.execute(
            "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, "
            "billed_amount, billed_percent, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, 0, 0, %s, %s)",
            (ctask_id, contract_id, task["sort_order"], task["name"],
             task["description"], task["amount"], now, now),
        )

    db.execute(
        "UPDATE proposals SET status = 'accepted', updated_at = %s WHERE id = %s",
        (now, proposal_id),
    )
    db.execute(
        "UPDATE projects SET status = 'contract', updated_at = %s WHERE id = %s",
        (now, project_id),
    )
    log_activity(db, action="promoted", entity_type="proposal", entity_id=proposal_id,
                 project_id=project_id, metadata={"contract_id": contract_id})

    db.commit()

    contract = db.execute("SELECT * FROM contracts WHERE id = %s", (contract_id,)).fetchone()
    result = dict(contract)
    contract_tasks = db.execute(
        "SELECT * FROM contract_tasks WHERE contract_id = %s ORDER BY sort_order",
        (contract_id,),
    ).fetchall()
    result["tasks"] = [dict(t) for t in contract_tasks]
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_proposal_dict(db, proposal_id: str) -> dict:
    row = db.execute(
        "SELECT * FROM proposals WHERE id = %s AND deleted_at IS NULL", (proposal_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return dict(row)


def _get_proposal_with_tasks(db, proposal_id: str) -> dict:
    proposal = _get_proposal_dict(db, proposal_id)
    tasks = db.execute(
        "SELECT * FROM proposal_tasks WHERE proposal_id = %s ORDER BY sort_order",
        (proposal_id,),
    ).fetchall()
    proposal["tasks"] = [dict(t) for t in tasks]
    return proposal


def _update_proposal_total(db, proposal_id: str):
    total = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM proposal_tasks WHERE proposal_id = %s",
        (proposal_id,),
    ).fetchone()["total"]
    db.execute(
        "UPDATE proposals SET total_fee = %s, updated_at = %s WHERE id = %s",
        (total, datetime.now().isoformat(), proposal_id),
    )


def _extract_google_doc_id(url: str) -> str | None:
    if not url:
        return None
    parts = url.split("/d/")
    if len(parts) < 2:
        return None
    doc_id = parts[1].split("/")[0]
    return doc_id if doc_id else None
