from pydantic import BaseModel


class CalendarEventBase(BaseModel):
    title: str
    start: int
    end: int
    all_day: bool = False
    description: str | None = None
    color: str | None = None
    url: str | None = None


class CalendarEventCreate(CalendarEventBase):
    id: str | None = None
    created_at: int
    updated_at: int


class CalendarEventUpdate(CalendarEventBase):
    updated_at: int


class CalendarEventPatch(BaseModel):
    title: str | None = None
    start: int | None = None
    end: int | None = None
    all_day: bool | None = None
    description: str | None = None
    color: str | None = None
    url: str | None = None
    updated_at: int | None = None


class CalendarEventModel(CalendarEventCreate):
    id: str
    project_id: str
