import time
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Nodespace, Node
from app.db.utils import assert_project_access
from app.dependencies import CurrentUser
from app.models.nodespace import NodespaceCreate, NodespacePatch
from app.models.project import ProjectShare
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/nodespaces", tags=["nodespaces"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_nodespaces(project_id: str, user: CurrentUser, db: Db):
    """Whole tree + the lightweight coordinate manifest, in one call.

    The manifest (`nodes: [{id, x, y}]`) is projected from the nodes table — not
    stored — so it is always correct without denormalization. Full node bodies are
    fetched separately via `/nodes?nodespace_id=` when a nodespace is opened.
    """
    assert_project_access(db, project_id, user["id"])
    spaces = db.query(Nodespace).filter(Nodespace.project_id == project_id).all()

    # Group node coordinates by nodespace in a single query.
    rows = (
        db.query(Node.id, Node.nodespace_id, Node.x, Node.y)
        .filter(Node.project_id == project_id)
        .all()
    )
    manifest: dict[str, list[dict]] = {}
    for nid, nsid, x, y in rows:
        if nsid is None:
            continue
        manifest.setdefault(nsid, []).append({"id": nid, "x": x, "y": y})

    return ok([_to_dict(s, manifest.get(s.id, [])) for s in spaces])


@router.post("")
async def create_nodespace(project_id: str, body: NodespaceCreate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    nsid = body.id or str(uuid.uuid4())
    if body.id and db.get(Nodespace, nsid):
        raise HTTPException(status_code=409, detail=f"Nodespace with id '{nsid}' already exists")
    data = body.model_dump()
    data["id"] = nsid
    space = Nodespace(project_id=project_id, **data)
    db.add(space)
    db.commit()
    db.refresh(space)
    return ok(_to_dict(space, []))


@router.get("/{nsid}")
async def get_nodespace(project_id: str, nsid: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    space = db.query(Nodespace).filter(Nodespace.id == nsid, Nodespace.project_id == project_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Nodespace not found")
    rows = db.query(Node.id, Node.x, Node.y).filter(Node.nodespace_id == nsid).all()
    nodes = [{"id": nid, "x": x, "y": y} for nid, x, y in rows]
    return ok(_to_dict(space, nodes))


@router.patch("/{nsid}")
async def patch_nodespace(project_id: str, nsid: str, body: NodespacePatch, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    space = db.query(Nodespace).filter(Nodespace.id == nsid, Nodespace.project_id == project_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Nodespace not found")
    # exclude_unset (not exclude_none) so an explicit parent_id=null moves to root.
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(space, field, value)
    db.commit()
    db.refresh(space)
    return ok(_to_dict(space, []))


@router.patch("/{nsid}/share")
async def share_nodespace(project_id: str, nsid: str, body: ProjectShare, user: CurrentUser, db: Db):
    """Toggle public visibility for a single nodespace (independent of the project)."""
    assert_project_access(db, project_id, user["id"])
    space = db.query(Nodespace).filter(Nodespace.id == nsid, Nodespace.project_id == project_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Nodespace not found")
    space.is_public = body.is_public
    space.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(space)
    return ok(_to_dict(space, []))


@router.delete("/{nsid}")
async def delete_nodespace(project_id: str, nsid: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    space = db.query(Nodespace).filter(Nodespace.id == nsid, Nodespace.project_id == project_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Nodespace not found")
    db.delete(space)  # children + nodes/edges cascade via FK ondelete=CASCADE
    db.commit()
    return ok({"deleted": nsid})


def _to_dict(s: Nodespace, nodes: list[dict]) -> dict:
    return {
        "id": s.id,
        "project_id": s.project_id,
        "parent_id": s.parent_id,
        "kind": s.kind,
        "name": s.name,
        "expanded": s.expanded,
        "sort": s.sort,
        "is_public": s.is_public,
        "nodes": nodes,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }
