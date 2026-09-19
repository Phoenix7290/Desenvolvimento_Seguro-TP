from fastapi import APIRouter, Depends, Form, HTTPException, status, Request
from pydantic import BaseModel
from app.core.limiter import limiter

from app.auth.dependencies import require_role
from app.auth.security import (
    SIMULATED_MFA_CODE,
    create_access_token,
    create_client_token,
    create_mfa_pending_token,
    decode_token,
    get_client_secret_hash,
    get_password_hash,
    verify_client_secret,
    verify_password,
)
from app.database.db import clients_db, get_client, get_user, users_db
from app.models.user import Role, UserCreate, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


class MfaVerifyRequest(BaseModel):
    temp_token: str
    code: str


class ClientRegisterRequest(BaseModel):
    client_id: str
    client_secret: str
    scope: str 


@router.post("/register", response_model=UserPublic)
def register(user: UserCreate):
    if get_user(user.username) is not None:
        raise HTTPException(status_code=400, detail="Username já cadastrado")

    users_db[user.username] = {
        "username": user.username,
        "role": user.role,
        "hashed_password": get_password_hash(user.password),
    }
    return UserPublic(username=user.username, role=user.role)


@router.post("/clients/register")
def register_client(
    client: ClientRegisterRequest,
    _admin: UserPublic = Depends(require_role(Role.admin)),
):
    if get_client(client.client_id) is not None:
        raise HTTPException(status_code=400, detail="client_id já cadastrado")

    clients_db[client.client_id] = {
        "client_id": client.client_id,
        "hashed_secret": get_client_secret_hash(client.client_secret),
        "scope": client.scope,
    }
    return {"client_id": client.client_id, "scope": client.scope}


@router.post("/token")
@limiter.limit("5/minute")
def login(
    request: Request,
    grant_type: str = Form(default="password"),
    username: str | None = Form(default=None),
    password: str | None = Form(default=None),
    client_id: str | None = Form(default=None),
    client_secret: str | None = Form(default=None),
):
    if grant_type == "client_credentials":
        client = get_client(client_id or "")
        if client is None or not verify_client_secret(
            client_secret or "", client["hashed_secret"]
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="client_id ou client_secret inválidos",
            )
        access_token = create_client_token(client["client_id"], client["scope"])
        return {"access_token": access_token, "token_type": "bearer"}

    user = get_user(username or "")
    if user is None or not verify_password(password or "", user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["role"] == Role.admin:
        temp_token = create_mfa_pending_token(user["username"], user["role"])
        return {
            "mfa_required": True,
            "temp_token": temp_token,
            "detail": "Senha correta. Informe o código MFA em /auth/mfa/verify.",
        }

    access_token = create_access_token(user["username"], user["role"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/mfa/verify")
def verify_mfa(request: MfaVerifyRequest):
    payload = decode_token(request.temp_token)
    if payload is None or payload.get("token_stage") != "mfa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de MFA inválido ou expirado — refaça o login",
        )

    if request.code != SIMULATED_MFA_CODE:
        raise HTTPException(status_code=401, detail="Código MFA incorreto")

    access_token = create_access_token(payload["sub"], payload["role"])
    return {"access_token": access_token, "token_type": "bearer"}