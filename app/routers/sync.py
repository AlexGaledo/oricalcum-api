import time
import uuid
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


def _unique_id(db: Session, model) -> str:
    prefix = model.__tablename__[0]
    while True:
        new_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        if not db.query(model).filter(model.id == new_id).first():
            return new_id


def _sync_entities(db: Session, model, project_id: str, payload: SyncPayload) -> SyncResult:
    now = int(time.time() * 1000)
    pushed = 0
    conflicts: list[ConflictInfo] = []

    for entity in payload.entities:
        data = entity.model_dump()
        existing = db.query(model).filter(model.id == entity.id).first()

        if not existing:
            data["project_id"] = project_id
            if model is Edge and "metadata" in data:
                data["metadata_"] = data.pop("metadata")
            db.add(model(**data))
            pushed += 1
        elif existing.project_id == project_id:
            if entity.version > existing.version:
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
        else:
            new_id = _unique_id(db, model)
            data["id"] = new_id
            data["project_id"] = project_id
            if model is Edge and "metadata" in data:
                data["metadata_"] = data.pop("metadata")
            db.add(model(**data))
            pushed += 1

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
