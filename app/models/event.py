from pydantic import BaseModel


class EventCreate(BaseModel):

    name: str
    date: str
    location: str


class EventPublic(BaseModel):

    id: int
    name: str
    date: str
    location: str


class EventInternal(EventPublic):

    organizer_id: str
    audit_token: str


class EventUpdate(BaseModel):

    name: str | None = None
    date: str | None = None
    location: str | None = None