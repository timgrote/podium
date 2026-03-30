from datetime import datetime

from pydantic import BaseModel


class WikiNoteCreate(BaseModel):
    title: str
    content: str = ""
    category: str = "General"
    created_by: str | None = None


class WikiNoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    updated_by: str | None = None


class WikiNoteResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    created_by: str | None = None
    updated_by: str | None = None
    created_by_name: str | None = None
    updated_by_name: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
