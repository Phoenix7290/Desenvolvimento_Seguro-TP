from enum import Enum

from pydantic import BaseModel, ConfigDict


class Role(str, Enum):
    organizer = "organizer"
    participant = "participant"
    admin = "admin"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str
    role: Role = Role.organizer


class UserPublic(BaseModel):
    username: str
    role: Role


class UserInDB(UserPublic):
    hashed_password: str
    mfa_enabled: bool = False