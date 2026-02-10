import os
from datetime import datetime

from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..config import settings
from ..database import get_db
from ..utils import generate_id

router = APIRouter()


@router.post("/proposals")
async def submit_proposal(
    job_id: str = Form(...),
    client_name: str = Form(...),
    client_email: str = Form(...),
    project_name: str = Form(...),
    amount: float = Form(...),
    turnaround: int = Form(5),
    scope: str = Form(""),
    proposal_pdf: UploadFile | None = File(None),
    db=Depends(get_db),
):
    now = datetime.now().isoformat()

    # Find or create client
    client_row = db.execute(
        "SELECT id FROM clients WHERE email = %s AND deleted_at IS NULL", (client_email,)
    ).fetchone()
    if client_row:
        client_id = client_row["id"]
    else:
        client_id = generate_id("c-")
        db.execute(
            "INSERT INTO clients (id, name, email, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
            (client_id, client_name, client_email, now, now),
        )

    # Find or create project
    project = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (job_id,)
    ).fetchone()
    if not project:
        db.execute(
            "INSERT INTO projects (id, name, client_id, status, created_at, updated_at) "
            "VALUES (%s, %s, %s, 'proposal', %s, %s)",
            (job_id, project_name, client_id, now, now),
        )

    # Save uploaded file
    pdf_path = None
    if proposal_pdf and proposal_pdf.filename:
        os.makedirs(settings.upload_dir, exist_ok=True)
        safe_name = PurePath(proposal_pdf.filename).name
        filename = f"{job_id}-proposal-{safe_name}"
        filepath = os.path.join(settings.upload_dir, filename)
        content = await proposal_pdf.read()
        with open(filepath, "wb") as f:
            f.write(content)
        pdf_path = f"/uploads/{filename}"

    # Create proposal
    prop_id = generate_id("prop-")
    db.execute(
        "INSERT INTO proposals (id, project_id, pdf_path, client_company, client_contact_email, "
        "total_fee, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, 'sent', %s, %s)",
        (prop_id, job_id, pdf_path, None, client_email, amount, now, now),
    )

    db.commit()
    return {"success": True, "proposal_id": prop_id}


@router.post("/contracts")
async def submit_contract(
    job_id: str = Form(...),
    client_name: str = Form(...),
    client_email: str = Form(...),
    signed_contract: UploadFile | None = File(None),
    db=Depends(get_db),
):
    now = datetime.now().isoformat()

    # Save uploaded file
    file_path = None
    if signed_contract and signed_contract.filename:
        os.makedirs(settings.upload_dir, exist_ok=True)
        safe_name = PurePath(signed_contract.filename).name
        filename = f"{job_id}-contract-{safe_name}"
        filepath = os.path.join(settings.upload_dir, filename)
        content = await signed_contract.read()
        with open(filepath, "wb") as f:
            f.write(content)
        file_path = f"/uploads/{filename}"

    # Verify project exists
    project = db.execute(
        "SELECT id FROM projects WHERE id = %s AND deleted_at IS NULL", (job_id,)
    ).fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update project status
    db.execute(
        "UPDATE projects SET status = 'contract', updated_at = %s WHERE id = %s",
        (now, job_id),
    )

    # Create contract record if file uploaded
    if file_path:
        contract_id = generate_id("con-")
        db.execute(
            "INSERT INTO contracts (id, project_id, file_path, signed_at, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (contract_id, job_id, file_path, now, now, now),
        )

    db.commit()
    return {"success": True}


@router.post("/payments")
async def submit_payment(
    invoice: str = Form(...),
    job_id: str = Form(...),
    client_email: str = Form(...),
    confirmation: str = Form(...),
    notes: str = Form(""),
    receipt: UploadFile | None = File(None),
    db=Depends(get_db),
):
    now = datetime.now().isoformat()

    # Save receipt file
    if receipt and receipt.filename:
        os.makedirs(settings.upload_dir, exist_ok=True)
        safe_name = PurePath(receipt.filename).name
        filename = f"{job_id}-receipt-{safe_name}"
        filepath = os.path.join(settings.upload_dir, filename)
        content = await receipt.read()
        with open(filepath, "wb") as f:
            f.write(content)

    # Mark invoice as paid
    inv_row = db.execute(
        "SELECT id FROM invoices WHERE invoice_number = %s AND deleted_at IS NULL",
        (invoice,),
    ).fetchone()
    if not inv_row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.execute(
        "UPDATE invoices SET paid_status = 'paid', paid_at = %s, updated_at = %s WHERE id = %s",
        (now, now, inv_row["id"]),
    )

    db.commit()
    return {"success": True}
