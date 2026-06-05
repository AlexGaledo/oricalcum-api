import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Node
from app.db.utils import assert_project_access
from app.dependencies import CurrentUser
from app.models.node import NodeCreate, NodeUpdate, NodePatch
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/nodes", tags=["nodes"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_nodes(project_id: str, user: CurrentUser, db: Db, nodespace_id: str | None = None):
    assert_project_access(db, project_id, user["id"])
    q = db.query(Node).filter(Node.project_id == project_id)
    if nodespace_id is not None:
        q = q.filter(Node.nodespace_id == nodespace_id)
    return ok([_to_dict(n) for n in q.all()])


@router.post("")
async def create_node(project_id: str, body: NodeCreate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    node_id = body.id or str(uuid.uuid4())
    if body.id:
        existing = db.query(Node).filter(Node.id == node_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Node with id '{node_id}' already exists")
    data = body.model_dump()
    data["id"] = node_id
    node = Node(project_id=project_id, **data)
    db.add(node)
    db.commit()
    db.refresh(node)
    return ok(_to_dict(node))


@router.get("/{node_id}")
async def get_node(project_id: str, node_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    node = db.query(Node).filter(Node.id == node_id, Node.project_id == project_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return ok(_to_dict(node))


@router.put("/{node_id}")
async def update_node(project_id: str, node_id: str, body: NodeUpdate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    node = db.query(Node).filter(Node.id == node_id, Node.project_id == project_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    for field, value in body.model_dump().items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return ok(_to_dict(node))


@router.patch("/{node_id}")
async def patch_node(project_id: str, node_id: str, body: NodePatch, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    node = db.query(Node).filter(Node.id == node_id, Node.project_id == project_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return ok(_to_dict(node))


@router.delete("/{node_id}")
async def delete_node(project_id: str, node_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    node = db.query(Node).filter(Node.id == node_id, Node.project_id == project_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return ok({"deleted": node_id})


def _to_dict(n: Node) -> dict:
    return {
        "id": n.id,
        "project_id": n.project_id,
        "nodespace_id": n.nodespace_id,
        "x": n.x, "y": n.y, "w": n.w, "h": n.h,
        "base_w": n.base_w, "base_h": n.base_h,
        "shape": n.shape,
        "title": n.title,
        "body": n.body,
        "color": n.color,
        "opacity": n.opacity,
        "tags": n.tags or [],
        "status": n.status,
        "version": n.version,
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }
