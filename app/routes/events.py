import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user, require_event_owner, require_scope
from app.database.db import events_db, get_next_id
from app.models.event import EventCreate, EventInternal, EventPublic, EventUpdate
from app.models.user import UserPublic

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventPublic])
def list_events():
    return list(events_db.values())


@router.post("/", response_model=EventPublic)
def create_event(
    event: EventCreate, current_user: UserPublic = Depends(get_current_user)
):
    event_id = get_next_id()
    internal_event = EventInternal(
        id=event_id,
        name=event.name,
        date=event.date,
        location=event.location,
        organizer_id=current_user.username,
        audit_token=str(uuid.uuid4()),
    )
    events_db[event_id] = internal_event.model_dump()
    return internal_event


@router.get("/partner-feed", response_model=list[EventPublic])
def partner_feed(_payload: dict = Depends(require_scope("events:read"))):
    return list(events_db.values())


@router.get("/{event_id}", response_model=EventPublic)
def get_event(event_id: int):
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="Event not found")
    return events_db[event_id]


@router.put("/{event_id}", response_model=EventPublic)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: UserPublic = Depends(require_event_owner),
):
    stored_event = events_db[event_id]
    update_data = event_update.model_dump(exclude_unset=True)
    stored_event.update(update_data)
    events_db[event_id] = stored_event
    return stored_event