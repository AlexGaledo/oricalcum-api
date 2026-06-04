import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import CalendarEvent
from app.db.utils import assert_project_access
from app.dependencies import CurrentUser
from app.models.calendar_event import CalendarEventCreate, CalendarEventUpdate, CalendarEventPatch
from app.schemas.response import ok

router = APIRouter(prefix="/projects/{project_id}/calendar-events", tags=["calendar_events"])

Db = Annotated[Session, Depends(get_db)]


@router.get("")
async def list_calendar_events(project_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    events = db.query(CalendarEvent).filter(CalendarEvent.project_id == project_id).all()
    return ok([_to_dict(e) for e in events])


@router.post("")
async def create_calendar_event(project_id: str, body: CalendarEventCreate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    event_id = body.id or str(uuid.uuid4())
    if body.id:
        existing = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"CalendarEvent with id '{event_id}' already exists")
    data = body.model_dump()
    data["id"] = event_id
    event = CalendarEvent(project_id=project_id, **data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return ok(_to_dict(event))


@router.get("/{event_id}")
async def get_calendar_event(project_id: str, event_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="CalendarEvent not found")
    return ok(_to_dict(event))


@router.put("/{event_id}")
async def update_calendar_event(project_id: str, event_id: str, body: CalendarEventUpdate, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="CalendarEvent not found")
    for field, value in body.model_dump().items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return ok(_to_dict(event))


@router.patch("/{event_id}")
async def patch_calendar_event(project_id: str, event_id: str, body: CalendarEventPatch, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="CalendarEvent not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return ok(_to_dict(event))


@router.delete("/{event_id}")
async def delete_calendar_event(project_id: str, event_id: str, user: CurrentUser, db: Db):
    assert_project_access(db, project_id, user["id"])
    event = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.project_id == project_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="CalendarEvent not found")
    db.delete(event)
    db.commit()
    return ok({"deleted": event_id})


def _to_dict(e: CalendarEvent) -> dict:
    return {
        "id": e.id,
        "project_id": e.project_id,
        "title": e.title,
        "start": e.start,
        "end": e.end,
        "all_day": e.all_day,
        "description": e.description,
        "color": e.color,
        "url": e.url,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }
