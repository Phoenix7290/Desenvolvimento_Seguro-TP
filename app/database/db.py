events_db: dict[int, dict] = {}
_next_id = 1

users_db: dict[str, dict] = {}

clients_db: dict[str, dict] = {}

inscricoes_db: dict[int, dict] = {}
_next_inscricao_id = 1

comments_db: dict[int, list[dict]] = {}


def get_next_id() -> int:
    global _next_id
    current_id = _next_id
    _next_id += 1
    return current_id


def get_user(username: str) -> dict | None:
    return users_db.get(username)


def get_client(client_id: str) -> dict | None:
    return clients_db.get(client_id)


def get_next_inscricao_id() -> int:
    global _next_inscricao_id
    current_id = _next_inscricao_id
    _next_inscricao_id += 1
    return current_id