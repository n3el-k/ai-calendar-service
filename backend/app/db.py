import sqlite3
from pathlib import Path

from app.config import settings

DB_PATH: Path = settings.db_path

def init_db():
    connection = get_connection()

    create_events_table_query = """
    CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, title TEXT NOT NULL, 
    start_day_time TEXT NOT NULL, end_day_time TEXT, location TEXT, session_id TEXT NOT NULL)
    """
    create_sessions_table_query = """
    CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, last_seen TEXT)
    """
    create_index_sessions_table_query = """
    CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)
    """
    create_pending_table_query = """
    CREATE TABLE IF NOT EXISTS pending_actions (session_id TEXT PRIMARY KEY,
        event_json TEXT NOT NULL, created_at TEXT NOT NULL)
    """

    connection.execute(create_events_table_query)
    connection.execute(create_sessions_table_query)
    connection.execute(create_index_sessions_table_query)
    connection.execute(create_pending_table_query)
    
    close_connection(connection)

def get_connection() -> sqlite3.Connection:

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection

def close_connection(connection: sqlite3.Connection):

    connection.commit()
    connection.close()