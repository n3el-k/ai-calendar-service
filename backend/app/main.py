from fastapi import FastAPI, HTTPException
from app import store
from app.llm import parse_command
from pydantic import BaseModel, Field

class UserInput(BaseModel):
    request: str

app = FastAPI()

@app.post("/command/")
def process_command(text_request: UserInput = Field(min_length=7)):
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
    if event_id in store.events:
        removed_event = store.remove_event(event_id)
        return {"removed_event": removed_event}
    raise HTTPException(404, "No event matches that request")
