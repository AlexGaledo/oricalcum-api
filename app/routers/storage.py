"""Per-workspace S3 file storage.

Every workspace is sandboxed under the `workspaces/{project_id}/` key prefix. Clients
send only relative paths; this router prepends the sandbox prefix and rejects any path
that tries to escape it. Bytes move browser<->S3 directly via presigned URLs; only
metadata operations (list, delete, copy, folder markers) pass through the API.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Project
from app.dependencies import CurrentUser
from app.models.storage import PresignUploadBody, CreateFolderBody, MoveBody
from app.schemas.response import ok
from app import s3_client

router = APIRouter(prefix="/projects/{project_id}/storage", tags=["storage"])

Db = Annotated[Session, Depends(get_db)]

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Allowlisted MIME types (sane defaults: images, docs, text, archives).
ALLOWED_CONTENT_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "image/avif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain", "text/markdown", "text/csv", "application/json",
    "application/zip", "application/x-zip-compressed", "application/gzip",
    "application/x-tar", "application/octet-stream",
}


def _assert_access(db: Session, project_id: str, user_id: str) -> Project:
    """Storage is collaborative: the owner OR any collaborator may access it."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user_id and user_id not in (project.collaborators or []):
        raise HTTPException(status_code=403, detail="Forbidden")
    return project


def _safe_relative(path: str) -> str:
    """Normalize a client path and reject traversal/absolute escapes."""
    rel = (path or "").strip().lstrip("/")
    if ".." in rel.split("/") or rel.startswith("/") or "\\" in rel:
        raise HTTPException(status_code=400, detail="Invalid path")
    return rel


def _key(project_id: str, rel: str) -> str:
    return f"workspaces/{project_id}/{rel}"


def _root(project_id: str) -> str:
    return f"workspaces/{project_id}/"


def _strip_root(project_id: str, key: str) -> str:
    return key[len(_root(project_id)):]


@router.get("")
async def list_dir(
    project_id: str,
    user: CurrentUser,
    db: Db,
    prefix: str = Query("", description="Relative folder path; empty = workspace root"),
):
    _assert_access(db, project_id, user["id"])
    rel = _safe_relative(prefix)
    if rel and not rel.endswith("/"):
        rel += "/"
    listing = s3_client.list_prefix(_key(project_id, rel))
    folders = [
        {"name": _strip_root(project_id, f).rstrip("/").split("/")[-1], "path": _strip_root(project_id, f)}
        for f in listing["folders"]
    ]
    files = [
        {
            "name": _strip_root(project_id, f["key"]).split("/")[-1],
            "path": _strip_root(project_id, f["key"]),
            "size": f["size"],
            "last_modified": f["last_modified"],
        }
        for f in listing["files"]
    ]
    return ok({"prefix": rel, "folders": folders, "files": files})


@router.post("/presign-upload")
async def presign_upload(project_id: str, body: PresignUploadBody, user: CurrentUser, db: Db):
    _assert_access(db, project_id, user["id"])
    if body.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported type: {body.content_type}")
    rel = _safe_relative(body.path)
    if not rel or rel.endswith("/"):
        raise HTTPException(status_code=400, detail="A file name is required")
    key = _key(project_id, rel)
    url = s3_client.presign_put(key, body.content_type)
    return ok({"url": url, "path": rel})


@router.get("/presign-download")
async def presign_download(
    project_id: str,
    user: CurrentUser,
    db: Db,
    path: str = Query(...),
    download: bool = Query(False),
):
    _assert_access(db, project_id, user["id"])
    rel = _safe_relative(path)
    name = rel.split("/")[-1] if download else None
    url = s3_client.presign_get(_key(project_id, rel), download_name=name)
    return ok({"url": url})


@router.delete("")
async def delete_item(
    project_id: str,
    user: CurrentUser,
    db: Db,
    path: str = Query(...),
):
    _assert_access(db, project_id, user["id"])
    rel = _safe_relative(path)
    if not rel:
        raise HTTPException(status_code=400, detail="Path is required")
    if rel.endswith("/"):
        count = s3_client.delete_prefix(_key(project_id, rel))
        return ok({"deleted": rel, "objects": count})
    s3_client.delete_key(_key(project_id, rel))
    return ok({"deleted": rel})


@router.post("/folder")
async def create_folder(project_id: str, body: CreateFolderBody, user: CurrentUser, db: Db):
    _assert_access(db, project_id, user["id"])
    rel = _safe_relative(body.path)
    if not rel:
        raise HTTPException(status_code=400, detail="Folder name is required")
    if not rel.endswith("/"):
        rel += "/"
    s3_client.put_empty(_key(project_id, rel))
    return ok({"path": rel})


@router.get("/media")
async def media_redirect(
    project_id: str,
    path: str = Query(...),
):
    """Stable, auth-free redirect to a freshly presigned GET URL.

    Used as the durable `src` for media embedded in node bodies / avatars, which
    cannot send an Authorization header. The bucket stays private; access relies on
    the unguessable uuid-prefixed keys these uploads use. Re-presigned on every load
    so the link never expires from the browser's perspective.
    """
    rel = _safe_relative(path)
    url = s3_client.presign_get(_key(project_id, rel))
    return RedirectResponse(url, status_code=307)


@router.post("/move")
async def move_item(project_id: str, body: MoveBody, user: CurrentUser, db: Db):
    _assert_access(db, project_id, user["id"])
    src = _safe_relative(body.from_path)
    dst = _safe_relative(body.to_path)
    if not src or not dst:
        raise HTTPException(status_code=400, detail="from_path and to_path are required")
    src_is_folder = src.endswith("/")
    dst_is_folder = dst.endswith("/")
    if src_is_folder != dst_is_folder:
        raise HTTPException(status_code=400, detail="Cannot move a file to a folder path or vice versa")

    src_key = _key(project_id, src)
    dst_key = _key(project_id, dst)
    if src_is_folder:
        s3_client.copy_prefix(src_key, dst_key)
        s3_client.delete_prefix(src_key)
    else:
        s3_client.copy_key(src_key, dst_key)
        s3_client.delete_key(src_key)
    return ok({"from": src, "to": dst})
