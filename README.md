# eventos-api

API REST para gerenciamento de eventos e inscrições de usuários, construída com **FastAPI**, autenticação JWT/OAuth2, autorização por ownership (RBAC + recurso), rate limiting, CORS restritivo e persistência com **SQLModel**.

## Estrutura do projeto

```
eventos-api/
├── main.py                     # Ponto de entrada: app FastAPI, CORS, headers de segurança, rate limit, routers
├── requirements.txt
├── .env.example                # Modelo de variáveis de ambiente (não versionar o .env real)
├── .gitignore
├── app/
│   ├── auth/
│   │   ├── dependencies.py     # get_current_user, require_event_owner, require_inscricao_owner, require_role, require_scope
│   │   └── security.py         # JWT, bcrypt, tokens de usuário / MFA / cliente M2M
│   ├── core/
│   │   ├── limiter.py          # Limiter (slowapi) por IP
│   │   └── settings.py         # BaseSettings (DATABASE_URL, SECRET_KEY via .env)
│   ├── database/
│   │   ├── engine.py           # SQLModel engine, create_db_and_tables, get_session
│   │   ├── db.py               # clients_db e comments_db (ainda em memória)
│   │   └── search_db.py        # Legado do Ex.1 (busca consolidada no SQLModel)
│   ├── models/
│   │   ├── event.py            # Event, EventCreate, EventPublic, EventUpdate (extra=forbid)
│   │   ├── inscricao.py        # Inscricao, InscricaoCreate, InscricaoPublic
│   │   └── user.py             # User, UserCreate, UserPublic, Role
│   ├── routes/
│   │   ├── auth.py             # register, token (password + client_credentials), MFA, clients
│   │   ├── events.py           # CRUD eventos, search (whitelist), comments, partner-feed
│   │   ├── inscricoes.py       # criar inscrição + get com ownership
│   │   └── pages.py            # Páginas HTML (Jinja2) — exigem autenticação
│   └── templates/
│       ├── base.html
│       ├── events_list.html
│       └── event_detail.html   # comentários com auto-escape (sem |safe)
└── docs/
    ├── relatorio-TP1/          # TP1 — estrutura, response_model, XSS, CIA, DFD
    │   ├── relatorio.md
    │   └── dfd.md
    ├── relatorio-TP2/          # TP2 — misuse cases, STRIDE, threat model, OAuth2, RBAC/M2M
    │   └── relatorio_2.md
    └── relatorio-TP3/          # TP3 — OWASP, BOLA, XSS stored, CORS, rate limit, SQLModel
        ├── relatorio.md
        └── html/               # Evidências HTML do teste de XSS (antes/depois)
            ├── pagina_teste.html
            └── pagina_apos_teste.html
```

## Responsabilidade de cada módulo

| Módulo | Responsabilidade |
|--------|------------------|
| **main.py** | Monta a app, CORS (allowlist), middleware de headers de segurança, rate limit handler e registro dos routers. |
| **app/auth/** | Autenticação (JWT, bcrypt, MFA simulado) e autorização centralizada (ownership, papéis, escopos). |
| **app/core/** | Configuração (`Settings` + `.env`) e rate limiting. |
| **app/database/** | Persistência SQLModel (eventos, usuários, inscrições) e stores em memória remanescentes (clientes M2M, comentários). |
| **app/models/** | Schemas SQLModel/Pydantic de entrada e saída; `extra="forbid"` nos modelos de escrita. |
| **app/routes/** | Endpoints HTTP por domínio (`auth`, `events`, `inscricoes`, `pages`). |
| **app/templates/** | Páginas HTML do painel interno (Jinja2 com auto-escape). |
| **docs/** | Relatórios técnicos de cada TP (TP1, TP2 e TP3). |

## Documentação dos trabalhos

- **[TP1 — Relatório](docs/relatorio-TP1/relatorio.md)** — Ambiente, estrutura modular, `response_model`, páginas Jinja2, XSS e auto-escape, tríade CIA, DFD.  
  - [DFD e frameworks de referência](docs/relatorio-TP1/dfd.md)
- **[TP2 — Relatório](docs/relatorio-TP2/relatorio_2.md)** — Misuse cases, STRIDE, threat model, fronteiras de segurança, eixos de API, OAuth2 + bcrypt, RBAC + ownership, fluxo M2M e escopos.
- **[TP3 — Relatório](docs/relatorio-TP3/relatorio.md)** — SQL Injection (busca), leitura crítica OWASP Top 10, BOLA em inscrições, ownership centralizado + `extra='forbid'`, XSS stored, CORS e headers HTTP, rate limiting diferenciado, migração SQLModel + gestão de credenciais.  
  - Evidências HTML do XSS: [antes](docs/relatorio-TP3/html/pagina_teste.html) · [depois](docs/relatorio-TP3/html/pagina_apos_teste.html)

## Como rodar

```bash
# 1) Ambiente virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2) Dependências
pip install -r requirements.txt

# 3) Credenciais locais (não versionar)
cp .env.example .env
# Edite .env e defina SECRET_KEY com um valor forte gerado localmente

# 4) Subir a API
uvicorn main:app --reload
```

A API fica em `http://127.0.0.1:8000`. Documentação interativa: `/docs`.

## Variáveis de ambiente

| Variável        | Descrição                                      | Exemplo                     |
|-----------------|------------------------------------------------|-----------------------------|
| `DATABASE_URL`  | URL do banco (SQLModel / SQLAlchemy)           | `sqlite:///./eventos.db`    |
| `SECRET_KEY`    | Chave para assinar JWT (nunca hardcoded)       | valor forte gerado localmente |

Use o arquivo `.env` (já listado no `.gitignore`). O repositório entrega apenas `.env.example`.

## Principais endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `POST` | `/auth/register` | — | Cadastro de usuário |
| `POST` | `/auth/token` | — | Login (password ou `client_credentials`); rate limit 5/min |
| `POST` | `/auth/mfa/verify` | temp token | Segundo fator (admin) |
| `POST` | `/auth/clients/register` | admin | Cadastro de cliente M2M |
| `GET`  | `/events/` | — | Listar eventos |
| `POST` | `/events/` | usuário | Criar evento (organizer_id = usuário autenticado) |
| `GET`  | `/events/search?nome=` | — | Busca por nome (whitelist + query parametrizada) |
| `GET`  | `/events/{id}` | — | Detalhe do evento |
| `PUT`  | `/events/{id}` | dono ou admin | Atualizar evento |
| `POST` | `/events/{id}/comments` | usuário | Adicionar comentário |
| `GET`  | `/events/partner-feed` | escopo `events:read` | Feed para parceiro M2M |
| `POST` | `/inscricoes/` | usuário | Criar inscrição |
| `GET`  | `/inscricoes/{id}` | dono ou admin | Consultar inscrição (ownership) |
| `GET`  | `/pages/events` | usuário | Listagem HTML (painel interno) |
| `GET`  | `/pages/events/{id}` | usuário | Detalhe HTML + comentários |

## Segurança (resumo das correções TP3)

1. **Injeção (busca)** — whitelist/regex no parâmetro `nome` + query parametrizada via SQLModel.  
2. **BOLA** — `require_inscricao_owner` / `require_event_owner` centralizados em `app/auth/dependencies.py`.  
3. **Mass assignment** — `extra="forbid"` nos modelos de escrita.  
4. **XSS stored** — remoção de `|safe` nos templates; auto-escape do Jinja2.  
5. **CORS** — allowlist explícita (sem `*`); headers HSTS, X-Frame-Options, X-Content-Type-Options.  
6. **Força bruta** — rate limit `5/minute` no endpoint de login.  
7. **Credenciais** — `SECRET_KEY` e `DATABASE_URL` via `.env` + `BaseSettings`.

Detalhes, reprodução e evidências: [docs/relatorio-TP3/relatorio.md](docs/relatorio-TP3/relatorio.md).
