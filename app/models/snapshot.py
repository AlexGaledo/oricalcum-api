from typing import Any
from pydantic import BaseModel
from app.models.node import NodeCreate
from app.models.edge import EdgeCreate
from app.models.document import DocumentUpsert
from app.models.project import Camera


class SnapshotData(BaseModel):
    nodes: list[NodeCreate] = []
    edges: list[EdgeCreate] = []
    documents: list[DocumentUpsert] = []
    camera: Camera = Camera()


class SnapshotCreate(BaseModel):
    name: str = ""
    data: SnapshotData


class SnapshotListItem(BaseModel):
    id: str
    project_id: str
    created_by: str
    name: str
    created_at: int


class SnapshotModel(SnapshotListItem):
    data: dict[str, Any]
