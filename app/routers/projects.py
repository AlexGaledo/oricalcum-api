import time
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Project
from app.dependencies import CurrentUser
from app.models.project import ProjectCreate, ProjectUpdate, ProjectShare
from app.schemas.response import ok

router = APIRouter(prefix="/projects", tags=["projects"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_projects(user: CurrentUser, db: Db):
    projects = db.query(Project).filter(Project.owner_id == user["id"]).all()
    return ok([_to_dict(p) for p in projects])


@router.post("")
async def create_project(body: ProjectCreate, user: CurrentUser, db: Db):
    project_id = body.id or str(uuid.uuid4())

    # idempotent — return existing project if already created
    existing = db.get(Project, project_id)
    if existing:
        if existing.owner_id != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return ok(_to_dict(existing))

    now = int(time.time() * 1000)
    project = Project(
        id=project_id,
        owner_id=user["id"],
        name=body.name,
        description=body.description,
        collaborators=body.collaborators,
        settings=body.settings,
        camera=body.camera.model_dump(),
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ok(_to_dict(project))


@router.get("/{project_id}")
async def get_project(project_id: str, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    collaborators = project.collaborators or []
    if project.owner_id != user["id"] and user["id"] not in collaborators:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ok(_to_dict(project))


@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    project.name = body.name
    project.description = body.description
    project.collaborators = body.collaborators
    project.settings = body.settings
    project.camera = body.camera.model_dump()
    project.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(project)
    return ok(_to_dict(project))


@router.patch("/{project_id}/share")
async def share_project(project_id: str, body: ProjectShare, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    project.is_public = body.is_public
    project.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(project)
    return ok(_to_dict(project))


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(project)
    db.commit()
    return ok({"deleted": project_id})


def _to_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "owner_id": p.owner_id,
        "collaborators": p.collaborators or [],
        "settings": p.settings or {},
        "camera": p.camera or {"x": 0, "y": 0, "zoom": 1},
        "is_public": p.is_public,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
