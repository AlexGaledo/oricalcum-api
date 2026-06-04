import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Project, ProjectSecret
from app.dependencies import CurrentUser
from app.models.secret import SecretCreate, SecretUpdate
from app.schemas.response import ok
from app.crypto import encrypt, decrypt

router = APIRouter(prefix="/projects/{project_id}/secrets", tags=["secrets"])

Db = Annotated[Session, Depends(get_db)]


def _assert_owner(db: Session, project_id: str, user_id: str) -> Project:
    """Secrets are owner-only — collaborators cannot list, read, or mutate them."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return project


@router.get("")
async def list_secrets(project_id: str, user: CurrentUser, db: Db):
    _assert_owner(db, project_id, user["id"])
    secrets = db.query(ProjectSecret).filter(ProjectSecret.project_id == project_id).all()
    return ok([_to_meta(s) for s in secrets])


@router.post("")
async def create_secret(project_id: str, body: SecretCreate, user: CurrentUser, db: Db):
    _assert_owner(db, project_id, user["id"])
    key = body.key.strip()
    if not key:
        raise HTTPException(status_code=422, detail="key is required")

    existing = db.query(ProjectSecret).filter(
        ProjectSecret.project_id == project_id, ProjectSecret.key == key
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Secret '{key}' already exists")

    now = int(time.time() * 1000)
    secret = ProjectSecret(
        id=str(uuid.uuid4()),
        project_id=project_id,
        key=key,
        value_encrypted=encrypt(body.value),
        created_at=now,
        updated_at=now,
    )
    db.add(secret)
    db.commit()
    db.refresh(secret)
    return ok(_to_meta(secret))


@router.get("/{secret_id}/reveal")
async def reveal_secret(project_id: str, secret_id: str, user: CurrentUser, db: Db):
    _assert_owner(db, project_id, user["id"])
    secret = _get(db, project_id, secret_id)
    return ok({**_to_meta(secret), "value": decrypt(secret.value_encrypted)})


@router.patch("/{secret_id}")
async def update_secret(project_id: str, secret_id: str, body: SecretUpdate, user: CurrentUser, db: Db):
    _assert_owner(db, project_id, user["id"])
    secret = _get(db, project_id, secret_id)
    secret.value_encrypted = encrypt(body.value)
    secret.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(secret)
    return ok(_to_meta(secret))


@router.delete("/{secret_id}")
async def delete_secret(project_id: str, secret_id: str, user: CurrentUser, db: Db):
    _assert_owner(db, project_id, user["id"])
    secret = _get(db, project_id, secret_id)
    db.delete(secret)
    db.commit()
    return ok({"deleted": secret_id})


def _get(db: Session, project_id: str, secret_id: str) -> ProjectSecret:
    secret = db.query(ProjectSecret).filter(
        ProjectSecret.id == secret_id, ProjectSecret.project_id == project_id
    ).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


def _to_meta(s: ProjectSecret) -> dict:
    return {
        "id": s.id,
        "key": s.key,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }
