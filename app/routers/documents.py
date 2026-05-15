import time
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Document
from app.dependencies import CurrentUser
from app.models.document import DocumentUpsert
from app.schemas.response import ok

router = APIRouter(prefix="/documents", tags=["documents"])

Db = Annotated[Session, Depends(get_db)]


@router.get("/{node_id}")
async def get_document(node_id: str, user: CurrentUser, db: Db):
    doc = db.get(Document, node_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return ok(_to_dict(doc))


@router.put("/{node_id}")
async def upsert_document(node_id: str, body: DocumentUpsert, user: CurrentUser, db: Db):
    now = int(time.time() * 1000)
    doc = db.get(Document, node_id)
    if doc:
        doc.content = body.content
        doc.version = body.version
        doc.updated_at = now
    else:
        doc = Document(
            node_id=node_id,
            content=body.content,
            version=body.version,
            created_at=now,
            updated_at=now,
        )
        db.add(doc)
    db.commit()
    db.refresh(doc)
    return ok(_to_dict(doc))


@router.delete("/{node_id}")
async def delete_document(node_id: str, user: CurrentUser, db: Db):
    doc = db.get(Document, node_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return ok({"deleted": node_id})


def _to_dict(d: Document) -> dict:
    return {
        "node_id": d.node_id,
        "content": d.content,
        "version": d.version,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }
