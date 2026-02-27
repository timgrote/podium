from datetime import datetime

from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    notes: str | None = None
    client_id: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    notes: str | None = None
    client_id: str | None = None


class ContactResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    notes: str | None = None
    client_id: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class ContactNoteCreate(BaseModel):
    content: str
    author_id: str | None = None


class ContactNoteResponse(BaseModel):
    id: str
    contact_id: str
    author_id: str | None = None
    author_name: str | None = None
    author_avatar_url: str | None = None
    content: str
    created_at: datetime | str | None = None
