from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class ClientResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    company: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
