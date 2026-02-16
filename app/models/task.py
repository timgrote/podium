from datetime import date, datetime

from pydantic import BaseModel


class TaskNoteCreate(BaseModel):
    content: str
    author_id: str | None = None


class TaskNoteResponse(BaseModel):
    id: str
    task_id: str
    author_id: str | None = None
    author_name: str | None = None
    content: str
    created_at: datetime | str | None = None


class TaskCreate(BaseModel):
    project_id: str | None = None  # set from URL path when creating under a project
    title: str
    description: str | None = None
    status: str = "todo"
    start_date: date | str | None = None
    due_date: date | str | None = None
    reminder_at: datetime | str | None = None
    parent_id: str | None = None
    sort_order: int = 0
    assignee_ids: list[str] | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: date | str | None = None
    due_date: date | str | None = None
    reminder_at: datetime | str | None = None
    parent_id: str | None = None
    sort_order: int | None = None
    assignee_ids: list[str] | None = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    parent_id: str | None = None
    title: str
    description: str | None = None
    status: str = "todo"
    priority: int | None = None
    start_date: date | str | None = None
    due_date: date | str | None = None
    reminder_at: datetime | str | None = None
    sort_order: int = 0
    created_by: str | None = None
    completed_at: datetime | str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    assignees: list[dict] = []
    notes: list[dict] = []
    subtasks: list[dict] = []
