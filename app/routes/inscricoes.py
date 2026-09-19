from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user, require_inscricao_owner
from app.database.db import events_db, get_next_inscricao_id, inscricoes_db
from app.models.inscricao import InscricaoCreate, InscricaoPublic
from app.models.user import UserPublic

router = APIRouter(prefix="/inscricoes", tags=["inscricoes"])


@router.post("/", response_model=InscricaoPublic)
def create_inscricao(
    inscricao: InscricaoCreate, current_user: UserPublic = Depends(get_current_user)
):
    if inscricao.event_id not in events_db:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    inscricao_id = get_next_inscricao_id()
    record = {
        "id": inscricao_id,
        "event_id": inscricao.event_id,
        "participante_id": current_user.username,
        "dados_pessoais": f"telefone de contato de {current_user.username}",
    }
    inscricoes_db[inscricao_id] = record
    return record


@router.get("/{inscricao_id}", response_model=InscricaoPublic)
def get_inscricao(
    inscricao_id: int, current_user: UserPublic = Depends(require_inscricao_owner)
):
    return inscricoes_db[inscricao_id]