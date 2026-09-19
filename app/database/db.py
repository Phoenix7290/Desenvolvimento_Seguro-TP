clients_db: dict[str, dict] = {}
comments_db: dict[int, list[dict]] = {}


def get_client(client_id: str) -> dict | None:
    return clients_db.get(client_id)