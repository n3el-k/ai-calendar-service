from datetime import datetime, timedelta, date
from enum import IntEnum

class Weekdays(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

def next_weekday(today: datetime, weekday: Weekdays) -> date:
    days_ahead = (weekday - today.weekday()) % 7 or 7  # today's weekday means next week
    return today.date() + timedelta(days=days_ahead)

def generate_next_n_days(today: datetime, n: int) -> str:
    # Lookup table for the llm: today on its own line, then each weekday's NEXT date (tomorrow to today + n),
    # so a weekday name always maps to exactly one date and today's weekday points to next week
    lines = [f"- Today: {today.date():%Y-%m-%d} ({today:%A})"]
    for i in range(1, n + 1):
        day = today.date() + timedelta(days=i)
        label = " (tomorrow)" if i == 1 else ""
        lines.append(f"- {day:%A}: {day:%Y-%m-%d}{label}")
    return "\n".join(lines)