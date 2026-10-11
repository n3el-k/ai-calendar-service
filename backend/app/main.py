from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from instructor import exceptions
from anthropic import APIError as AnthropicAPIError
from openai import APIError as OpenAIAPIError
from dotenv import load_dotenv
import os

from app import store
from app.llm.parse import parse_command
from app.models import UserInput
from app.db import init_db

# Setup app
load_dotenv()
app = FastAPI()

# Setup db
init_db()
if os.getenv("RESET_DB_ON_START", "").lower() in ("1", "true", "yes"):
    store.clear_store()

# Exception functions
@app.exception_handler(exceptions.InstructorRetryException)
async def llm_retry_handler(request: Request, exc: exceptions.InstructorRetryException):
    return JSONResponse(status_code=502, content={"detail": "LLM exceeded retry limit"})

@app.exception_handler(AnthropicAPIError)
@app.exception_handler(OpenAIAPIError)
async def llm_api_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=502, content={"detail": "LLM provider error"})

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
