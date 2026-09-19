from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user, require_inscricao_owner
from app.database.engine import get_session
from app.models.event import Event
from app.models.inscricao import Inscricao, InscricaoCreate, InscricaoPublic
from app.models.user import UserPublic

router = APIRouter(prefix="/inscricoes", tags=["inscricoes"])


@router.post("/", response_model=InscricaoPublic)
def create_inscricao(
    inscricao: InscricaoCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if session.get(Event, inscricao.event_id) is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    db_inscricao = Inscricao(
        event_id=inscricao.event_id,
        participante_id=current_user.username,
        dados_pessoais=f"telefone de contato de {current_user.username}",
    )
    session.add(db_inscricao)
    session.commit()
    session.refresh(db_inscricao)
    return db_inscricao


@router.get("/{inscricao_id}", response_model=InscricaoPublic)
def get_inscricao(
    inscricao_id: int,
    current_user: UserPublic = Depends(require_inscricao_owner),
    session: Session = Depends(get_session),
):
    return session.get(Inscricao, inscricao_id)