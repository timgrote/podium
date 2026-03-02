from datetime import datetime

from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    accounting_email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class ClientResponse(BaseModel):
    id: str
    name: str
    accounting_email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class ClientNoteCreate(BaseModel):
    content: str
    author_id: str | None = None


class ClientNoteResponse(BaseModel):
    id: str
    client_id: str
    author_id: str | None = None
    author_name: str | None = None
    author_avatar_url: str | None = None
    content: str
    created_at: datetime | str | None = None
