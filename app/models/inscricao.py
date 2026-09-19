from sqlmodel import Field, SQLModel


class InscricaoBase(SQLModel):
    event_id: int = Field(foreign_key="events.id")


class Inscricao(InscricaoBase, table=True):
    __tablename__ = "inscricoes"
    id: int | None = Field(default=None, primary_key=True)
    participante_id: str = Field(foreign_key="users.username")
    dados_pessoais: str


class InscricaoCreate(InscricaoBase):
    model_config = {"extra": "forbid"}


class InscricaoPublic(InscricaoBase):
    id: int
    participante_id: str
    dados_pessoais: str