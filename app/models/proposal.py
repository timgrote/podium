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
    engineer_key: str | None = None
    engineer_name: str | None = None
    engineer_title: str | None = None
    contact_method: str | None = None
    proposal_date: str | None = None
    status: str = "draft"
    data_path: str | None = None
    pdf_path: str | None = None
    tasks: list[ProposalTaskCreate] | None = None


class ProposalUpdate(BaseModel):
    client_company: str | None = None
    client_contact_email: str | None = None
    total_fee: float | None = None
    engineer_key: str | None = None
    engineer_name: str | None = None
    engineer_title: str | None = None
    contact_method: str | None = None
    proposal_date: str | None = None
    status: str | None = None
    sent_at: str | None = None
    data_path: str | None = None
    pdf_path: str | None = None


class ProposalGenerateTask(BaseModel):
    name: str
    description: str | None = None
    amount: float = 0


class ProposalGenerate(BaseModel):
    """All-in-one input for bot/API proposal generation.
    Auto-creates client/project if needed."""
    client_name: str
    client_email: str | None = None
    client_company: str | None = None
    client_address: str | None = None
    client_city: str | None = None
    client_state: str | None = None
    client_zip: str | None = None
    project_name: str
    project_id: str | None = None
    engineer_key: str | None = None
    contact_method: str | None = None
    proposal_date: str | None = None
    tasks: list[ProposalGenerateTask]
    generate_doc: bool = True
