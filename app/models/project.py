from typing import Any
from pydantic import BaseModel


class Camera(BaseModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


class ProjectBase(BaseModel):
    name: str
    description: str = ""
    collaborators: list[str] = []
    settings: dict[str, Any] = {}
    camera: Camera = Camera()


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectModel(ProjectBase):
    id: str
    owner_id: str
    created_at: int
    updated_at: int
