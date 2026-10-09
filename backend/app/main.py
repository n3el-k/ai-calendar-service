from fastapi import FastAPI, HTTPException
from app import store
from app.llm.parse import parse_command
from app.models import UserInput
from app.db import init_db

# Setup app
app = FastAPI()
init_db()

# API Functons
@app.post("/command")
def process_command(text_request: UserInput):
    processed_command = parse_command(text_request.request)
    if processed_command.command.action == "add":
        id = store.add_event(processed_command.command)
        return {"id": id}
    
    # If remove, check if id is none
    if processed_command.command.event_id is None:
        raise HTTPException(404, "No event matches that request")

    removed_event = store.remove_event(processed_command.command.event_id)
    return {"removed_event": removed_event}

# Does not add to database, just used for checking without storing
@app.post("/parse")
def parse(text_request: UserInput):
    processed_command = parse_command(text_request.request)
    return processed_command.command

@app.get("/events")
def get_events():
    return store.list_events()

# For deleting manually without LLM. Need exact ID
@app.delete("/events/{event_id}")
def delete(event_id: str):
    removed_event = store.remove_event(event_id)
    if removed_event is None:
        raise HTTPException(404, "No event matches that request")
    return {"removed_event": removed_event}

# Reset: clears every event (the demo shares a single DB for the session)
@app.delete("/events")
def clear_events():
    store.clear_store()
    return {"cleared": True}
