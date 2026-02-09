from pydantic import BaseModel


class ProposalTaskCreate(BaseModel):
    name: str
    description: str | None = None
    amount: float = 0


class ProposalTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    amount: float | None = None
    sort_order: int | None = None


class ProposalCreate(BaseModel):
    project_id: str
    client_company: str | None = None
    client_contact_email: str | None = None
    total_fee: float = 0
    status: str = "draft"
    data_path: str | None = None
    pdf_path: str | None = None
    tasks: list[ProposalTaskCreate] | None = None


class ProposalUpdate(BaseModel):
    client_company: str | None = None
    client_contact_email: str | None = None
    total_fee: float | None = None
    status: str | None = None
    sent_at: str | None = None
    data_path: str | None = None
    pdf_path: str | None = None
