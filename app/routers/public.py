from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Project, Node, Edge
from app.schemas.response import ok

router = APIRouter(prefix="/public", tags=["public"])

Db = Annotated[Session, Depends(get_db)]


def _get_public_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_public:
        raise HTTPException(status_code=404, detail="Not found")
    return project


@router.get("/projects/{project_id}")
async def get_public_project(project_id: str, db: Db):
    project = _get_public_project(project_id, db)
    return ok(_project_dict(project))


@router.get("/projects/{project_id}/nodes")
async def get_public_nodes(project_id: str, db: Db):
    _get_public_project(project_id, db)
    nodes = db.query(Node).filter(Node.project_id == project_id).all()
    return ok([_node_dict(n) for n in nodes])


@router.get("/projects/{project_id}/edges")
async def get_public_edges(project_id: str, db: Db):
    _get_public_project(project_id, db)
    edges = db.query(Edge).filter(Edge.project_id == project_id).all()
    return ok([_edge_dict(e) for e in edges])


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "camera": p.camera or {"x": 0, "y": 0, "zoom": 1},
    }


def _node_dict(n: Node) -> dict:
    return {
        "id": n.id,
        "x": n.x, "y": n.y, "w": n.w, "h": n.h,
        "base_w": n.base_w, "base_h": n.base_h,
        "shape": n.shape,
        "title": n.title,
        "body": n.body,
        "color": n.color,
        "opacity": n.opacity,
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }


def _edge_dict(e: Edge) -> dict:
    return {
        "id": e.id,
        "from_node": e.from_node,
        "to_node": e.to_node,
        "from_port": e.from_port,
        "to_port": e.to_port,
    }
