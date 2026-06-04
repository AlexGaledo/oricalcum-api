import json
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.agent import stream_agent_reply
from app.db.models import ChatMessage
from app.db.session import SessionLocal, get_db
from app.db.utils import assert_project_access
from app.dependencies import authenticate_token, bearer_scheme
from app.models.chat import ChatRequest

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["chat"])

Db = Annotated[Session, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]

# How many prior turns to feed the model as memory.
_HISTORY_LIMIT = 20


def _now_ms() -> int:
    return int(time.time() * 1000)


def _save_message(db: Session, project_id: str, user_id: str, role: str, content: str) -> None:
    db.add(
        ChatMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=user_id,
            role=role,
            content=content,
            created_at=_now_ms(),
        )
    )
    db.commit()


@router.post("")
async def chat(project_id: str, body: ChatRequest, credentials: Credentials, db: Db):
    """Converse with the workspace assistant. Streams the reply as SSE.

    Events: `data: {"delta": "..."}` token chunks, `event: error` on failure,
    and a terminating `event: done`.
    """
    jwt = credentials.credentials
    user = authenticate_token(jwt)
    assert_project_access(db, project_id, user["id"])

    # Load prior turns (oldest first) as memory, then persist this user turn.
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project_id, ChatMessage.user_id == user["id"])
        .order_by(ChatMessage.created_at.desc())
        .limit(_HISTORY_LIMIT)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(rows)]
    _save_message(db, project_id, user["id"], "user", body.message)

    async def event_stream():
        parts: list[str] = []
        try:
            async for token in stream_agent_reply(
                jwt=jwt,
                project_id=project_id,
                history=history,
                user_message=body.message,
            ):
                parts.append(token)
                yield f"data: {json.dumps({'delta': token})}\n\n"
        except Exception as exc:  # surface to client instead of dropping the stream
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
        finally:
            reply = "".join(parts).strip()
            if reply:
                # Fresh session: the request `db` may be mid-teardown by now.
                persist_db = SessionLocal()
                try:
                    _save_message(persist_db, project_id, user["id"], "assistant", reply)
                finally:
                    persist_db.close()
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
