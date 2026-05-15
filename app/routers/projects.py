import time
import uuid
from fastapi import APIRouter, HTTPException
from app.dependencies import CurrentUser
from app.database import supabase
from app.models.project import ProjectCreate, ProjectUpdate
from app.schemas.response import ok, err

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(user: CurrentUser):
    res = supabase.table("projects").select("*").eq("owner_id", user["id"]).execute()
    return ok(res.data)


@router.post("")
async def create_project(body: ProjectCreate, user: CurrentUser):
    now = int(time.time() * 1000)
    record = {
        "id": str(uuid.uuid4()),
        "owner_id": user["id"],
        "name": body.name,
        "description": body.description,
        "collaborators": body.collaborators,
        "settings": body.settings,
        "camera": body.camera.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    res = supabase.table("projects").insert(record).execute()
    return ok(res.data[0] if res.data else record)


@router.get("/{project_id}")
async def get_project(project_id: str, user: CurrentUser):
    res = supabase.table("projects").select("*").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = res.data
    if project["owner_id"] != user["id"] and user["id"] not in project.get("collaborators", []):
        raise HTTPException(status_code=403, detail="Forbidden")
    return ok(project)


@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, user: CurrentUser):
    now = int(time.time() * 1000)
    res = supabase.table("projects").select("owner_id, collaborators").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    if res.data["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    updated = supabase.table("projects").update({
        "name": body.name,
        "description": body.description,
        "collaborators": body.collaborators,
        "settings": body.settings,
        "camera": body.camera.model_dump(),
        "updated_at": now,
    }).eq("id", project_id).execute()
    return ok(updated.data[0] if updated.data else None)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: CurrentUser):
    res = supabase.table("projects").select("owner_id").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    if res.data["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    supabase.table("projects").delete().eq("id", project_id).execute()
    return ok({"deleted": project_id})
