from typing import Optional
from pydantic import BaseModel


class PathMappingCreate(BaseModel):
    pattern: str
    source: str
    project_id: str


class OverrideCreate(BaseModel):
    source: str
    source_key: str
    employee_id: str
    project_id: Optional[str] = None
    remember: bool = False
    pattern: Optional[str] = None
