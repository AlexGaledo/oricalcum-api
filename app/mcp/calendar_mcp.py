"""MCP tools for the workspace calendar.

Writes to the internal `calendar_events` table (mirrors
`app/routers/calendar_events.py`), which the app's calendar widget renders. Times
are unix epoch milliseconds, matching the rest of the API.
"""

import time
import uuid

from app.db.models import CalendarEvent
from app.mcp.context import scoped_session
from app.mcp.oricalcum_mcp import mcp
from app.routers.calendar_events import _to_dict as event_to_dict


def _now_ms() -> int:
    return int(time.time() * 1000)


@mcp.tool
def list_meetings() -> list[dict]:
    """List all calendar meetings/events in the current workspace."""
    with scoped_session() as s:
        events = (
            s.db.query(CalendarEvent)
            .filter(CalendarEvent.project_id == s.project_id)
            .all()
        )
        return [event_to_dict(e) for e in events]


@mcp.tool
def create_meeting(
    title: str,
    start: int,
    end: int,
    description: str | None = None,
    all_day: bool = False,
    color: str | None = None,
) -> dict:
    """Schedule a meeting/event in the current workspace's calendar.

    `start` and `end` are unix epoch timestamps in milliseconds. Resolve relative
    dates the user gives ("tomorrow 3pm") to absolute ms before calling. Returns
    the created event.
    """
    if end < start:
        raise ValueError("Meeting end must be at or after start")
    with scoped_session() as s:
        now = _now_ms()
        event = CalendarEvent(
            id=str(uuid.uuid4()),
            project_id=s.project_id,
            title=title,
            start=start,
            end=end,
            all_day=all_day,
            description=description,
            color=color,
            created_at=now,
            updated_at=now,
        )
        s.db.add(event)
        s.db.commit()
        s.db.refresh(event)
        return event_to_dict(event)
