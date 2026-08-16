# Banco de dados em memória, apenas para fins didáticos/

events_db: dict[int, dict] = {}
_next_id = 1


def get_next_id() -> int:
    global _next_id
    current_id = _next_id
    _next_id += 1
    return current_id
