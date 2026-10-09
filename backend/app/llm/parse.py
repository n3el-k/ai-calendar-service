import os
from datetime import datetime

import instructor
from openai import OpenAI

from app import store
from app.models import CalendarCommand
from app.date_utils import generate_next_n_days
from app.llm.providers import get_provider

PROMPT_LLM ="""You turn a natural language calendar request into a structured command.

Command rules:
- Use "add" when the user wants to create an event. Use "remove" when they want to cancel or delete one.
- For remove, set event_id to the id of the matching event below, or null if nothing matches.
- If no end time is given, set end_day_time to null.

Existing events:
{events}

Date rules:
- If the user names a weekday, find that weekday in the lookup table below and copy its date exactly. Do not calculate dates yourself.
- "today" and "tomorrow" are marked in the list.
- If the user gives a specific date (for example "October 24"), use that date.
- Never use a date before today.
- For remove, only pick an event whose title matches what the user wants to cancel. If no event title matches, event_id must be null. Never pick an unrelated event.

The current date and time is: {now}
Next 7 days:
{generated_week}
"""

def parse_command(text: str, now: datetime | None = None) -> CalendarCommand:
    now = now or datetime.now()
    week = generate_next_n_days(now, 7)
    candidates = store.events_near(now)
    prompt = PROMPT_LLM.format(now=f"{now:%Y-%m-%d %H:%M (%A)}",
                                events=store.format_for_prompt(candidates),
                                generated_week=week,
                                )
    return get_provider().parse(prompt, text, CalendarCommand, {'valid_ids': set(candidates)})