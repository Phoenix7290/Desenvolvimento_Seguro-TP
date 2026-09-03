from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "dev-secret-key-troque-em-producao"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MFA_PENDING_TOKEN_EXPIRE_MINUTES = 5
CLIENT_TOKEN_EXPIRE_MINUTES = 60

SIMULATED_MFA_CODE = "123456"

ROLE_SCOPES = {
    "participant": "events:read",
    "organizer": "events:read events:write:own",
    "admin": "events:read events:write:any",
}


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_client_secret_hash(client_secret: str) -> str:
    return pwd_context.hash(client_secret)


def verify_client_secret(plain_secret: str, hashed_secret: str) -> bool:
    return pwd_context.verify(plain_secret, hashed_secret)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(username: str, role: str) -> str:
    return _create_token(
        {
            "sub": username,
            "role": role,
            "scope": ROLE_SCOPES.get(role, "events:read"),
            "token_stage": "full",
            "client_type": "user",
        },
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_mfa_pending_token(username: str, role: str) -> str:
    return _create_token(
        {"sub": username, "role": role, "token_stage": "mfa_pending"},
        timedelta(minutes=MFA_PENDING_TOKEN_EXPIRE_MINUTES),
    )


def create_client_token(client_id: str, scope: str) -> str:
    return _create_token(
        {
            "sub": client_id,
            "scope": scope,
            "token_stage": "full",
            "client_type": "partner",
        },
        timedelta(minutes=CLIENT_TOKEN_EXPIRE_MINUTES),
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None