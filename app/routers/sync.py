import time
from fastapi import APIRouter
from app.dependencies import CurrentUser
from app.database import supabase
from app.models.sync import SyncPayload, SyncResult, ConflictInfo
from app.schemas.response import ok

router = APIRouter(prefix="/sync", tags=["sync"])


def _sync_entities(table: str, project_id: str, payload: SyncPayload) -> SyncResult:
    now = int(time.time() * 1000)
    pushed = 0
    conflicts: list[ConflictInfo] = []

    for entity in payload.entities:
        data = entity.model_dump()
        existing = supabase.table(table).select("id, version").eq("id", entity.id).eq("project_id", project_id).execute()

        if not existing.data:
            data["project_id"] = project_id
            supabase.table(table).insert(data).execute()
            pushed += 1
        else:
            server_version = existing.data[0]["version"]
            if entity.version > server_version:
                supabase.table(table).update(data).eq("id", entity.id).execute()
                pushed += 1
            elif entity.version < server_version:
                conflicts.append(ConflictInfo(
                    id=entity.id,
                    local_version=entity.version,
                    server_version=server_version,
                ))

    pulled_res = supabase.table(table).select("*").eq("project_id", project_id).gt("updated_at", payload.last_synced_at).execute()
    pulled_entities = pulled_res.data or []

    return SyncResult(
        pushed=pushed,
        pulled=len(pulled_entities),
        conflicts=conflicts,
        server_time=now,
        pulled_entities=pulled_entities,
    )


@router.post("/nodes")
async def sync_nodes(payload: SyncPayload, user: CurrentUser):
    result = _sync_entities("nodes", payload.project_id, payload)
    return ok(result.model_dump())


@router.post("/edges")
async def sync_edges(payload: SyncPayload, user: CurrentUser):
    result = _sync_entities("edges", payload.project_id, payload)
    return ok(result.model_dump())
