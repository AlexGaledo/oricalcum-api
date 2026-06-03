from typing import Any, Literal
from pydantic import BaseModel


Port = Literal["top", "right", "bottom", "left"]
AnimationStyle = Literal["flow", "pulse", "orbit"]


class EdgeBase(BaseModel):
    from_node: str
    to_node: str
    from_port: Port = "right"
    to_port: Port = "left"
    animation_style: AnimationStyle | None = None
    label: str | None = None
    metadata: dict[str, Any] = {}


class EdgeCreate(EdgeBase):
    id: str | None = None
    version: int = 1


class EdgeUpdate(EdgeBase):
    version: int


class EdgePatch(BaseModel):
    from_node: str | None = None
    to_node: str | None = None
    from_port: Port | None = None
    to_port: Port | None = None
    animation_style: AnimationStyle | None = None
    label: str | None = None
    metadata: dict[str, Any] | None = None
    version: int | None = None


class EdgeModel(EdgeCreate):
    id: str
    project_id: str
