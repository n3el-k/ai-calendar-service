import json
from typing import Any

from anthropic.types import ToolParam, ToolResultBlockParam
from pydantic import ValidationError
from pydantic_core import to_jsonable_python

from app import store
from app.models import AddEvent, RemoveEvent, SearchFilters, UpdateEvent

DATETIME_FORMAT = "YYYY-MM-DDTHH:MM in the user's local time, no timezone"

# no sid, will get from endpoint
TOOLS: list[ToolParam] = [
    {
        "name": "search_events",
        "description": "Find events in the user's calendar. All filters are optional and combine with AND; "
                       "no filters returns every event (up to 30, earliest first). "
                       "Always use this to get an event's id before updating or removing it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Case-insensitive keyword matched against event titles"},
                "start_time": {"type": "string", "description": f"Only events starting at or after this time. {DATETIME_FORMAT}"},
                "end_time": {"type": "string", "description": f"Only events starting before this time (exclusive). {DATETIME_FORMAT}"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_event",
        "description": "Create a new event. If it overlaps an existing event it is not saved; "
                       "it is held until the user confirms it themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the event"},
                "start_day_time": {"type": "string", "description": f"Start time. {DATETIME_FORMAT}"},
                "end_day_time": {"type": "string", "description": f"End time. Omit if the user gave none. {DATETIME_FORMAT}"},
                "location": {"type": "string", "description": "Where the event is. Omit if the user gave none"},
            },
            "required": ["title", "start_day_time"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_event",
        "description": "Change an existing event. Get the event_id from search_events first. "
                       "Only include the fields that change; omitted fields stay the same. "
                       "If only the start time changes, the end moves with it. "
                       "If the change overlaps another event it is not saved; it is held until the user confirms it themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "id of the event, from search_events"},
                "title": {"type": "string", "description": "New title"},
                "start_day_time": {"type": "string", "description": f"New start time. {DATETIME_FORMAT}"},
                "end_day_time": {"type": "string", "description": f"New end time. {DATETIME_FORMAT}"},
                "location": {"type": "string", "description": "New location"},
            },
            "required": ["event_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "remove_event",
        "description": "Delete an event permanently. Get the event_id from search_events first, "
                       "and only remove events the user clearly asked to remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "id of the event, from search_events"},
            },
            "required": ["event_id"],
            "additionalProperties": False,
        },
    },
]

class ToolError(Exception):
    """The tool ran but failed in a way the model should hear about (e.g. unknown id)."""

def _to_json(value: Any) -> str:
    # to_jsonable_python turns Events and datetimes into plain JSON (default=str would give reprs)
    return json.dumps(value, default=to_jsonable_python)

def _held_result(result: dict[str, Any], replaced_pending: bool) -> str:
    # A clash is not saved: the user has to confirm it with the buttons, the agent can't
    note = "NOT SAVED: this overlaps existing events. It is waiting for the user to confirm or cancel it. Tell the user."
    if replaced_pending:
        note += " It replaced an earlier change that was also waiting, so that one is no longer pending."
    return _to_json({**result, "note": note})

def handle_search_events(sid: str, tool_input: dict) -> str:

    filters = SearchFilters.model_validate(tool_input)
    events = store.search_events(sid, filters.query, filters.start_time, filters.end_time)

    if not events:
        return "No events found."
    return _to_json([{"id": event_id, **event.model_dump(mode="json")} for event_id, event in events.items()])

def handle_add_event(sid: str, tool_input: dict) -> str:

    validated_event = AddEvent.model_validate(tool_input)
    had_pending = store.get_pending(sid) is not None
    result = store.add_event(sid, validated_event)

    if result["status"] == "needs_confirmation":
        return _held_result(result, had_pending)
    return _to_json(result)

def handle_update_event(sid: str, tool_input: dict) -> str:

    changes = UpdateEvent.model_validate(tool_input)
    if changes.event_id is None:
        raise ToolError("event_id is required. Use search_events to find it.")

    had_pending = store.get_pending(sid) is not None
    result = store.update_event(sid, changes.event_id, changes)  # raises ValidationError if end < start

    if result is None:
        raise ToolError(f"No event with id {changes.event_id}. Use search_events to find it.")
    if result["status"] == "needs_confirmation":
        return _held_result(result, had_pending)
    return _to_json(result)

def handle_remove_event(sid: str, tool_input: dict) -> str:

    target = RemoveEvent.model_validate(tool_input)
    if target.event_id is None:
        raise ToolError("event_id is required. Use search_events to find it.")

    removed = store.remove_event(sid, target.event_id)

    if removed is None:
        raise ToolError(f"No event with id {target.event_id}. Use search_events to find it.")
    return _to_json({"status": "removed", "event": removed})

def run_tool(sid: str, block) -> ToolResultBlockParam:
    # Turns one tool_use block into its tool_result. Expected failures go back to the model
    # as is_error results so it can fix its call; anything else is a real bug and raises.
    handler = HANDLERS.get(block.name)
    try:
        if handler is None:
            raise ToolError(f"Unknown tool {block.name}")
        content, is_error = handler(sid, block.input), False
    except (ToolError, ValidationError) as e:
        content, is_error = str(e), True

    return {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error}

HANDLERS = {
    "search_events": handle_search_events,
    "add_event": handle_add_event,
    "update_event": handle_update_event,
    "remove_event": handle_remove_event,
}