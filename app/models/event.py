from sqlmodel import Field, SQLModel


class EventBase(SQLModel):
    name: str
    date: str
    location: str


class Event(EventBase, table=True):
    __tablename__ = "events"
    id: int | None = Field(default=None, primary_key=True)
    organizer_id: str = Field(foreign_key="users.username")
    audit_token: str


class EventCreate(EventBase):
    model_config = {"extra": "forbid"}


class EventPublic(EventBase):
    id: int


class EventUpdate(SQLModel):
    model_config = {"extra": "forbid"}
    name: str | None = None
    date: str | None = None
    location: str | None = None