import time
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Snapshot
from app.db.utils import assert_project_access
from app.dependencies import CurrentUser
from app.models.snapshot import SnapshotCreate
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/snapshots", tags=["snapshots"])

Db = Annotated[Session, Depends(get_db)]


@router.post("")
async def create_snapshot(project_id: str, body: SnapshotCreate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    now = int(time.time() * 1000)
    snapshot = Snapshot(
        id=str(uuid.uuid4()),
        project_id=project_id,
        created_by=user["id"],
        name=body.name,
        data=body.data.model_dump(),
        created_at=now,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return ok(_to_dict(snapshot, include_data=True))


@router.get("")
async def list_snapshots(project_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.project_id == project_id)
        .order_by(Snapshot.created_at.desc())
        .all()
    )
    return ok([_to_dict(s, include_data=False) for s in snapshots])


@router.get("/{snapshot_id}")
async def get_snapshot(project_id: str, snapshot_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    snapshot = db.query(Snapshot).filter(
        Snapshot.id == snapshot_id,
        Snapshot.project_id == project_id,
    ).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return ok(_to_dict(snapshot, include_data=True))


@router.delete("/{snapshot_id}")
async def delete_snapshot(project_id: str, snapshot_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    snapshot = db.query(Snapshot).filter(
        Snapshot.id == snapshot_id,
        Snapshot.project_id == project_id,
    ).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    db.delete(snapshot)
    db.commit()
    return ok({"deleted": snapshot_id})


def _to_dict(s: Snapshot, *, include_data: bool) -> dict:
    result = {
        "id": s.id,
        "project_id": s.project_id,
        "created_by": s.created_by,
        "name": s.name,
        "created_at": s.created_at,
    }
    if include_data:
        result["data"] = s.data
    return result
