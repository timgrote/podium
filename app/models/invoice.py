from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    invoice_number: str | None = None
    project_id: str
    contract_id: str | None = None
    type: str = "task"
    description: str | None = None
    total_due: float = 0


class InvoiceUpdate(BaseModel):
    sent_status: str | None = None
    paid_status: str | None = None
    paid_at: str | None = None
    total_due: float | None = None
    description: str | None = None
    data_path: str | None = None
    pdf_path: str | None = None


class InvoiceFromContract(BaseModel):
    tasks: list[dict]
    """Each dict: {"task_id": str, "percent_this_invoice": float}"""
    pm_email: str | None = None
