from fastapi import APIRouter, HTTPException
from app.dependencies import CurrentUser
from app.database import supabase
from app.models.edge import EdgeCreate, EdgeUpdate, EdgePatch
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/edges", tags=["edges"])


def _assert_project_access(project_id: str, user_id: str):
    res = supabase.table("projects").select("owner_id, collaborators").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    p = res.data
    if p["owner_id"] != user_id and user_id not in p.get("collaborators", []):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
async def list_edges(project_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("edges").select("*").eq("project_id", project_id).execute()
    return ok(res.data)


@router.post("")
async def create_edge(project_id: str, body: EdgeCreate, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    record = body.model_dump()
    record["project_id"] = project_id
    res = supabase.table("edges").insert(record).execute()
    return ok(res.data[0] if res.data else record)


@router.get("/{edge_id}")
async def get_edge(project_id: str, edge_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("edges").select("*").eq("id", edge_id).eq("project_id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Edge not found")
    return ok(res.data)


@router.put("/{edge_id}")
async def update_edge(project_id: str, edge_id: str, body: EdgeUpdate, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("edges").update(body.model_dump()).eq("id", edge_id).eq("project_id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Edge not found")
    return ok(res.data[0])


@router.patch("/{edge_id}")
async def patch_edge(project_id: str, edge_id: str, body: EdgePatch, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("edges").update(patch).eq("id", edge_id).eq("project_id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Edge not found")
    return ok(res.data[0])


@router.delete("/{edge_id}")
async def delete_edge(project_id: str, edge_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    supabase.table("edges").delete().eq("id", edge_id).eq("project_id", project_id).execute()
    return ok({"deleted": edge_id})
