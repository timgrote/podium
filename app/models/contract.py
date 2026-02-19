from pydantic import BaseModel


class ContractCreate(BaseModel):
    project_id: str
    total_amount: float = 0
    signed_at: str | None = None
    file_path: str | None = None
    dropbox_url: str | None = None
    notes: str | None = None
    tasks: list[dict] | None = None


class ContractUpdate(BaseModel):
    signed_at: str | None = None
    file_path: str | None = None
    dropbox_url: str | None = None
    notes: str | None = None
    tasks: list[dict] | None = None  # Full replacement of tasks when provided


class ContractTaskCreate(BaseModel):
    name: str
    description: str | None = None
    amount: float = 0


class ContractTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    amount: float | None = None
