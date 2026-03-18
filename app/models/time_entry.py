import datetime as dt
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class TimeEntryCreate(BaseModel):
    employee_id: str
    project_id: str
    contract_task_id: Optional[str] = None
    hours: Decimal
    date: dt.date
    description: Optional[str] = None


class TimeEntryUpdate(BaseModel):
    employee_id: Optional[str] = None
    project_id: Optional[str] = None
    contract_task_id: Optional[str] = None
    hours: Optional[Decimal] = None
    date: Optional[dt.date] = None
    description: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: str
    employee_id: str
    project_id: str
    contract_task_id: Optional[str] = None
    hours: Decimal
    date: dt.date
    description: Optional[str] = None
    employee_name: Optional[str] = None
    project_name: Optional[str] = None
    contract_task_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
