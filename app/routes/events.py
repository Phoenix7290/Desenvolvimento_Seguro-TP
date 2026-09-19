import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user, require_event_owner, require_scope
from app.database.engine import get_session
from app.database.db import comments_db 
from app.models.event import Event, EventCreate, EventPublic, EventUpdate
from app.models.user import UserPublic

router = APIRouter(prefix="/events", tags=["events"])

NOME_BUSCA_REGEX = __import__("re").compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9 ]{1,60}$")


@router.get("/", response_model=list[EventPublic])
def list_events(session: Session = Depends(get_session)):
    return session.exec(select(Event)).all()


@router.post("/", response_model=EventPublic)
def create_event(
    event: EventCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    db_event = Event(
        name=event.name,
        date=event.date,
        location=event.location,
        organizer_id=current_user.username,
        audit_token=str(uuid.uuid4()),
    )
    session.add(db_event)
    session.commit()
    session.refresh(db_event)
    return db_event


@router.get("/partner-feed", response_model=list[EventPublic])
def partner_feed(
    _payload: dict = Depends(require_scope("events:read")),
    session: Session = Depends(get_session),
):
    return session.exec(select(Event)).all()


@router.get("/search", response_model=list[EventPublic])
def search_events(nome: str, session: Session = Depends(get_session)):
    if not NOME_BUSCA_REGEX.fullmatch(nome):
        raise HTTPException(status_code=400, detail="Parâmetro 'nome' contém caracteres não permitidos.")
    statement = select(Event).where(Event.name.like(f"%{nome}%"))  # parametrizado pelo próprio SQLModel/SQLAlchemy
    return session.exec(statement).all()


@router.get("/{event_id}", response_model=EventPublic)
def get_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventPublic)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    current_user: UserPublic = Depends(require_event_owner),
    session: Session = Depends(get_session),
):
    event = session.get(Event, event_id)
    update_data = event_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event

@router.post("/{event_id}/comments")
def add_comment(
    event_id: int,
    texto: str,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if session.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")
    comments_db.setdefault(event_id, []).append(
        {"autor": current_user.username, "texto": texto}
    )
    return {"status": "comentário adicionado"}