from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.database.db import comments_db
from app.database.engine import get_session
from app.models.event import Event
from app.models.user import UserPublic

router = APIRouter(prefix="/pages", tags=["pages"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/events")
def list_events_page(
    request: Request,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    events = session.exec(select(Event)).all()
    return templates.TemplateResponse(
        request=request, name="events_list.html", context={"events": events}
    )


@router.get("/events/{event_id}")
def event_detail_page(
    request: Request,
    event_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    comments = comments_db.get(event_id, [])
    return templates.TemplateResponse(
        request=request, name="event_detail.html",
        context={"event": event, "comments": comments},
    )