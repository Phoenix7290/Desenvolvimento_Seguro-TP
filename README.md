# eventos-api

API REST para gerenciamento de inscrições de usuários em eventos, construída com FastAPI.

## Estrutura do projeto

```
eventos-api/
├── main.py                 # Ponto de entrada. Cria a app FastAPI e registra os routers.
├── requirements.txt
└── app/
    ├── routes/              # Rotas HTTP, organizadas por recurso (um arquivo por domínio).
    │   └── events.py        # Endpoints do recurso "eventos": list, create, get by id.
    ├── models/              # Schemas Pydantic (validação de entrada e formato de resposta).
    │   └── event.py          # EventCreate, EventPublic (resposta segura), EventInternal.
    └── database/             # Camada de acesso a dados.
        └── db.py              # "Banco" em memória e geração de ids.
```

## Responsabilidade de cada módulo

- **main.py**: monta a aplicação e conecta os routers. Não contém lógica de negócio nem
  definições de rota específicas de um domínio.
- **app/routes/**: define os endpoints HTTP. Cada recurso (eventos, futuramente inscrições,
  usuários) tem seu próprio arquivo e seu próprio `APIRouter`, evitando que uma mudança em
  um recurso afete rotas de outro.
- **app/models/**: define os formatos de dados (Pydantic). Separa explicitamente o que é
  público (`EventPublic`) do que é uso interno (`EventInternal`), controlando o que a API
  expõe.
- **app/database/**: concentra o acesso aos dados. Se o projeto migrar de memória para um
  banco real, só este módulo precisa mudar.

## Como rodar

```bash
source venv/bin/activate
uvicorn main:app --reload
```
