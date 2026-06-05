from typing import Literal
from pydantic import BaseModel


NodespaceKind = Literal["file", "folder"]


class NodespaceCreate(BaseModel):
    id: str | None = None
    parent_id: str | None = None
    kind: NodespaceKind = "file"
    name: str = "untitled"
    expanded: bool = True
    sort: float = 0
    created_at: int
    updated_at: int


class NodespacePatch(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    kind: NodespaceKind | None = None
    expanded: bool | None = None
    sort: float | None = None
    updated_at: int | None = None


class NodespaceModel(NodespaceCreate):
    id: str
    project_id: str
