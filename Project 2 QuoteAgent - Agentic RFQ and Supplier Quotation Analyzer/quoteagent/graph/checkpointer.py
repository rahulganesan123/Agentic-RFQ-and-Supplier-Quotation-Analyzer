"""
Checkpointer factory for QuoteAgent LangGraph persistence.
Supports PostgreSQL (production LangGraph checkpointer) and SQLite/Memory for seamless local development.
Allows paused human review checkpoints to persist and resume later.
"""

import os
from typing import Any
from quoteagent.config import POSTGRES_URI, SQLITE_DB_PATH


def get_checkpointer(custom_uri: str = None) -> Any:
    """
    Returns an active checkpointer instance:
    1. PostgresSaver if POSTGRES_URI is defined and available.
    2. SqliteSaver (persistent file quoteagent_state.db) as local default.
    3. MemorySaver as in-memory fallback.
    """
    uri = custom_uri or POSTGRES_URI

    # 1. Attempt PostgreSQL checkpointer
    if uri and uri.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            # Sync or async connection context
            checkpointer = PostgresSaver.from_conn_string(uri)
            checkpointer.setup()
            return checkpointer
        except Exception as e:
            print(f"[Warning] Failed to initialize Postgres checkpointer ({e}). Falling back to SQLite.")

    # 2. SQLite checkpointer (persisted to disk)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        return checkpointer
    except Exception as e:
        print(f"[Warning] Failed to initialize SQLite checkpointer ({e}). Falling back to MemorySaver.")

    # 3. In-memory checkpointer fallback
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()
