import time
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Node, Edge
from app.dependencies import CurrentUser
from app.models.sync import SyncPayload, SyncResult, ConflictInfo
from app.schemas.response import ok

router = APIRouter(prefix="/sync", tags=["sync"])

Db = Annotated[Session, Depends(get_db)]


def _sync_entities(db: Session, model, project_id: str, payload: SyncPayload) -> SyncResult:
    now = int(time.time() * 1000)
    pushed = 0
    conflicts: list[ConflictInfo] = []

    for entity in payload.entities:
        data = entity.model_dump()
        existing = db.query(model).filter(model.id == entity.id, model.project_id == project_id).first()

        if not existing:
            data["project_id"] = project_id
            if model is Edge and "metadata" in data:
                data["metadata_"] = data.pop("metadata")
            db.add(model(**data))
            pushed += 1
        elif entity.version > existing.version:
            if model is Edge and "metadata" in data:
                data["metadata_"] = data.pop("metadata")
            for field, value in data.items():
                setattr(existing, field, value)
            pushed += 1
        elif entity.version < existing.version:
            conflicts.append(ConflictInfo(
                id=entity.id,
                local_version=entity.version,
                server_version=existing.version,
            ))

    db.commit()

    pulled_rows = (
        db.query(model)
        .filter(model.project_id == project_id, model.updated_at > payload.last_synced_at)
        .all()
        if hasattr(model, "updated_at") and payload.last_synced_at
        else []
    )

    return SyncResult(
        pushed=pushed,
        pulled=len(pulled_rows),
        conflicts=conflicts,
        server_time=now,
        pulled_entities=[row.__dict__ for row in pulled_rows],
    )


@router.post("/nodes")
async def sync_nodes(payload: SyncPayload, user: CurrentUser, db: Db):
    result = _sync_entities(db, Node, payload.project_id, payload)
    return ok(result.model_dump(exclude={"pulled_entities"}))


@router.post("/edges")
async def sync_edges(payload: SyncPayload, user: CurrentUser, db: Db):
    result = _sync_entities(db, Edge, payload.project_id, payload)
    return ok(result.model_dump(exclude={"pulled_entities"}))
