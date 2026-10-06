from datetime import datetime, timedelta
from uuid import uuid4
from app.models import Event

# In-memory store keyed by event id; swap for a database later.
events: dict[str, Event] = {}

def remove_event(event_id: str) -> Event | None:
    return events.pop(event_id, None)

def add_event(event: Event) -> str:
    # The event being passed in is a models.AddEvent as that is what the LLM outputs.
    event = Event(**event.model_dump(exclude={"action"})) # Convert to regular event
    id = uuid4().hex[:8]
    events[id] = event
    return id

def list_events() -> dict[str, Event]:
    return dict(sort_daytime(events)) 

def events_near(now: datetime, days_back: int = 1, days_ahead: int = 14) -> dict[str, Event]:
    lo, hi = now - timedelta(days=days_back), now + timedelta(days=days_ahead)
    return {
        event_id: e 
        for event_id, e in events.items()
        if lo <= e.start_day_time <= hi
    }

def format_for_prompt(candidates: dict[str, Event]) -> str:
    if not candidates:
        return "(no events)"

    lines = []
    for id, event, in sort_daytime(candidates):
        lines.append(f"{event.start_day_time:%Y-%m-%d %H:%M (%A)} | {event.title} | id={id}")
    return "\n".join(lines)

def sort_daytime(events: dict[str, Event]) -> list[tuple[str, Event]]:
    # Append tuple of start time, event id
    list_by_start_time = []
    for id, event in events.items():
        list_by_start_time.append((event.start_day_time, id))
    list_by_start_time.sort() # Sort by time

    result = []
    for time, id in list_by_start_time:
        result.append((id, events[id]))
    return result
