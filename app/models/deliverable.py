from datetime import date, datetime

from pydantic import BaseModel


class DeliverableCreate(BaseModel):
    name: str
    contract_task_id: str | None = None
    sort_order: int = 0
    status: str = "not_started"
    progress_percent: float = 0
    deadline: date | str | None = None


class DeliverableUpdate(BaseModel):
    name: str | None = None
    contract_task_id: str | None = None
    sort_order: int | None = None
    status: str | None = None
    progress_percent: float | None = None
    deadline: date | str | None = None
    updated_by: str | None = None  # employee id; auto-stamped if omitted


class DeliverableResponse(BaseModel):
    id: str
    project_id: str
    contract_task_id: str | None = None
    name: str
    sort_order: int = 0
    status: str = "not_started"
    progress_percent: float = 0
    deadline: date | str | None = None
    sent_at: datetime | str | None = None
    updated_by: str | None = None
    updated_by_name: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
