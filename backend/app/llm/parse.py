from datetime import datetime

from app import store
from app.models import CalendarCommand
from app.date_utils import generate_next_n_days
from app.llm.providers import get_provider

PROMPT_LLM ="""You turn a natural language calendar request into a structured command.

Command rules:
- Use "add" when the user wants to create an event. Use "remove" when they want to cancel or delete one.
- Use "update" when the user wants to change an existing event (for example "move", "reschedule", "rename", "change", "push back").
- For remove and update, set event_id to the id of the matching event below, or null if nothing matches.
- For update, only set the fields the user wants changed and leave every other field null. If the user only changes the start time, leave end_day_time null (the end moves with the start automatically).
- When adding, if no end time is given, set end_day_time to null.
- Example: "move dentist to Friday 3pm" is an update with the dentist's event_id, start_day_time set to Friday 15:00, and title, end_day_time and location all null.

Existing events:
{events}

Date rules:
- If the user names a weekday, find that weekday in the lookup table below and copy its date exactly. Do not calculate dates yourself.
- "today" and "tomorrow" are marked in the list below.
- If the user gives a specific date (for example "October 24"), use that date.
- A weekday name always means the date listed for it below, even when it is today's weekday (the list maps that to next week). Only use today's date if the user says "today" or "tonight".
- Never schedule or move an event to a time that has already passed.
- If a time has no am/pm, choose the more likely one for that kind of event (for example "lunch at 1" is 13:00, "breakfast at 8" is 08:00).
- For remove and update, only pick an event whose title matches what the user is referring to. If no event title matches, event_id must be null. Never pick an unrelated event.

The current date and time is: {now}
Date lookup:
{generated_week}
"""

def parse_command(session_id: str, text: str, now: datetime | None = None) -> CalendarCommand:
    now = now or datetime.now()
    week = generate_next_n_days(now, 7)
    candidates = store.events_near(session_id, now)
    prompt = PROMPT_LLM.format(now=f"{now:%Y-%m-%d %H:%M (%A)}",
                                events=store.format_for_prompt(candidates),
                                generated_week=week,
                                )
    return get_provider().parse(prompt, text, CalendarCommand, {'valid_ids': set(candidates)})
