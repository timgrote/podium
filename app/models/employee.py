from datetime import datetime

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    bot_id: str | None = None


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    bot_id: str | None = None
    is_active: bool | None = None


class EmployeeResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str | None = None
    bot_id: str | None = None
    is_active: bool = True
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
