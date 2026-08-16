import uuid

from fastapi import APIRouter, HTTPException

from app.database.db import events_db, get_next_id
from app.models.event import EventCreate, EventInternal, EventPublic

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventPublic])
def list_events():
    return list(events_db.values())


@router.post("/", response_model=EventPublic)
def create_event(event: EventCreate):
    event_id = get_next_id()
    internal_event = EventInternal(
        id=event_id,
        name=event.name,
        date=event.date,
        location=event.location,
        organizer_id=42,
        audit_token=str(uuid.uuid4()),
    )
    events_db[event_id] = internal_event.model_dump()
    return internal_event


@router.post("/insecure-demo")
def create_event_insecure(event: EventCreate):
    event_id = get_next_id()
    internal_event = EventInternal(
        id=event_id,
        name=event.name,
        date=event.date,
        location=event.location,
        organizer_id=42,
        audit_token=str(uuid.uuid4()),
    )
    events_db[event_id] = internal_event.model_dump()
    return internal_event


@router.get("/{event_id}", response_model=EventPublic)
def get_event(event_id: int):
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="Event not found")
    return events_db[event_id]
