from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    created_at: datetime | str | None = None
    last_used_at: datetime | str | None = None
    expires_at: datetime | str | None = None


class ApiKeyCreateResponse(ApiKeyResponse):
    raw_key: str
