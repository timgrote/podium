from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    project_name: str
    job_code: str | None = None
    client_name: str | None = None
    client_email: str | None = None
    client_id: str | None = None
    pm_id: str | None = None
    location: str | None = None
    status: str = "proposal"
    data_path: str | None = None
    notes: str | None = None
    tasks: list[dict] | None = None
    contract: dict | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_id: str | None = None
    location: str | None = None
    project_number: str | None = None
    job_code: str | None = None
    status: str | None = None
    data_path: str | None = None
    notes: str | None = None
    pm_id: str | None = None
    pm_name: str | None = None
    pm_email: str | None = None
    client_project_number: str | None = None


class ProjectSummary(BaseModel):
    id: str
    project_number: str | None = None
    job_code: str | None = None
    project_name: str | None = None
    status: str
    client_id: str | None = None
    client_name: str | None = None
    client_company: str | None = None
    client_email: str | None = None
    pm_id: str | None = None
    pm_name: str | None = None
    pm_email: str | None = None
    pm_avatar_url: str | None = None
    client_project_number: str | None = None
    location: str | None = None
    data_path: str | None = None
    total_contracted: float = 0
    total_invoiced: float = 0
    total_paid: float = 0
    total_outstanding: float = 0
    contracts: list[dict] = []
    invoices: list[dict] = []
    proposals: list[dict] = []


class ProjectNoteCreate(BaseModel):
    content: str
    author_id: str | None = None


class ProjectNoteResponse(BaseModel):
    id: str
    project_id: str
    author_id: str | None = None
    author_name: str | None = None
    content: str
    created_at: datetime | str | None = None


class ProjectDetail(ProjectSummary):
    data_path: str | None = None
    notes: str | None = None
    client_phone: str | None = None
    current_invoice_id: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
