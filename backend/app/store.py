from datetime import datetime, timedelta
from uuid import uuid4
import json

from app.models import Event, UpdateEvent
from app.db import get_connection, close_connection
from app.config import settings

def remove_event(session_id: str, event_id: str) -> Event | None:

    select_row_query = "SELECT * FROM events WHERE id = ? AND session_id = ?"
    delete_event_query = "DELETE FROM events WHERE id = ? AND session_id = ?"
    connection = get_connection()

    row = connection.execute(select_row_query, (event_id, session_id)) .fetchone()       
    connection.execute(delete_event_query, (event_id, session_id))
    close_connection(connection)
    
    if row:
        return _row_to_event(row)
    return None

def add_event(session_id: str, event: Event, event_id: str | None = None) -> str:    
    # The event being passed in is a models.AddEvent as that is what the LLM outputs.
    event = Event(**event.model_dump(exclude={"action"})) # Convert to regular event
    id = event_id or uuid4().hex[:8]  # event_id lets tests seed known ids

    query = """
    INSERT INTO events (id, title, start_day_time, end_day_time, location, session_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    connection = get_connection()
    connection.execute(query, (id, event.title, event.start_day_time.isoformat(), 
                               event.end_day_time.isoformat() if event.end_day_time else None, 
                               event.location, session_id))
    close_connection(connection)
    return id

def update_event(session_id: str, event_id: str, changes: UpdateEvent) -> Event | None:

    connection = get_connection()
    fetch_row_query = "SELECT * FROM events WHERE id = ? AND session_id = ?"
    row = connection.execute(fetch_row_query, (event_id, session_id)).fetchone()

    if row is None:
        close_connection(connection)
        return None
    event = _row_to_event(row)
    new_event = _merge_update(event, changes)

    update_event_query = """UPDATE events
    SET title=?, start_day_time=?, end_day_time=?, location=?
    WHERE id = ? AND session_id = ?
    """
    
    connection.execute(update_event_query, (
        new_event.title,
        new_event.start_day_time.isoformat(),
        new_event.end_day_time.isoformat() if new_event.end_day_time else None,
        new_event.location,
        event_id,
        session_id,
    ))
    close_connection(connection)

    return new_event

def list_events(session_id: str) -> dict[str, Event]:

    query = "SELECT * FROM events WHERE session_id = ? ORDER BY start_day_time"
    connection = get_connection()
    rows = connection.execute(query, (session_id,)).fetchall()
    result = {row["id"]: _row_to_event(row) for row in rows}

    close_connection(connection) 
    return result

def events_near(session_id: str, now: datetime, days_back: int = 1, days_ahead: int = 14) -> dict[str, Event]:
    lo, hi = now - timedelta(days=days_back), now + timedelta(days=days_ahead)

    connection = get_connection()
    query = """
    SELECT * FROM events
    WHERE session_id = ? AND
    start_day_time BETWEEN ? and ?
    ORDER BY start_day_time
    """

    rows = connection.execute(query, (session_id, lo.isoformat(), hi.isoformat()))
    result = {row['id']: _row_to_event(row) for row in rows}

    close_connection(connection)
    return result

def touch_session(session_id: str) -> None:
    # upsert function for last seen in sessions
    query = """
    INSERT INTO sessions (session_id, last_seen) VALUES (?,?)
    ON CONFLICT (session_id) DO UPDATE SET last_seen = excluded.last_seen
    """

    connection = get_connection()
    connection.execute(query, (session_id, datetime.now().isoformat()))
    close_connection(connection)

def delete_stale_sessions(num_days_cutoff: int) -> None:

    cutoff_datetime_str = (datetime.now() - timedelta(days=num_days_cutoff)).isoformat()

    connection = get_connection()
    delete_events_query = """DELETE FROM events WHERE session_id IN
    (SELECT session_id FROM sessions WHERE last_seen < ?)
    """
    delete_pending_query = """DELETE FROM pending_actions WHERE session_id IN
    (SELECT session_id FROM sessions WHERE last_seen < ?)
    """
    delete_sessions_query = "DELETE FROM sessions WHERE last_seen < ?"

    connection.execute(delete_events_query, (cutoff_datetime_str,))
    connection.execute(delete_pending_query, (cutoff_datetime_str,))
    connection.execute(delete_sessions_query, (cutoff_datetime_str,))
    close_connection(connection)

def find_conflicts(session_id: str, query_event: Event, exclude_id: str | None = None) -> dict[str, Event]:

    result = {}
    connection = get_connection()

    # Calculate projected end time for conflict detection
    default_duration = timedelta(minutes=settings.default_event_duration_minutes)
    projected_end = query_event.end_day_time or query_event.start_day_time + default_duration

    query = """
    SELECT * FROM events
    WHERE session_id = ? AND id IS NOT ? AND
    start_day_time < ? AND start_day_time >= ?
    """
    rows = connection.execute(query, (session_id, exclude_id, projected_end.isoformat(),
                               (query_event.start_day_time - timedelta(days=1)).isoformat())).fetchall()
    close_connection(connection)

    for row in rows:
        event = _row_to_event(row)
        end = event.end_day_time or event.start_day_time + default_duration
        if query_event.start_day_time < end and event.start_day_time < projected_end:
            # clash -> add to results
            result[row["id"]] = event
    return result

def set_pending(session_id: str, event: Event) -> None:

    # upsert
    connection = get_connection()
    query = """
    INSERT INTO pending_actions (session_id, event_json, created_at) VALUES (?, ?, ?)
    ON CONFLICT (session_id) DO UPDATE SET event_json = excluded.event_json, created_at = excluded.created_at
    """
    event_json = json.dumps({"action": "add", "event": event.model_dump(mode="json", exclude={"action"})})
    connection.execute(query, (session_id, event_json, datetime.now().isoformat()))
    close_connection(connection)

def get_pending(session_id: str) -> Event | None:

    connection = get_connection()
    row = connection.execute("SELECT event_json FROM pending_actions WHERE session_id = ?", (session_id,)).fetchone()
    close_connection(connection)
    if row is None:
        return None

    # load the json
    data = json.loads(row["event_json"])
    return Event.model_validate(data["event"])

def confirm_pending(session_id: str) -> str | None:

    connection = get_connection()

    row = connection.execute("DELETE FROM pending_actions WHERE session_id = ? RETURNING event_json",
                             (session_id,)).fetchone()
    close_connection(connection)

    if row is None:
        return None
    data = json.loads(row["event_json"])
    event = Event.model_validate(data["event"])
    if data['action'] == 'add':
        id = add_event(session_id, event)
        return id
    raise ValueError(f"unknown pending action {data['action']!r}")

def clear_pending(session_id: str) -> None:

    connection = get_connection()
    connection.execute("DELETE FROM pending_actions WHERE session_id = ?", (session_id,))
    close_connection(connection)

def clear_store(session_id: str) -> None:

    connection = get_connection()
    connection.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
    connection.execute("DELETE FROM pending_actions WHERE session_id = ?", (session_id,))
    close_connection(connection)

def clear_all() -> None:

    connection = get_connection()
    connection.execute("DELETE FROM events")
    connection.execute("DELETE FROM pending_actions")
    close_connection(connection)

# Helper functions
def format_for_prompt(candidates: dict[str, Event]) -> str:
    if not candidates:
        return "(no events)"

    lines = []
    # candidates come from events_near, which is already ordered by start time
    for id, event in candidates.items():
        lines.append(f"{event.start_day_time:%Y-%m-%d %H:%M (%A)} | {event.title} | id={id}")
    return "\n".join(lines)

def _merge_update(event: Event, changes: UpdateEvent) -> Event:

    changed_elem = changes.model_dump(exclude={"action", "event_id"}, exclude_none=True)

    # If start moved and no new end was given, shift end by the same amount
    new_start = changed_elem.get("start_day_time")
    if new_start and not changed_elem.get("end_day_time") and event.end_day_time:
        delta = new_start - event.start_day_time
        changed_elem["end_day_time"] = event.end_day_time + delta

    new_event = Event(**{**event.model_dump(), **changed_elem}) # This also checks start < end!
    
    return new_event

def _row_to_event(row) -> Event:

    return Event(title=row['title'], 
                 start_day_time=row['start_day_time'], 
                 end_day_time=row['end_day_time'], 
                 location=row['location'])