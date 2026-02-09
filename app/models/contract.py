from pydantic import BaseModel


class ContractCreate(BaseModel):
    project_id: str
    total_amount: float = 0
    signed_at: str | None = None
    file_path: str | None = None
    notes: str | None = None


class ContractTaskCreate(BaseModel):
    name: str
    description: str | None = None
    amount: float = 0


class ContractTaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    amount: float | None = None
