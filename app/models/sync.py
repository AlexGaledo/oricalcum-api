from typing import Any
from pydantic import BaseModel


class SyncEntity(BaseModel):
    id: str
    version: int
    updated_at: int
    model_config = {"extra": "allow"}


class SyncPayload(BaseModel):
    project_id: str
    last_synced_at: int
    entities: list[SyncEntity]


class ConflictInfo(BaseModel):
    id: str
    local_version: int
    server_version: int


class SyncResult(BaseModel):
    pushed: int
    pulled: int
    conflicts: list[ConflictInfo]
    server_time: int
    pulled_entities: list[dict[str, Any]] = []
