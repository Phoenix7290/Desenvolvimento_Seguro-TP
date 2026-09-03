# Exercício 8 — DFD e frameworks de referência

## Diagrama de fluxo de dados (descrição)

```
[Cliente: navegador/curl]  --(zona não confiável)--
        |
        | POST /events {name, date, location}
        v
=========== trust boundary: processo eventos-api ===========
   [Rotas FastAPI: routes/events.py, routes/pages.py]
        |                                  ^
        v                                  |
   [Modelos Pydantic: EventCreate,    JSON/HTML de resposta
    EventInternal, EventPublic]       (response_model filtra
        |                              organizer_id/audit_token)
        v
   [events_db — armazenamento em memória]
===============================================================
```

- Entrada de dados do usuário: payload JSON enviado pelo cliente (fora da trust boundary).
- Processamento: validação/serialização pelos modelos Pydantic dentro do processo da API.
- Armazenamento: `events_db` (simulado, em memória).
- Fluxo sensível: `organizer_id` e `audit_token` são gerados e armazenados dentro da trust
  boundary; a única saída controlada para fora dela é filtrada pelo `response_model`
  (Exercício 3) — se esse controle for removido, o dado sensível atravessa a boundary sem
  proteção.

## Frameworks de referência

| Framework | Controle de segurança concreto já discutido |
|---|---|
| OWASP | `response_model` do FastAPI (Ex. 3) mitigando exposição excessiva de dados (OWASP API3:2023 — Broken Object Property Level Authorization) |
| NIST SSDF | Uso de `venv`/`virtualenv` com `requirements.txt` (Ex. 1) para isolamento e rastreabilidade de dependências (prática PW.4 — reutilizar componentes de terceiros de forma controlada) |
| MITRE | Auto-escape do Jinja2 (Ex. 6) mitigando XSS refletido, mapeável a CWE-79 (Improper Neutralization of Input During Web Page Generation) |
