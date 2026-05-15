from fastapi import APIRouter, HTTPException
from app.dependencies import CurrentUser
from app.database import supabase
from app.models.node import NodeCreate, NodeUpdate, NodePatch
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/nodes", tags=["nodes"])


def _assert_project_access(project_id: str, user_id: str):
    res = supabase.table("projects").select("owner_id, collaborators").eq("id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Project not found")
    p = res.data
    if p["owner_id"] != user_id and user_id not in p.get("collaborators", []):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
async def list_nodes(project_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("nodes").select("*").eq("project_id", project_id).execute()
    return ok(res.data)


@router.post("")
async def create_node(project_id: str, body: NodeCreate, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    record = body.model_dump()
    record["project_id"] = project_id
    res = supabase.table("nodes").insert(record).execute()
    return ok(res.data[0] if res.data else record)


@router.get("/{node_id}")
async def get_node(project_id: str, node_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("nodes").select("*").eq("id", node_id).eq("project_id", project_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Node not found")
    return ok(res.data)


@router.put("/{node_id}")
async def update_node(project_id: str, node_id: str, body: NodeUpdate, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    res = supabase.table("nodes").update(body.model_dump()).eq("id", node_id).eq("project_id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Node not found")
    return ok(res.data[0])


@router.patch("/{node_id}")
async def patch_node(project_id: str, node_id: str, body: NodePatch, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("nodes").update(patch).eq("id", node_id).eq("project_id", project_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Node not found")
    return ok(res.data[0])


@router.delete("/{node_id}")
async def delete_node(project_id: str, node_id: str, user: CurrentUser):
    _assert_project_access(project_id, user["id"])
    supabase.table("nodes").delete().eq("id", node_id).eq("project_id", project_id).execute()
    return ok({"deleted": node_id})
