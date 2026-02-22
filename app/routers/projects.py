from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..models.project import ProjectCreate, ProjectDetail, ProjectNoteCreate, ProjectNoteResponse, ProjectSummary, ProjectUpdate
from ..utils import generate_id, next_invoice_number, next_project_number

router = APIRouter()


def _get_contracts_for_project(db, project_id: str) -> list[dict]:
    from .contracts import _compute_task_billing

    contracts = []
    rows = db.execute(
        "SELECT * FROM contracts WHERE project_id = %s AND deleted_at IS NULL ORDER BY created_at",
        (project_id,),
    ).fetchall()
    for c in rows:
        contract = dict(c)
        tasks = db.execute(
            "SELECT * FROM contract_tasks WHERE contract_id = %s ORDER BY sort_order",
            (c["id"],),
        ).fetchall()
        contract["tasks"] = _compute_task_billing(db, c["id"], [dict(t) for t in tasks])
        contracts.append(contract)
    return contracts


def _get_invoices_for_project(db, project_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM invoices WHERE project_id = %s AND deleted_at IS NULL ORDER BY created_at",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_proposals_for_project(db, project_id: str) -> list[dict]:
    rows = db.execute(
        "SELECT * FROM proposals WHERE project_id = %s AND deleted_at IS NULL ORDER BY created_at",
        (project_id,),
    ).fetchall()
    proposals = []
    for p in rows:
        proposal = dict(p)
        tasks = db.execute(
            "SELECT * FROM proposal_tasks WHERE proposal_id = %s ORDER BY sort_order",
            (p["id"],),
        ).fetchall()
        proposal["tasks"] = [dict(t) for t in tasks]
        proposals.append(proposal)
    return proposals


@router.get("", response_model=list[ProjectSummary])
def list_projects(db=Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM v_project_summary ORDER BY id"
    ).fetchall()

    projects = []
    for r in rows:
        p = dict(r)
        project_id = p["id"]

        # Get client email
        client_email = None
        if p.get("client_id"):
            client_row = db.execute(
                "SELECT email FROM clients WHERE id = %s", (p["client_id"],)
            ).fetchone()
            if client_row:
                client_email = client_row["email"]

        contracts = _get_contracts_for_project(db, project_id)
        invoices = _get_invoices_for_project(db, project_id)
        proposals = _get_proposals_for_project(db, project_id)

        projects.append(ProjectSummary(
            id=project_id,
            project_number=p.get("project_number"),
            job_code=p.get("job_code"),
            project_name=p["name"],
            status=p["status"],
            client_id=p.get("client_id"),
            client_name=p.get("client_name"),
            client_company=p.get("client_company"),
            client_email=p.get("client_email") or client_email,
            pm_id=p.get("pm_id"),
            pm_name=p.get("pm_name"),
            pm_email=p.get("pm_email"),
            pm_avatar_url=p.get("pm_avatar_url"),
            client_project_number=p.get("client_project_number"),
            location=p.get("location"),
            data_path=p.get("data_path"),
            total_contracted=p.get("total_contracted", 0),
            total_invoiced=p.get("total_invoiced", 0),
            total_paid=p.get("total_paid", 0),
            total_outstanding=p.get("total_outstanding", 0),
            contracts=contracts,
            invoices=invoices,
            proposals=proposals,
        ))
    return projects


# --- Project Notes (before /{project_id} to avoid route shadowing) ---


@router.get("/notes/{note_id}", response_model=ProjectNoteResponse)
def get_project_note(note_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT n.id, n.project_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.id = %s",
        (note_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@router.delete("/notes/{note_id}")
def delete_project_note(note_id: str, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM project_notes WHERE id = %s", (note_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    db.execute("DELETE FROM project_notes WHERE id = %s", (note_id,))
    db.commit()
    return {"success": True}


@router.get("/{project_id}/notes", response_model=list[ProjectNoteResponse])
def list_project_notes(project_id: str, db=Depends(get_db)):
    rows = db.execute(
        "SELECT n.id, n.project_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.project_id = %s "
        "ORDER BY n.created_at DESC",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/{project_id}/notes", response_model=ProjectNoteResponse, status_code=201)
def add_project_note(project_id: str, data: ProjectNoteCreate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    note_id = generate_id("pnote-")
    now = datetime.now().isoformat()
    db.execute(
        "INSERT INTO project_notes (id, project_id, author_id, content, created_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (note_id, project_id, data.author_id, data.content, now),
    )
    db.commit()

    row = db.execute(
        "SELECT n.id, n.project_id, n.author_id, n.content, n.created_at, "
        "e.first_name || ' ' || e.last_name AS author_name "
        "FROM project_notes n "
        "LEFT JOIN employees e ON n.author_id = e.id "
        "WHERE n.id = %s",
        (note_id,),
    ).fetchone()
    return dict(row)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db=Depends(get_db)):
    row = db.execute(
        "SELECT * FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    p = dict(row)

    # Client info
    client_name = client_company = client_email = client_phone = None
    if p.get("client_id"):
        client_row = db.execute(
            "SELECT name, company, email, phone FROM clients WHERE id = %s", (p["client_id"],)
        ).fetchone()
        if client_row:
            client_name = client_row["name"]
            client_company = client_row["company"]
            client_email = client_row["email"]
            client_phone = client_row["phone"]

    # Summary totals
    summary = db.execute(
        "SELECT * FROM v_project_summary WHERE id = %s", (project_id,)
    ).fetchone()

    contracts = _get_contracts_for_project(db, project_id)
    invoices = _get_invoices_for_project(db, project_id)
    proposals = _get_proposals_for_project(db, project_id)

    return ProjectDetail(
        id=project_id,
        project_number=p.get("project_number"),
        job_code=p.get("job_code"),
        project_name=p["name"],
        status=p["status"],
        client_id=p.get("client_id"),
        client_name=client_name,
        client_company=client_company,
        client_email=client_email,
        client_phone=client_phone,
        pm_id=p.get("pm_id"),
        pm_name=p.get("pm_name"),
        pm_email=p.get("pm_email"),
        pm_avatar_url=summary["pm_avatar_url"] if summary else None,
        client_project_number=p.get("client_project_number"),
        location=p.get("location"),
        data_path=p.get("data_path"),
        notes=p.get("notes"),
        current_invoice_id=p.get("current_invoice_id"),
        total_contracted=summary["total_contracted"] if summary else 0,
        total_invoiced=summary["total_invoiced"] if summary else 0,
        total_paid=summary["total_paid"] if summary else 0,
        total_outstanding=summary["total_outstanding"] if summary else 0,
        contracts=contracts,
        invoices=invoices,
        proposals=proposals,
        created_at=p.get("created_at"),
        updated_at=p.get("updated_at"),
    )


@router.post("", response_model=ProjectDetail, status_code=201)
def create_project(data: ProjectCreate, db=Depends(get_db)):
    now = datetime.now().isoformat()
    project_id = generate_id("proj-")
    project_number = next_project_number(db)

    # Auto-create client if info provided but no client_id
    client_id = data.client_id
    if not client_id and data.client_email:
        existing = db.execute(
            "SELECT id FROM clients WHERE email = %s AND deleted_at IS NULL", (data.client_email,)
        ).fetchone()
        if existing:
            client_id = existing["id"]
        elif data.client_name:
            client_id = generate_id("c-")
            db.execute(
                "INSERT INTO clients (id, name, email, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                (client_id, data.client_name, data.client_email, now, now),
            )

    # Resolve PM name/email from employee if pm_id provided
    pm_id = data.pm_id
    pm_name = None
    pm_email = None
    if pm_id:
        emp = db.execute(
            "SELECT first_name, last_name, email FROM employees WHERE id = %s AND deleted_at IS NULL",
            (pm_id,),
        ).fetchone()
        if emp:
            pm_name = f"{emp['first_name']} {emp['last_name']}"
            pm_email = emp["email"]

    db.execute(
        "INSERT INTO projects (id, name, client_id, pm_id, pm_name, pm_email, location, project_number, job_code, status, data_path, notes, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (project_id, data.project_name, client_id, pm_id, pm_name, pm_email, data.location, project_number, data.job_code, data.status, data.data_path, data.notes, now, now),
    )

    # Create contract + tasks if provided
    if data.contract or (data.tasks and len(data.tasks) > 0):
        contract_id = generate_id("con-")
        total = sum(t.get("amount", 0) for t in (data.tasks or []))
        signed_at = data.contract.get("signed_date") if data.contract else None
        file_path = data.contract.get("file_path") if data.contract else None

        db.execute(
            "INSERT INTO contracts (id, project_id, total_amount, signed_at, file_path, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (contract_id, project_id, total, signed_at, file_path, now, now),
        )

        for i, task in enumerate(data.tasks or []):
            task_id = generate_id("ctask-")
            db.execute(
                "INSERT INTO contract_tasks (id, contract_id, sort_order, name, description, amount, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (task_id, contract_id, i + 1, task["name"], task.get("description"), task.get("amount", 0), now, now),
            )

    db.commit()
    return get_project(project_id, db)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: str, data: ProjectUpdate, db=Depends(get_db)):
    existing = db.execute(
        "SELECT * FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not updates:
        return get_project(project_id, db)

    # If pm_id is being set, sync pm_name/pm_email from employee
    if "pm_id" in updates:
        pm_id = updates["pm_id"]
        if pm_id:
            emp = db.execute(
                "SELECT first_name, last_name, email FROM employees WHERE id = %s AND deleted_at IS NULL",
                (pm_id,),
            ).fetchone()
            if emp:
                updates["pm_name"] = f"{emp['first_name']} {emp['last_name']}"
                updates["pm_email"] = emp["email"]
        else:
            # Clearing pm_id also clears pm_name/pm_email
            updates["pm_name"] = None
            updates["pm_email"] = None

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [project_id]
    db.execute(f"UPDATE projects SET {set_clause} WHERE id = %s", values)
    db.commit()
    return get_project(project_id, db)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    cascade: bool = False,
    db=Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()

    if cascade:
        # Soft-delete contracts and invoices
        db.execute(
            "UPDATE contracts SET deleted_at = %s WHERE project_id = %s AND deleted_at IS NULL",
            (now, project_id),
        )
        db.execute(
            "UPDATE invoices SET deleted_at = %s WHERE project_id = %s AND deleted_at IS NULL",
            (now, project_id),
        )
        db.execute(
            "UPDATE proposals SET deleted_at = %s WHERE project_id = %s AND deleted_at IS NULL",
            (now, project_id),
        )

    db.execute("UPDATE projects SET deleted_at = %s WHERE id = %s", (now, project_id))
    db.commit()
    return {"success": True}


@router.post("/{project_id}/invoices")
def add_invoice_to_project(
    project_id: str,
    invoice_number: str | None = None,
    invoice_type: str = "list",
    description: str | None = None,
    total_due: float = 0,
    db=Depends(get_db),
):
    """Add a standalone (non-contract) invoice to a project."""
    existing = db.execute(
        "SELECT * FROM projects WHERE id = %s AND deleted_at IS NULL", (project_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now().isoformat()
    inv_id = generate_id("inv-")

    if not invoice_number:
        invoice_number = next_invoice_number(db, project_id)

    db.execute(
        "INSERT INTO invoices (id, invoice_number, project_id, type, description, total_due, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (inv_id, invoice_number, project_id, invoice_type, description, total_due, now, now),
    )
    db.commit()

    row = db.execute("SELECT * FROM invoices WHERE id = %s", (inv_id,)).fetchone()
    return dict(row)
