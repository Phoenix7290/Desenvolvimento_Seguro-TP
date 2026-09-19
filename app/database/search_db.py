import sqlite3


def _create_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


_search_conn = _create_connection()


def sync_event_to_search_db(event: dict) -> None:
    """Espelha um evento recém-criado em events_db para a tabela de busca."""
    _search_conn.execute(
        "INSERT OR REPLACE INTO events (id, name, date, location) VALUES (?, ?, ?, ?)",
        (event["id"], event["name"], event["date"], event["location"]),
    )
    _search_conn.commit()


def get_search_connection() -> sqlite3.Connection:
    return _search_conn