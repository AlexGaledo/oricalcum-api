import time
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Project
from app.dependencies import CurrentUser
from app.models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectPatch,
    ProjectShare,
    CollaboratorAdd,
)
from app.schemas.response import ok
from app.auth_client import auth_client

router = APIRouter(prefix="/projects", tags=["projects"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_projects(user: CurrentUser, db: Db):
    # Show workspaces the user is included in: owned OR a collaborator on.
    uid = user["id"]
    projects = (
        db.query(Project)
        .filter(or_(Project.owner_id == uid, Project.collaborators.any(uid)))
        .all()
    )
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


@router.patch("/{project_id}")
async def patch_project(project_id: str, body: ProjectPatch, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = body.model_dump(exclude_none=True)
    if "camera" in data:
        project.camera = data.pop("camera")
    for field, value in data.items():
        setattr(project, field, value)
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


@router.get("/{project_id}/collaborators")
async def list_collaborators(project_id: str, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    collaborators = project.collaborators or []
    if project.owner_id != user["id"] and user["id"] not in collaborators:
        raise HTTPException(status_code=403, detail="Forbidden")

    emails = _resolve_emails([project.owner_id, *collaborators])
    result = [{"user_id": project.owner_id, "email": emails.get(project.owner_id), "is_owner": True}]
    for cid in collaborators:
        result.append({"user_id": cid, "email": emails.get(cid), "is_owner": False})
    return ok(result)


@router.post("/{project_id}/collaborators")
async def add_collaborator(project_id: str, body: CollaboratorAdd, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.user_id:
        target_id = body.user_id
    elif body.email:
        target_id = _resolve_id_by_email(body.email)
        if not target_id:
            raise HTTPException(status_code=404, detail=f"No user found for '{body.email}'")
    else:
        raise HTTPException(status_code=422, detail="user_id or email required")

    if target_id == project.owner_id:
        raise HTTPException(status_code=409, detail="Owner is already on the project")

    collaborators = list(project.collaborators or [])
    if target_id not in collaborators:
        collaborators.append(target_id)
        project.collaborators = collaborators
        project.updated_at = int(time.time() * 1000)
        db.commit()
        db.refresh(project)
    return ok(_to_dict(project))


@router.delete("/{project_id}/collaborators/{collaborator_id}")
async def remove_collaborator(project_id: str, collaborator_id: str, user: CurrentUser, db: Db):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    collaborators = [c for c in (project.collaborators or []) if c != collaborator_id]
    project.collaborators = collaborators
    project.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(project)
    return ok(_to_dict(project))


def _resolve_id_by_email(email: str) -> str | None:
    target = email.strip().lower()
    try:
        users = auth_client.auth.admin.list_users()
    except Exception:
        return None
    for u in users:
        if (getattr(u, "email", None) or "").lower() == target:
            return u.id
    return None


def _resolve_emails(user_ids: list[str]) -> dict[str, str]:
    wanted = set(user_ids)
    mapping: dict[str, str] = {}
    try:
        users = auth_client.auth.admin.list_users()
    except Exception:
        return mapping
    for u in users:
        if u.id in wanted and getattr(u, "email", None):
            mapping[u.id] = u.email
    return mapping


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
