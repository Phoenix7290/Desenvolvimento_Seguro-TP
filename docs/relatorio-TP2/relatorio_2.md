# Misuse Cases - Exercício 1

Levantamento de ações mal-intencionadas plausíveis contra o `eventos-api`,
elaborado antes da categorização formal com STRIDE. Baseado no código real
do TP1 (`database/db.py`, `models/event.py`, `routes/events.py`, `routes/pages.py`).

## MC-01 — Criação de eventos falsos/spam por qualquer visitante

- **Ator malicioso:** usuário anônimo, sem cadastro ou login.
- **Ação indesejada:** chama `POST /events/` repetidamente para inserir
  centenas de eventos falsos (nome, data e local arbitrários).
- **Impacto:** poluição do catálogo de eventos, degradação da experiência
  de quem consulta `GET /events/` e `/pages/events`, possível esgotamento
  de memória do processo (o "banco" é um `dict` em memória, sem limite).
- **Vetor concreto:** `create_event` em `routes/events.py` não exige
  nenhuma autenticação nem faz rate limiting.

## MC-02 — Falsificação de autoria do evento (organizer_id)

- **Ator malicioso:** qualquer chamador da API, autenticado ou não.
- **Ação indesejada:** cria um evento esperando que ele seja atribuído a
  si mesmo, mas na prática qualquer criação é gravada com
  `organizer_id=42`, hardcoded — ou, quando a autenticação existir, tenta
  manipular esse campo para se passar por outro organizador.
- **Impacto:** perda de rastreabilidade de quem realmente criou cada
  evento; base para disputas de propriedade quando a autorização de
  edição existir (Exercício 6).
- **Vetor concreto:** `organizer_id=42` fixo em `create_event`, sem
  vínculo com um usuário autenticado real.

## MC-03 — Uso do endpoint de demonstração insegura em produção

- **Ator malicioso:** atacante que descobre rotas não documentadas via
  fuzzing ou leitura do OpenAPI gerado automaticamente pelo FastAPI.
- **Ação indesejada:** usa `POST /events/insecure-demo` — cópia de
  `create_event` sem nenhuma proteção adicional — como via alternativa
  para escrever dados caso a rota principal ganhe controles no futuro.
- **Impacto:** qualquer mitigação aplicada só à rota "oficial" é
  contornada por essa rota espelho, tornando o esforço de correção inútil.
- **Vetor concreto:** rota `/events/insecure-demo` em `routes/events.py`,
  duplicando a lógica de criação sem review de segurança.

## MC-04 — Divulgação de dados internos via páginas HTML públicas

- **Ator malicioso:** qualquer visitante do site, incluindo concorrentes.
- **Ação indesejada:** acessa `/pages/events` e `/pages/events/{id}`, que
  renderizam `organizer_id` diretamente no HTML, sem autenticação nem
  controle de quem pode ver esse "painel interno de operações".
- **Impacto:** vazamento de metadados internos (id do organizador) para
  qualquer pessoa na internet; a própria página se autodenomina "uso
  interno — equipe de operações", indicando expectativa de
  confidencialidade que não é aplicada tecnicamente.
- **Vetor concreto:** `routes/pages.py` não possui nenhuma verificação de
  autenticação/autorização antes de renderizar os templates.

## MC-05 — Manipulação de datas/locais para causar inconsistência de exibição

- **Ator malicioso:** usuário mal-intencionado explorando a falta de
  validação de formato.
- **Ação indesejada:** envia `date` como string arbitrária (ex.: HTML,
  texto muito longo, valor não-parseável) já que `EventCreate.date` é um
  `str` livre, sem validação de formato de data.
- **Impacto:** quebra de exibição nas páginas HTML (`event_detail.html`,
  `events_list.html`), inconsistência de dados para qualquer futura
  ordenação/filtragem por data, potencial vetor de XSS refletido caso o
  Jinja2 autoescaping seja desabilitado em algum ponto futuro.
- **Vetor concreto:** ausência de validação de formato em
  `EventCreate.date` (`models/event.py`).

## Priorização por impacto

1. **MC-04** (vazamento de dados internos) — maior impacto imediato: dado
   já sai da aplicação para qualquer visitante, sem exigir nenhuma ação
   adicional do atacante além de acessar uma URL pública.
2. **MC-03** (rota insegura espelho) — alto impacto porque invalida
   qualquer mitigação futura enquanto a rota existir; é uma "porta dos
   fundos" persistente.
3. **MC-02** (falsificação de autoria) — impacto estrutural: compromete a
   integridade de todo o modelo de autorização que será construído no
   Exercício 6.
4. **MC-01** (spam/DoS de criação) — impacto operacional, mas reversível
   (dados podem ser limpos) e menos crítico que vazamento ou backdoor.
5. **MC-05** (dados malformados) — impacto mais limitado hoje (não há
   renderização perigosa visível), mas vira mais relevante conforme a
   aplicação cresce.


# Análise STRIDE — Exercício 2

Aplicação do framework STRIDE a três componentes do sistema, com base nos
misuse cases levantados em `misuse-cases.md`.

| Componente | Categoria STRIDE | Ameaça identificada |
|---|---|---|
| Rota de criação de evento (`POST /events/`, `routes/events.py`) | **Spoofing** | Como não há autenticação nem vínculo real com um usuário, qualquer chamador pode "assumir" a autoria de um evento; hoje isso se manifesta como `organizer_id` sempre igual a 42, mascarando quem de fato originou a requisição. |
| Rota de criação de evento (`POST /events/`, incluindo `/insecure-demo`) | **Denial of Service** | Ausência de autenticação e de rate limiting permite que um script envie milhares de requisições de criação, esgotando memória do `events_db` (dict em memória, sem limite de tamanho) e degradando a resposta para usuários legítimos. |
| Camada de autenticação futura (ainda inexistente — Exercício 6/7) | **Elevation of Privilege** | Quando papéis (organizador, participante, administrador) forem implementados, a ausência de verificação de ownership na edição de evento (nenhuma rota de edição existe ainda) é um ponto onde um participante comum poderia, por falha de implementação, editar ou assumir dados de eventos de outro organizador. |
| Camada de autenticação futura | **Repudiation** | Sem registro de quem fez cada ação (não há log de autoria vinculado a uma identidade real, apenas um `audit_token` gerado por `uuid4()` e nunca consultado ou exposto em nenhum endpoint), um organizador pode negar ter criado ou alterado um evento, e não há como provar o contrário. |
| Armazenamento de dados (`database/db.py`, dict em memória) | **Tampering** | Qualquer código executando no mesmo processo (ou uma futura rota mal protegida) pode alterar diretamente `events_db`, já que não há camada de validação/controle de acesso entre a "escrita lógica" (via rota) e o dado persistido — hoje o dict é acessível a qualquer módulo que o importe. |
| Armazenamento de dados / páginas HTML (`routes/pages.py`) | **Information Disclosure** | `/pages/events` e `/pages/events/{id}` expõem `organizer_id` (dado interno) para qualquer visitante, sem nenhuma autenticação — o próprio template se identifica como "painel interno de operações", confirmando que esse dado não deveria ser público. |

## Observações

- A rota `/events/insecure-demo` foi tratada como parte do mesmo
  componente "rota de criação de evento", pois duplica exatamente a
  mesma lógica e portanto herda a mesma exposição a Spoofing e DoS —
  qualquer mitigação aplicada apenas à rota principal deve também cobrir
  essa rota espelho.
- A "camada de autenticação" é tratada como componente mesmo não
  existindo ainda no código, porque o TP2 pede explicitamente sua
  modelagem antes da implementação (Exercícios 6 e 7); isso evita que a
  ameaça de elevação de privilégio só seja descoberta depois do deploy,
  como já aconteceu em outro projeto da empresa segundo o enunciado.


# Threat Model — Exercício 3

Documento de referência oficial da modelagem de ameaças do `eventos-api`,
consolidando os misuse cases (`misuse-cases.md`) e a análise STRIDE
(`stride-analysis.md`). Escrito para ser lido por outro desenvolvedor sem
contexto prévio do projeto.

## 1. Visão geral do sistema

O `eventos-api` é uma API FastAPI para gestão de eventos, com duas
interfaces: uma API REST (`routes/events.py`) consumida por clientes
programáticos, e um conjunto de páginas HTML server-side (`routes/pages.py`,
templates Jinja2) para visualização. Os dados são mantidos em memória
(`database/db.py`), sem persistência em disco nem banco relacional.

## 2. Ativos principais

| Ativo | Descrição | Por que importa |
|---|---|---|
| Dados de eventos | `name`, `date`, `location` de cada evento | Integridade e disponibilidade impactam diretamente usuários finais |
| Dados de organizador (`organizer_id`) | Vínculo entre evento e quem o criou | Base de todo controle de autorização futuro (ownership) |
| `audit_token` | Token `uuid4()` gerado por evento, hoje sem uso funcional | Ativo latente — projetado para rastreabilidade/auditoria futura |
| Credenciais futuras (senhas, tokens JWT) | Ainda não implementadas (Exercícios 6–8) | Comprometimento aqui dá acesso total às contas |

## 3. Superfícies de ataque identificadas

- `POST /events/` e `POST /events/insecure-demo` — criação de evento sem
  autenticação.
- `GET /events/{event_id}` — leitura pública (aceitável para dados
  públicos, mas sem rate limiting).
- `GET /pages/events` e `GET /pages/events/{event_id}` — páginas HTML sem
  autenticação, expondo `organizer_id`.
- Import direto do dict `events_db` por qualquer módulo do projeto —
  superfície interna de tampering.

## 4. Ameaças e mitigações

| # | Ameaça (STRIDE) | Componente | Mitigação proposta |
|---|---|---|---|
| 1 | Spoofing — autoria falsa de evento | Criação de evento | Implementar autenticação real (Exercício 6) e substituir `organizer_id=42` fixo pelo id do usuário autenticado extraído do token. |
| 2 | Denial of Service — flood de criação | Criação de evento (incl. `/insecure-demo`) | Exigir autenticação antes de criar eventos (elimina anônimos) e aplicar rate limiting por usuário/IP. |
| 3 | Elevation of Privilege — edição sem ownership | Futura rota de edição | Ao implementar edição, usar dependency injection do FastAPI para validar que `organizer_id` do evento bate com o usuário do token antes de permitir a alteração (Exercício 6). |
| 4 | Repudiation — negação de autoria | Camada de autenticação/registro | Vincular cada criação/edição a um usuário autenticado real e persistir esse vínculo; considerar expor `audit_token` em log de auditoria em vez de deixá-lo inerte. |
| 5 | Tampering — alteração direta do dict em memória | Armazenamento de dados | Encapsular todo acesso a `events_db` em uma camada de repositório com validação, em vez de import direto do dict por qualquer rota. |
| 6 | Information Disclosure — `organizer_id` exposto publicamente | Páginas HTML (`routes/pages.py`) | Exigir autenticação para acessar `/pages/*` (ou remover `organizer_id` do template se a página for de fato pública), já que o próprio conteúdo se declara "uso interno". |

Cada ameaça listada em `stride-analysis.md` aparece acima com pelo menos
uma mitigação associada (rastreabilidade #1–#6).

## 5. Prioridade de correção

Seguindo a priorização por impacto de `misuse-cases.md`: primeiro a
mitigação #6 (vazamento em `/pages/*`), depois #2 (rota insegura/DoS),
seguida de #1 e #3 (autenticação e ownership, tratadas juntas no
Exercício 6), depois #4 e #5.


# Fronteiras de Segurança e Fluxo de Dados — Exercício 4

## Partições do sistema

1. **Cliente** — navegador ou script externo (httpie, front-end,
   futuro parceiro M2M) que consome a API ou visualiza as páginas HTML.
2. **Camada de API/aplicação** — processo FastAPI, contendo os routers
   (`routes/events.py`, `routes/pages.py`) e os modelos Pydantic
   (`models/event.py`).
3. **Armazenamento de dados** — módulo `database/db.py`, hoje um dict
   `events_db` em memória dentro do próprio processo Python.

## Fluxo de dados e cruzamento de fronteiras

```
[Cliente] --(1) HTTP request--> [Camada de API]
                                      |
                                (2) chamada de função
                                      v
                              [Armazenamento de dados]
                                      |
                                (3) retorno do dict
                                      v
                              [Camada de API] --(4) response_model / template--> [Cliente]
```

- **Cruzamento (1):** requisição HTTP do cliente para a API — é a
  fronteira de confiança mais exposta, pois qualquer ator na internet
  pode iniciá-la. Hoje, nenhum controle de autenticação existe nesse
  ponto para `POST /events/` nem para `/pages/*`.
- **Cruzamento (2):** dentro do mesmo processo, `routes/events.py` e
  `routes/pages.py` importam e manipulam `events_db` diretamente. Não é
  uma fronteira de rede, mas é uma fronteira de confiança de código —
  qualquer módulo com acesso ao import pode ler/escrever sem passar por
  validação centralizada.
- **Cruzamento (3):** o dado bruto do armazenamento retorna para a
  camada de API sem sanitização adicional além da validação Pydantic
  já aplicada na entrada.
- **Cruzamento (4):** a resposta cruza de volta a fronteira de confiança
  para o cliente. No caso da API REST, o `response_model=EventPublic`
  filtra corretamente `organizer_id` e `audit_token` da resposta JSON.
  No caso das páginas HTML (`routes/pages.py`), esse filtro **não
  existe** — os templates recebem o dicionário completo do evento e
  renderizam `organizer_id` diretamente.

## Como essa visão confirma/refina o threat model

A visão de partições confirma a ameaça de Information Disclosure (#6 no
threat model): o cruzamento (4) mostra que existem dois caminhos de
saída de dados da camada de API para o cliente — um filtrado
(`response_model` da API REST) e um não filtrado (templates HTML) — e é
justamente o caminho não filtrado que vaza `organizer_id`. Além disso, a
ausência de qualquer controle no cruzamento (1) para as rotas de escrita
confirma que Spoofing e DoS (#1 e #2) atuam exatamente na borda mais
exposta do sistema, reforçando que a autenticação (Exercício 6) precisa
ser aplicada o mais próximo possível dessa fronteira de entrada, antes de
qualquer lógica de negócio ser executada.


# Eixos de Segurança de API : Abertura a Parceiros Externos - Exercício 5

Análise de vetores de ataque segundo os três eixos de segurança de APIs,
para o cenário de abrir parte do `eventos-api` a parceiros externos via
integração automatizada (M2M), além dos usuários finais via navegador.

| Eixo | Vetor de ataque identificado | Coberto pelo threat model? |
|---|---|---|
| **Design** | Falta de escopos de acesso diferenciados: hoje não existe nenhum conceito de escopo/permissão granular — se um parceiro M2M receber as mesmas credenciais/rotas que um organizador humano, ele poderá executar qualquer operação, além do combinado em contrato. | **Lacuna nova.** O threat model atual cobre autenticação e ownership, mas não modela diferenciação de escopo entre tipos de cliente (organizador vs. parceiro M2M). |
| **Implementação** | Validação de entrada fraca em `EventCreate.date` (campo `str` livre, sem parsing/formatação) pode ser explorada por um parceiro automatizado enviando payloads malformados em volume, já que integrações M2M tendem a gerar tráfego maior e mais repetitivo que usuários humanos. | **Já coberto** — corresponde ao MC-05 dos misuse cases e pode ser tratado junto da mitigação de validação de dados. |
| **Infraestrutura** | Risco de exposição de rotas internas (`/pages/*`, pensadas para uso interno da equipe de operações) ao mesmo domínio/host público usado pela API de parceiros, caso não haja segmentação de rede ou de rota entre o painel interno e a API externa. | **Lacuna nova** — o threat model trata `/pages/*` como vazamento de dado (Information Disclosure), mas não havia, até aqui, considerado o risco adicional de exposição de infraestrutura quando parceiros externos passarem a ser roteados para o mesmo serviço. |

## Por que considerar os três eixos, e não só implementação

Focar apenas no eixo de implementação (ex.: só corrigir validação de
input ou só trocar hashing de senha) resolveria o MC-05, mas deixaria
passar exatamente os dois vetores mais críticos para o cenário de
parceiros externos: sem um vetor de **design** (escopos), um parceiro
comprometido teria acesso equivalente a um administrador humano, mesmo
que toda a implementação esteja tecnicamente correta; e sem considerar
**infraestrutura**, a segmentação entre painel interno e API pública pode
não existir fisicamente, tornando qualquer controle de aplicação
insuficiente caso a rede permita acesso direto às rotas internas. Isso é
consistente com o alerta do enunciado: decisões de autenticação tomadas
sem olhar infraestrutura já causaram exposição indevida de endpoints
internos em outro serviço da empresa — exatamente o risco identificado
aqui para `/pages/*`.


# Autenticação OAuth2 + bcrypt — Exercício 6

Para o resultado visto em images/ex06, foram utilizados os seguintes comandos:

```bash
# 1) Registrar dois organizadores.
http POST :8000/auth/register username=alice password=senha123 role=organizer
http POST :8000/auth/register username=bob password=senha456 role=organizer

# 2) Fazer login de cada organizador.
# Atenção: use --form, pois o endpoint recebe OAuth2PasswordRequestForm,
# e não um corpo JSON.
http --form POST :8000/auth/token username=alice password=senha123
http --form POST :8000/auth/token username=bob password=senha456
# Guarde os dois access_token retornados.

# 3) Alice cria um evento.
# Substitua TOKEN_ALICE pelo token obtido na etapa 2.
http POST :8000/events/ Authorization:"Bearer TOKEN_ALICE" name="Festa" date="2026-10-10" location="SP"
# Anote o id retornado (por exemplo, 1).

# 4) Alice edita o próprio evento; a resposta esperada é HTTP 200.
http PUT :8000/events/1 Authorization:"Bearer TOKEN_ALICE" location="RJ"

# 5) Bob tenta editar o evento de Alice; a resposta esperada é HTTP 403.
# Substitua TOKEN_BOB pelo token obtido na etapa 2.
http PUT :8000/events/1 Authorization:"Bearer TOKEN_BOB" location="BH"
```

# Decisão de Modelo de Autorização — Exercício 7

## Comparação

| Modelo | Como funciona | Encaixe no eventos-api |
|---|---|---|
| **RBAC** (Role-Based Access Control) | Permissões atreladas a um papel fixo do usuário (organizador, participante, admin). | Simples de implementar e de raciocinar sobre; suficiente quando as regras de acesso não mudam por contexto. |
| **ABAC** (Attribute-Based Access Control) | Permissões calculadas a partir de atributos dinâmicos (hora, localização, atributos do recurso, relação usuário-recurso). | Poderoso, mas exige um motor de políticas e mais infraestrutura — overkill para regras que hoje dependem só de "quem é o usuário". |
| **Autorização por recurso** (ownership-based) | Permissão verificada comparando o usuário com o dono do recurso específico. | Já usada no Exercício 6 (`require_event_owner`) e continua necessária mesmo com RBAC — são complementares, não excludentes. |

## Recomendação

Para o `eventos-api`, recomendo **RBAC combinado com autorização por
recurso**, não ABAC puro.

Justificativa: os três papéis do domínio (organizador, participante,
administrador) têm permissões que não variam por atributos dinâmicos —
um admin pode moderar qualquer evento independente de hora do dia,
localização do evento ou qualquer outro atributo contextual. O que varia
por *recurso específico* (não por atributo do ambiente) é o ownership —
e isso já é resolvido com uma checagem direta de propriedade
(`organizer_id == current_user.username`), sem precisar de um motor de
políticas ABAC.

**Cenário concreto do domínio:** um participante denuncia um evento com
conteúdo impróprio. O administrador precisa poder editar/remover esse
evento mesmo não sendo o organizador. Isso é exatamente o que a
combinação RBAC + ownership resolve: a checagem de papel (`role ==
admin`) dá bypass da checagem de ownership, implementado em
`require_event_owner` (`app/auth/dependencies.py`). Se um dia surgir uma
regra do tipo "admin só pode moderar eventos da própria região" (um
atributo do recurso combinado com um atributo do usuário), aí sim valeria
migrar essa regra específica para ABAC — mas hoje essa necessidade não
existe.

ABAC seria justificável se, por exemplo, o eventos-api precisasse de
regras como "organizadores só podem editar eventos que ainda não
começaram" (atributo de tempo do recurso) ou "participantes só veem
eventos da própria cidade" — nenhuma dessas regras existe no escopo
atual dos exercícios.


# Fluxo OAuth2 M2M e Escopos — Exercício 8

## Escolha do fluxo

Para o parceiro externo, o fluxo escolhido é **OAuth2 Client Credentials
Grant**, em vez do **Resource Owner Password** já usado para usuários
finais (Exercícios 6/7).

Justificativa: Client Credentials existe justamente para comunicação
máquina-a-máquina, sem um usuário humano na outra ponta — o parceiro se
autentica com `client_id`/`client_secret` (credencial da aplicação, não
de uma pessoa), sem senha de usuário nem qualquer redirect de navegador.
Authorization Code (o fluxo "com redirect e tela de login") também não
se aplica aqui pela mesma razão: não há navegador nem consentimento de
usuário final envolvido, só um servidor conversando com outro.

## Escopos e claims por tipo de cliente

| Claim | Usuário final (organizador) | Parceiro M2M |
|---|---|---|
| `sub` | `username` (ex.: `alice`) | `client_id` (ex.: `parceiro-x`) |
| `role` | `organizer` / `participant` / `admin` | *(ausente — parceiros não têm papel RBAC de usuário)* |
| `client_type` | `user` | `partner` |
| `scope` | calculado a partir do papel (ex.: `events:read events:write:own`) | definido no cadastro do parceiro pelo contrato comercial (ex.: `events:read`) |
| `token_stage` | `full` (ou `mfa_pending` durante o segundo fator) | `full` |

O ponto central pedido pelo time jurídico — limitar tecnicamente o que o
parceiro pode fazer, não só descrever em contrato — é resolvido porque o
`scope` do token do parceiro vem do que foi cadastrado em
`clients_db` no momento do provisionamento, e **não** é escolhido
livremente pelo parceiro na requisição de token. Mesmo que o token vaze,
ele só carrega o escopo contratado.

## Exemplo de payload decodificado

Organizador humano (`alice`), obtido via `grant_type=password`:

```json
{
  "sub": "alice",
  "role": "organizer",
  "scope": "events:read events:write:own",
  "token_stage": "full",
  "client_type": "user",
  "exp": 1788399198
}
```

Parceiro M2M (`parceiro-x`), obtido via `grant_type=client_credentials`:

```json
{
  "sub": "parceiro-x",
  "scope": "events:read",
  "token_stage": "full",
  "client_type": "partner",
  "exp": 1788400999
}
```

Note que o token do parceiro não tem `role` (não existe um "papel" de
usuário aplicável) e seu `scope` é somente leitura — condizente com o
cenário descrito no enunciado, em que o parceiro consome dados via
integração automatizada sem operações de escrita previstas em contrato.
A rota de demonstração `GET /events/partner-feed`
(`app/routes/events.py`) aceita os dois tipos de token, desde que
tenham `events:read` no escopo — e uma tentativa do parceiro de criar
evento (`POST /events/`) é rejeitada, porque essa rota exige
especificamente um token de usuário (`client_type=user`).
