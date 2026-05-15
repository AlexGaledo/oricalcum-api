from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Edge
from app.db.utils import assert_project_access
from app.dependencies import CurrentUser
from app.models.edge import EdgeCreate, EdgeUpdate, EdgePatch
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/edges", tags=["edges"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_edges(project_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    edges = db.query(Edge).filter(Edge.project_id == project_id).all()
    return ok([_to_dict(e) for e in edges])


@router.post("")
async def create_edge(project_id: str, body: EdgeCreate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    data = body.model_dump()
    edge = Edge(project_id=project_id, metadata_=data.pop("metadata", {}), **data)
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return ok(_to_dict(edge))


@router.get("/{edge_id}")
async def get_edge(project_id: str, edge_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    edge = db.query(Edge).filter(Edge.id == edge_id, Edge.project_id == project_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    return ok(_to_dict(edge))


@router.put("/{edge_id}")
async def update_edge(project_id: str, edge_id: str, body: EdgeUpdate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    edge = db.query(Edge).filter(Edge.id == edge_id, Edge.project_id == project_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    data = body.model_dump()
    edge.metadata_ = data.pop("metadata", {})
    for field, value in data.items():
        setattr(edge, field, value)
    db.commit()
    db.refresh(edge)
    return ok(_to_dict(edge))


@router.patch("/{edge_id}")
async def patch_edge(project_id: str, edge_id: str, body: EdgePatch, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    edge = db.query(Edge).filter(Edge.id == edge_id, Edge.project_id == project_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    data = body.model_dump(exclude_none=True)
    if "metadata" in data:
        edge.metadata_ = data.pop("metadata")
    for field, value in data.items():
        setattr(edge, field, value)
    db.commit()
    db.refresh(edge)
    return ok(_to_dict(edge))


@router.delete("/{edge_id}")
async def delete_edge(project_id: str, edge_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    edge = db.query(Edge).filter(Edge.id == edge_id, Edge.project_id == project_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    db.delete(edge)
    db.commit()
    return ok({"deleted": edge_id})


def _to_dict(e: Edge) -> dict:
    return {
        "id": e.id,
        "project_id": e.project_id,
        "from_node": e.from_node,
        "to_node": e.to_node,
        "from_port": e.from_port,
        "to_port": e.to_port,
        "animation_style": e.animation_style,
        "label": e.label,
        "metadata": e.metadata_ or {},
        "version": e.version,
    }
