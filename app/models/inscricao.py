from pydantic import BaseModel, ConfigDict


class InscricaoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: int


class InscricaoPublic(BaseModel):
    id: int
    event_id: int
    participante_id: str
    dados_pessoais: str