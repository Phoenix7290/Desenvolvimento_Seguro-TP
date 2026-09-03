from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    organizer = "organizer"
    participant = "participant"
    admin = "admin"


class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = Role.organizer


class UserPublic(BaseModel):
    username: str
    role: Role


class UserInDB(UserPublic):
    hashed_password: str
    mfa_enabled: bool = False