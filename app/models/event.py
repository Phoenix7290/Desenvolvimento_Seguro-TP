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

    organizer_id: int
    audit_token: str
