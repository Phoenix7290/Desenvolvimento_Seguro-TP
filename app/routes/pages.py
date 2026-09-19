from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_current_user
from app.database.db import events_db, comments_db
from app.models.user import UserPublic

router = APIRouter(prefix="/pages", tags=["pages"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/events")
def list_events_page(
    request: Request, current_user: UserPublic = Depends(get_current_user)
):
    events = list(events_db.values())
    return templates.TemplateResponse(
        request=request, name="events_list.html", context={"events": events}
    )


@router.get("/events/{event_id}")
def event_detail_page(request: Request, event_id: int, current_user: UserPublic = Depends(get_current_user)):
    if event_id not in events_db:
        raise HTTPException(status_code=404, detail="Event not found")
    event = events_db[event_id]
    comments = comments_db.get(event_id, [])
    return templates.TemplateResponse(
        request=request, name="event_detail.html",
        context={"event": event, "comments": comments},
    )