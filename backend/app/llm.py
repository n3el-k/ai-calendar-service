import os
from datetime import datetime

import instructor
from openai import OpenAI

from app import store
from app.models import CalendarCommand

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

client = instructor.from_openai(
    OpenAI(base_url=OLLAMA_URL, api_key="ollama"),
    mode=instructor.Mode.JSON
)

PROMPT_LLM ="""You turn a natural language calendar request into a structured command.
The current date and time is: {now}
Existing events in database: 
{events}

More rules:
- Choose add when user wants to add event to calendar. Otherwise remove
- When nothing in events matches the event_id, put null
- When no end_day_time given, put null
"""

def parse_command(text: str) -> CalendarCommand:

    now = datetime.now()
    candidates = store.events_near(now)
    prompt = PROMPT_LLM.format(now=f"{now:%Y-%m-%d %H:%M (%A)}", events=store.format_for_prompt(candidates))
    return client.chat.completions.create(
        model=OLLAMA_MODEL,
        response_model=CalendarCommand,
        context={"valid_ids": set(candidates)},
        max_retries=2,
        messages=[
            {"role":"system", "content":prompt},
            {"role":"user", "content":text}
        ]
    )