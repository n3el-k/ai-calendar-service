import sqlite3
from pathlib import Path

DB_PATH: Path = Path(__file__).resolve().parent.parent / "calendar.db"

def init_db():
    connection = get_connection()

    create_table_query = """
    CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, title TEXT NOT NULL, 
    start_day_time TEXT NOT NULL, end_day_time TEXT, location TEXT)
    """

    connection.execute(create_table_query)
    close_connection(connection)

def get_connection() -> sqlite3.Connection:

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection

def close_connection(connection: sqlite3.Connection):

    connection.commit()
    connection.close()