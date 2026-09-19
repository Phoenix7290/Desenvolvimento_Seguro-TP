import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.limiter import limiter
from app.auth.dependencies import get_current_user, require_event_owner, require_scope
from app.database.db import events_db, get_next_id, comments_db
from app.models.event import EventCreate, EventInternal, EventPublic, EventUpdate
from app.models.user import UserPublic
from app.database.search_db import get_search_connection, sync_event_to_search_db

import re

NOME_BUSCA_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9 ]{1,60}$")

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventPublic])
@limiter.limit("100/minute")
def list_events(request: Request):
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
    sync_event_to_search_db(internal_event.model_dump())
    return internal_event


@router.get("/partner-feed", response_model=list[EventPublic])
def partner_feed(_payload: dict = Depends(require_scope("events:read"))):
    return list(events_db.values())

@router.get("/search", response_model=list[EventPublic])
def search_events(nome: str):
    if not NOME_BUSCA_REGEX.fullmatch(nome):
        raise HTTPException(
            status_code=400,
            detail="Parâmetro 'nome' contém caracteres não permitidos.",
        )

    conn = get_search_connection()
    query = "SELECT id, name, date, location FROM events WHERE name LIKE ?"
    cursor = conn.execute(query, (f"%{nome}%",))
    rows = cursor.fetchall()
    return [{"id": r[0], "name": r[1], "date": r[2], "location": r[3]} for r in rows]

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

@router.post("/{event_id}/comments")
def add_comment(
    event_id: int, texto: str, current_user: UserPublic = Depends(get_current_user)
):
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="Event not found")
    comments_db.setdefault(event_id, []).append(
        {"autor": current_user.username, "texto": texto}
    )
    return {"status": "comentário adicionado"}