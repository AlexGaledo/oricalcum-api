from typing import Literal
from pydantic import BaseModel


NodeShape = Literal["rectangle", "circle", "hexagon", "diamond", "cloud", "document"]
NodeStatus = Literal["active", "archived", "deleted"]


class NodeBase(BaseModel):
    x: float
    y: float
    w: float
    h: float
    base_w: float
    base_h: float
    shape: NodeShape = "rectangle"
    title: str = ""
    body: str = ""
    color: str | None = None
    opacity: float | None = None
    tags: list[str] = []
    status: NodeStatus = "active"


class NodeCreate(NodeBase):
    id: str | None = None
    version: int = 1
    created_at: int
    updated_at: int


class NodeUpdate(NodeBase):
    version: int
    updated_at: int


class NodePatch(BaseModel):
    x: float | None = None
    y: float | None = None
    w: float | None = None
    h: float | None = None
    base_w: float | None = None
    base_h: float | None = None
    shape: NodeShape | None = None
    title: str | None = None
    body: str | None = None
    color: str | None = None
    opacity: float | None = None
    tags: list[str] | None = None
    status: NodeStatus | None = None
    version: int | None = None
    updated_at: int | None = None


class NodeModel(NodeCreate):
    id: str
    project_id: str
