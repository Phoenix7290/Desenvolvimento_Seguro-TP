from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth.security import decode_token
from app.database.db import events_db, get_user
from app.models.user import Role, UserPublic
from app.database.db import events_db, get_user, inscricoes_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("token_stage") != "full":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação incompleta — verificação MFA pendente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("client_type") != "user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Este token é de um cliente M2M, não de um usuário",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    user = get_user(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserPublic(username=user["username"], role=user["role"])

def _check_ownership(
    current_user: UserPublic, resource: dict | None, owner_field: str
) -> UserPublic:
    """
    Lógica de ownership centralizada (Exercício 4) — única fonte de verdade
    reaproveitada por qualquer recurso sensível do eventos-api, corrigindo a
    falha do Exercício 3 sem repetir a checagem endpoint por endpoint.
    """
    if resource is None:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    if current_user.role == Role.admin:
        return current_user
    if resource.get(owner_field) != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão sobre este recurso",
        )
    return current_user

def require_event_owner(
    event_id: int, current_user: UserPublic = Depends(get_current_user)
) -> UserPublic:
    return _check_ownership(current_user, events_db.get(event_id), "organizer_id")


def require_inscricao_owner(
    inscricao_id: int, current_user: UserPublic = Depends(get_current_user)
) -> UserPublic:
    return _check_ownership(
        current_user, inscricoes_db.get(inscricao_id), "participante_id"
    )
    
def require_role(*allowed_roles: Role):

    def checker(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Papel do usuário não tem permissão para esta ação",
            )
        return current_user

    return checker


def require_scope(required_scope: str):

    def checker(token: str = Depends(oauth2_scheme)) -> dict:
        payload = decode_token(token)
        if payload is None or payload.get("token_stage") != "full":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido, expirado ou com MFA pendente",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_scopes = payload.get("scope", "").split()
        if required_scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Escopo insuficiente — requer '{required_scope}'",
            )
        return payload

    return checker

