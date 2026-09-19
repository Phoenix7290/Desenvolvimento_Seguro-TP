from enum import Enum

from sqlmodel import Field, SQLModel


class Role(str, Enum):
    organizer = "organizer"
    participant = "participant"
    admin = "admin"


class UserBase(SQLModel):
    username: str = Field(index=True)
    role: Role = Role.organizer


class User(UserBase, table=True):
    __tablename__ = "users"
    username: str = Field(primary_key=True)
    hashed_password: str
    mfa_enabled: bool = False


class UserCreate(SQLModel):
    model_config = {"extra": "forbid"}
    username: str
    password: str
    role: Role = Role.organizer


class UserPublic(UserBase):
    pass