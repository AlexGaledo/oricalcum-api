import time
from fastapi import APIRouter, HTTPException
from app.dependencies import CurrentUser
from app.database import supabase
from app.models.document import DocumentUpsert
from app.schemas.response import ok

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{node_id}")
async def get_document(node_id: str, user: CurrentUser):
    res = supabase.table("documents").select("*").eq("node_id", node_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return ok(res.data)


@router.put("/{node_id}")
async def upsert_document(node_id: str, body: DocumentUpsert, user: CurrentUser):
    now = int(time.time() * 1000)
    existing = supabase.table("documents").select("node_id").eq("node_id", node_id).execute()

    if existing.data:
        res = supabase.table("documents").update({
            "content": body.content,
            "version": body.version,
            "updated_at": now,
        }).eq("node_id", node_id).execute()
    else:
        res = supabase.table("documents").insert({
            "node_id": node_id,
            "content": body.content,
            "version": body.version,
            "created_at": now,
            "updated_at": now,
        }).execute()

    return ok(res.data[0] if res.data else None)


@router.delete("/{node_id}")
async def delete_document(node_id: str, user: CurrentUser):
    supabase.table("documents").delete().eq("node_id", node_id).execute()
    return ok({"deleted": node_id})
