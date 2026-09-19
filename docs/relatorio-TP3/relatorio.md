# Relatório Técnico — TP3

Este relatório documenta as vulnerabilidades identificadas e corrigidas no
`eventos-api` ao longo dos 8 exercícios do TP de Ambiente Seguro em
Programação, cobrindo OWASP Top 10, BOLA, XSS stored, CORS, rate limiting e
migração da persistência para SQLModel. Assume-se que a autenticação JWT do
TP2 (`app/auth/security.py`, `app/auth/dependencies.py`) já está implementada.

Todas as evidências de "antes e depois" (prints de tela e outputs de
terminal) estão em `docs/relatorio-TP3/images/`, referenciadas pelo nome do
arquivo em cada seção.

---

# Exercício 1 — SQL Injection na busca de eventos

## Vulnerabilidade

O endpoint `GET /events/search` montava a query SQL concatenando
diretamente o parâmetro `nome` recebido do usuário:

```python
query = f"SELECT id, name, date, location FROM events WHERE name LIKE '%{nome}%'"
cursor = conn.execute(query)
```

Isso permite que qualquer caractere de controle SQL (aspas simples, `OR`,
`--`) altere a estrutura da query original.

## Reprodução

```bash
# comportamento normal
http GET ":8000/events/search?nome=Festa"

# 1) quebra de sintaxe — aspa simples não escapada
http GET ":8000/events/search?nome=Festa'"
# → 500 Internal Server Error (sqlite3.OperationalError: near "'": syntax error)

# 2) tautologia clássica — ignora o filtro de nome
http GET ":8000/events/search?nome=xyz' OR '1'='1"
# → 200 OK, retornando TODOS os eventos, mesmo "xyz" não batendo com nada
```

**Evidência:** `images/ex1-with-error.png`

## Correção

Duas camadas de defesa aplicadas:

1. **Whitelist + regex** sobre o parâmetro de entrada, rejeitando qualquer
   caractere fora do esperado antes de qualquer processamento:

```python
NOME_BUSCA_REGEX = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9 ]{1,60}$")

@router.get("/search", response_model=list[EventPublic])
def search_events(nome: str, session: Session = Depends(get_session)):
    if not NOME_BUSCA_REGEX.fullmatch(nome):
        raise HTTPException(
            status_code=400,
            detail="Parâmetro 'nome' contém caracteres não permitidos.",
        )
    statement = select(Event).where(Event.name.like(f"%{nome}%"))
    return session.exec(statement).all()
```

2. **Query parametrizada** via `select()`/`where()` do SQLModel (mais além
   do mínimo pedido no Exercício 1, mas que se tornou o padrão definitivo
   de toda a camada de persistência a partir do Exercício 8, eliminando a
   concatenação em vez de apenas mitigá-la neste único endpoint).

## Confirmação da correção

```bash
http GET ":8000/events/search?nome=Festa'"
# → 400 Bad Request {"detail":"Parâmetro 'nome' contém caracteres não permitidos."}

http GET ":8000/events/search?nome=xyz' OR '1'='1"
# → 400 Bad Request (mesmo motivo)

http GET ":8000/events/search?nome=Festa"
# → 200 OK, comportamento normal preservado
```

**Evidência:** `images/ex1-without-error.png`

**Nota:** durante a implementação, identificamos que a rota `/search`
precisava ser declarada **antes** de `/{event_id}` em `events.py` — como o
FastAPI casa rotas na ordem de registro, `/search` estava sendo capturada
pelo path param `{event_id}` e retornando `422` (tentativa de converter
`"search"` para inteiro). Reordenar as rotas resolveu.

---

# Exercício 2 — Leitura crítica OWASP Top 10

Análise de três padrões vulneráveis do próprio código do `eventos-api`,
sem execução, apenas leitura crítica.

| # | Categoria OWASP | Local do código | Risco |
|---|---|---|---|
| 1 | **A02:2021 — Cryptographic Failures** | `app/auth/security.py`, constante `SECRET_KEY` hardcoded no código-fonte (antes da correção do Exercício 8) | Qualquer pessoa com acesso ao repositório consegue forjar tokens JWT válidos — inclusive com `role: admin` — sem nunca ter feito login de verdade, comprometendo toda a autenticação. |
| 2 | **A01:2021 — Broken Access Control (BOLA)** | `app/routes/inscricoes.py`, endpoint `GET /inscricoes/{inscricao_id}` (antes da correção do Exercício 4) | A dependência `get_current_user` prova apenas *quem* está autenticado, nunca compara esse usuário com o dono do recurso antes de retornar dados pessoais de outro usuário. |
| 3 | **A07:2021 — Identification and Authentication Failures** | `app/routes/auth.py`, endpoint `POST /auth/token` (antes da correção do Exercício 7) | Sem limite de tentativas por IP/usuário, um atacante pode tentar milhares de senhas por segundo contra qualquer conta, incluindo `admin`, sem bloqueio nem atraso progressivo. |

Os três padrões identificados aqui foram, não coincidentemente, corrigidos
nos exercícios seguintes deste mesmo TP3 — a leitura crítica funcionou como
um mapeamento inicial do trabalho a ser feito.

---

# Exercício 3 — BOLA em `GET /inscricoes/{id}`

## Vulnerabilidade

O endpoint de consulta de inscrição validava apenas autenticação, nunca
ownership:

```python
@router.get("/{inscricao_id}", response_model=InscricaoPublic)
def get_inscricao(
    inscricao_id: int, current_user: UserPublic = Depends(get_current_user)
):
    inscricao = inscricoes_db.get(inscricao_id)
    if inscricao is None:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada")
    return inscricao
```

## Reprodução

```bash
# Carla se inscreve em um evento
http POST :8000/auth/register username=carla password=senha789 role=participant
http --form POST :8000/auth/token username=carla password=senha789
http POST :8000/inscricoes/ Authorization:"Bearer TOKEN_CARLA" event_id=1
# → {"id":1, "participante_id":"carla", "dados_pessoais":"telefone de contato de carla", ...}

# Bob, outro usuário autenticado sem qualquer relação com essa inscrição, acessa mesmo assim
http --form POST :8000/auth/token username=bob password=senha456
http GET :8000/inscricoes/1 Authorization:"Bearer TOKEN_BOB"
# → 200 OK, retornando os dados pessoais de Carla
```

**Evidência:** `images/ex3-part_one.png` `images/ex3-part_two.png`

## Onde exatamente falta a verificação

Em `get_inscricao`, a única dependência é `get_current_user` — ela prova
**autenticação** (quem é o chamador), mas o corpo da função nunca compara
`current_user.username` com `inscricao["participante_id"]`, que seria a
prova de **autorização** sobre este recurso específico.

## O que resolveria (implementado no Exercício 4)

Uma dependency equivalente ao já existente `require_event_owner`: buscar a
inscrição pelo `inscricao_id`, comparar `participante_id` com
`current_user.username` (com bypass para `role == admin`), retornando 403
se não bater.

---

# Exercício 4 — Middleware de ownership centralizado + `extra='forbid'`

## Correção — ownership centralizada

Implementada como **dependency injection centralizada** em
`app/auth/dependencies.py`, e não como middleware HTTP tradicional
(`@app.middleware("http")`), porque essa abordagem não tem acesso direto e
simples ao usuário autenticado nem ao path param do recurso sem reimplementar
a decodificação do token — dependency injection é o padrão idiomático do
FastAPI para esse tipo de checagem:

```python
def _check_ownership(
    current_user: UserPublic, resource, owner_attr: str
) -> UserPublic:
    """
    Lógica de ownership centralizada — única fonte de verdade reaproveitada
    por qualquer recurso sensível do eventos-api, corrigindo a falha do
    Exercício 3 sem repetir a checagem endpoint por endpoint.
    """
    if resource is None:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")
    if current_user.role == Role.admin:
        return current_user
    if getattr(resource, owner_attr) != current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão sobre este recurso",
        )
    return current_user


def require_event_owner(event_id: int, current_user=Depends(get_current_user), session=Depends(get_session)):
    return _check_ownership(current_user, session.get(Event, event_id), "organizer_id")


def require_inscricao_owner(inscricao_id: int, current_user=Depends(get_current_user), session=Depends(get_session)):
    return _check_ownership(current_user, session.get(Inscricao, inscricao_id), "participante_id")
```

Aplicada na rota vulnerável:

```python
@router.get("/{inscricao_id}", response_model=InscricaoPublic)
def get_inscricao(
    inscricao_id: int, current_user: UserPublic = Depends(require_inscricao_owner)
):
    return inscricoes_db[inscricao_id]
```

## Correção — `extra='forbid'`

Aplicado em todos os modelos Pydantic/SQLModel que recebem corpo de
requisição (`EventCreate`, `EventUpdate`, `UserCreate`, `InscricaoCreate`,
`MfaVerifyRequest`, `ClientRegisterRequest`), rejeitando qualquer campo não
declarado:

```python
class EventCreate(EventBase):
    model_config = {"extra": "forbid"}
```

## Testes

```bash
# Teste 1 — ownership bloqueado
http GET :8000/inscricoes/1 Authorization:"Bearer TOKEN_BOB"
# → 403 Forbidden {"detail":"Você não tem permissão sobre este recurso"}

# Teste 2 — campo extra rejeitado
http POST :8000/events/ Authorization:"Bearer TOKEN_ALICE" \
  name="Festa" date="2026-10-10" location="SP" is_admin:=true
# → 422 Unprocessable Entity {"detail":[{"loc":["body","is_admin"],"msg":"Extra inputs are not permitted","type":"extra_forbidden"}]}
```

**Evidência:** `images/ex4.png`

**Nota:** durante a implementação, identificamos que havia duas definições
da mesma rota `GET /{inscricao_id}` no arquivo — uma antiga (sem ownership)
e uma nova. Como o FastAPI casa a primeira rota registrada, a versão
vulnerável continuava ativa mesmo com a correção já escrita no código.
Remover a duplicata resolveu — um lembrete de que aplicar a correção não
basta; é preciso confirmar, via teste manual, que ela está de fato sendo
executada.

---

# Exercício 5 — XSS Stored nos comentários de evento

## Vulnerabilidade

O template `event_detail.html` renderizava o texto de comentários com o
filtro `| safe` do Jinja2, desabilitando explicitamente o auto-escape:

```html
<p><strong>{{ c.autor }}:</strong> {{ c.texto | safe }}</p>
```

## Reprodução

```bash
http POST ":8000/events/1/comments?texto=<script>alert('xss')</script>" \
  Authorization:"Bearer TOKEN_ALICE"
# → 200 OK {"status":"comentário adicionado"}
```

Ao abrir `/pages/events/1` no navegador, o `alert('xss')` dispara — o
script malicioso ficou persistido no "banco" e é executado toda vez que
qualquer visitante carrega a página, caracterizando XSS **stored** (afeta
todos os usuários, não só quem enviou o payload).

**Evidência:** `images/ex5-antes-alert.png` (popup do alert disparando)

## Correção

Remoção do `| safe`, deixando o auto-escape padrão do Jinja2 (ativo por
padrão para arquivos `.html` no `Jinja2Templates`) fazer o output encoding:

```html
<p><strong>{{ c.autor }}:</strong> {{ c.texto }}</p>
```

## Confirmação

Recarregando a mesma página com o mesmo comentário salvo, o payload passa a
ser exibido como texto literal, sem execução:

```html
<p><strong>alice:</strong> &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;</p>
```

**Evidência:** `html/pagina_teste.html`, `html/pagina_apos_teste.html`

---

# Exercício 6 — CORS e cabeçalhos de segurança HTTP

## Correção

**CORS com allowlist explícita** (sem wildcard `*`):

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://app.eventos-api.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Cabeçalhos de segurança HTTP** via middleware, aplicados a todas as
respostas:

```python
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
```

## Testes

```bash
# origem não autorizada
http OPTIONS :8000/events/ Origin:"http://site-malicioso.com" \
  Access-Control-Request-Method:GET Access-Control-Request-Headers:Authorization
# → 400 Bad Request "Disallowed CORS origin" — sem header Access-Control-Allow-Origin

# origem autorizada
http OPTIONS :8000/events/ Origin:"http://localhost:3000" \
  Access-Control-Request-Method:GET Access-Control-Request-Headers:Authorization
# → 200 OK com access-control-allow-origin: http://localhost:3000

# cabeçalhos de segurança em qualquer resposta
http GET :8000/
# → strict-transport-security, x-content-type-options, x-frame-options presentes
```

**Evidência:** `images/ex6.png`

O bloqueio de origem não autorizada foi rejeitado explicitamente pelo
`CORSMiddleware` do Starlette já na fase de preflight (`400 Bad Request`,
corpo `"Disallowed CORS origin"`), sem sequer expor o header
`Access-Control-Allow-Origin` — comportamento mais explícito do que apenas
omitir o header.

---

# Exercício 7 — Rate limiting diferenciado

## Correção

Implementado com `slowapi`, aplicando um limite restritivo apenas ao
endpoint de login:

```python
# app/core/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

```python
# app/routes/auth.py
@router.post("/token")
@limiter.limit("5/minute")
def login(request: Request, session: Session = Depends(get_session), ...):
    ...
```

```python
# main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## Justificativa da diferenciação por tipo de rota

O endpoint de login é alvo natural de força bruta: cada tentativa é barata
para o atacante e cara para a segurança, já que uma única senha
comprometida dá acesso total à conta. Já a listagem de eventos
(`GET /events/`) é consultada constantemente por usuários legítimos
navegando normalmente, sem envolver validação de credencial nenhuma —
aplicar o mesmo limite de 5/min quebraria a experiência de uso sem ganho de
segurança proporcional. Rate limiting não deve ser "quanto menor, mais
seguro"; o limite precisa ser calibrado pelo custo de abuso de cada tipo de
operação, não aplicado uniformemente à API inteira.

## Teste

```bash
for i in $(seq 1 7); do
  http --form POST :8000/auth/token username=alice password=senha_errada
done
```

Resultado: as primeiras 5 requisições retornam `401 Unauthorized` (senha
incorreta, mas dentro do limite); a partir da 6ª, `429 Too Many Requests`
com o corpo `{"error": "Rate limit exceeded: 5 per 1 minute"}`.

**Evidência:** `images/ex7-part_one.png`, `images/ex7-part_two.png`

---

# Exercício 8 — Migração para SQLModel + gestão de credenciais

## Migração da persistência

Toda a camada de dados em memória (`events_db`, `users_db`,
`inscricoes_db`, dicts em `app/database/db.py`) foi migrada para tabelas
SQLModel (`User`, `Event`, `Inscricao`), com sessões gerenciadas via
dependency injection:

```python
# app/database/engine.py
from sqlmodel import Session, SQLModel, create_engine
from app.core.settings import settings

engine = create_engine(settings.database_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

```python
# main.py
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
```

Todas as operações passaram a usar `session.get(...)` e
`session.exec(select(...))`, eliminando qualquer concatenação de string
remanescente na camada de persistência — inclusive consolidando o banco
SQLite paralelo criado no Exercício 1 (`search_db.py`) na mesma tabela
`Event` usada por todo o restante da API, via `select(Event).where(Event.name.like(...))`
(parametrizado nativamente pelo SQLAlchemy).

`clients_db` (cadastro de parceiros M2M) e `comments_db` (comentários do
Exercício 5) permaneceram em memória, fora do escopo desta migração — não
fizeram parte do pedido explícito do enunciado, que tratava
especificamente de eventos, usuários e inscrições.

## Gestão de credenciais

```python
# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str
    secret_key: str

settings = Settings()
```

```
# .env (NÃO commitado — já presente no .gitignore)
DATABASE_URL=sqlite:///./eventos.db
SECRET_KEY=<chave gerada localmente>
```

```
# .env.example (commitado, sem valores reais)
DATABASE_URL=sqlite:///./eventos.db
SECRET_KEY=coloque-uma-chave-secreta-aqui
```

A constante `SECRET_KEY` hardcoded em `app/auth/security.py` — identificada
como vulnerabilidade A02 (Cryptographic Failures) no Exercício 2 — foi
substituída por `settings.secret_key`, fechando definitivamente essa
lacuna:

```python
from app.core.settings import settings
SECRET_KEY = settings.secret_key
```

## Teste de fumaça (banco novo, do zero)

```bash
rm -f eventos.db
python -m uvicorn main:app --reload
```

```bash
http POST :8000/auth/register username=alice password=senha123 role=organizer
http --form POST :8000/auth/token username=alice password=senha123
http POST :8000/events/ Authorization:"Bearer TOKEN_ALICE" name="Festa" date="2026-10-10" location="SP"
http GET ":8000/events/search?nome=Festa"
http POST :8000/inscricoes/ Authorization:"Bearer TOKEN_ALICE" event_id=1
```

Todos os passos retornaram `200 OK`, confirmando que a migração para
SQLModel preservou o comportamento de todas as correções aplicadas nos
exercícios anteriores (validação por regex do Ex1, ownership do Ex4,
autenticação do TP2).

**Evidência:** `images/ex8-part_one.png`, `images/ex8-part_two.png`

---

# Considerações finais

O eventos-api evoluiu, ao longo deste TP3, de uma estrutura em memória sem
nenhuma validação de entrada, autorização granular ou controle de acesso
por origem, para uma API com: validação por whitelist nas entradas
críticas, autorização por ownership centralizada, output encoding
consistente, política de CORS restritiva, cabeçalhos de segurança padrão,
rate limiting diferenciado por sensibilidade de rota, e persistência
parametrizada com gestão de credenciais fora do código-fonte. As
vulnerabilidades corrigidas mapeiam diretamente para OWASP A01 (BOLA), A02
(Cryptographic Failures), A03 (Injection) e A07 (Authentication Failures),
identificadas previamente na leitura crítica do Exercício 2.