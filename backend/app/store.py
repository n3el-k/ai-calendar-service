from datetime import datetime, timedelta
from uuid import uuid4

from app.models import Event
from app.db import get_connection, close_connection

def remove_event(event_id: str) -> Event | None:

    select_row_query = "SELECT * FROM events WHERE id = ?"
    delete_event_query = "DELETE FROM events WHERE id = ?"
    connection = get_connection()

    row = connection.execute(select_row_query, (event_id,)) .fetchone()       
    connection.execute(delete_event_query, (event_id,))
    close_connection(connection)
    
    if row:
        return _row_to_event(row)
    return None

def clear_store() -> None:

    connection = get_connection()
    connection.execute("DELETE FROM events")
    close_connection(connection)

def add_event(event: Event, event_id: str | None = None) -> str:
    # The event being passed in is a models.AddEvent as that is what the LLM outputs.
    event = Event(**event.model_dump(exclude={"action"})) # Convert to regular event
    id = event_id or uuid4().hex[:8]  # event_id lets tests seed known ids

    query = """
    INSERT INTO events (id, title, start_day_time, end_day_time, location)
    VALUES (?, ?, ?, ?, ?)
    """
    
    connection = get_connection()
    connection.execute(query, (id, event.title, event.start_day_time.isoformat(), 
                               event.end_day_time.isoformat() if event.end_day_time else None, event.location))
    close_connection(connection)
    return id

def list_events() -> dict[str, Event]:

    query = "SELECT * FROM events ORDER BY start_day_time"
    connection = get_connection()
    rows = connection.execute(query).fetchall()
    result = {row["id"]: _row_to_event(row) for row in rows}

    close_connection(connection) 
    return result

def events_near(now: datetime, days_back: int = 1, days_ahead: int = 14) -> dict[str, Event]:
    lo, hi = now - timedelta(days=days_back), now + timedelta(days=days_ahead)

    connection = get_connection()
    query = """
    SELECT * FROM events
    WHERE start_day_time BETWEEN ? and ?
    ORDER BY start_day_time
    """

    rows = connection.execute(query, (lo.isoformat(), hi.isoformat()))
    result = {row['id']: _row_to_event(row) for row in rows}

    close_connection(connection)
    return result

def format_for_prompt(candidates: dict[str, Event]) -> str:
    if not candidates:
        return "(no events)"

    lines = []
    # candidates come from events_near, which is already ordered by start time
    for id, event in candidates.items():
        lines.append(f"{event.start_day_time:%Y-%m-%d %H:%M (%A)} | {event.title} | id={id}")
    return "\n".join(lines)

def _row_to_event(row) -> Event:

    return Event(title=row['title'], 
                 start_day_time=row['start_day_time'], 
                 end_day_time=row['end_day_time'], 
                 location=row['location'])