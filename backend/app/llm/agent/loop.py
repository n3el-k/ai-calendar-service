from functools import lru_cache
from anthropic import Anthropic
from anthropic.types import MessageParam, ToolResultBlockParam
from datetime import datetime

from app.config import settings
from app.store import get_pending
from app.llm.agent.tools import TOOLS, run_tool
from app.date_utils import generate_next_n_days

MAX_STEPS = 8

@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    return Anthropic()

PROMPT = """You manage the user's calendar using the tools provided.

Rules:
- To change or remove an event, call search_events first to find it and get its id. Never guess an id.
- Only change or remove events the user clearly meant. If the search finds several plausible matches and the request is ambiguous, ask the user instead of picking one.
- For update_event, only include the fields that change. If only the start time changes, leave out end_day_time (the end moves with the start).
- When adding, leave out end_day_time if the user gave no end time.
- If a tool result says NOT SAVED, the change is waiting for the user to confirm it with the buttons. Say so in your reply; never claim it was saved.
- If a tool returns an error, read it, fix your call and try again.
- When you are done, reply with one or two plain sentences saying what you changed.

Date rules:
- If the user names a weekday, find that weekday in the lookup table below and copy its date exactly. Do not calculate dates yourself.
- "today" and "tomorrow" are marked in the list below.
- If the user gives a specific date (for example "October 24"), use that date.
- A weekday name always means the date listed for it below, even when it is today's weekday (the list maps that to next week). Only use today's date if the user says "today" or "tonight".
- Never schedule or move an event to a time that has already passed.
- If a time has no am/pm, choose the more likely one for that kind of event (for example "lunch at 1" is 13:00, "breakfast at 8" is 08:00).
- If no event matches what the user means, don't call update_event or remove_event; tell the user instead. Never pick an unrelated event.

The current date and time is: {now}
Date lookup:
{generated_week} """

def run_agent(sid: str, text, now=None) -> dict:
    
    now = now or datetime.now()
    system = PROMPT.format(
        now=f"{now:%Y-%m-%d %H:%M (%A)}",
        generated_week=generate_next_n_days(now, 7)
    )
    messages: list[MessageParam] = [{"role": "user", "content": text}]
    actions = []
    reply = ""
    truncated = True

    for _ in range(MAX_STEPS):
        response = get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            system=system,
            tools=TOOLS,
            messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})

        # check if stop
        if response.stop_reason == "end_turn":
            reply = "".join(block.text for block in response.content if block.type=='text')
            truncated = False
            break
        elif response.stop_reason != "tool_use":

            reply = "Could not finish the request. Some changes may have been made to the calendar"
            truncated = False
            break

        # otherwise run tools
        results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(sid, block)
                results.append(result)
                actions.append({"tool": block.name, "input": block.input, "is_error": result.get("is_error", False)})
        messages.append({"role": "user", "content": results})

    return {
        "reply": reply,
        "truncated": truncated,
        "actions": actions,
        "pending": get_pending(sid)
    }