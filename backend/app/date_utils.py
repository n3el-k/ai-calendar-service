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
    days_ahead = (weekday - today.weekday()) % 7
    return today.date() + timedelta(days=days_ahead)

def generate_week(today: datetime) -> str:
    # Generates starting at now, formates for the llm output
    lines = []
    for i in range(7):
        day = today.date() + timedelta(days=i)
        label = " (today)" if i == 0 else " (tomorrow)" if i == 1 else ""
        lines.append(f"- {day:%A}: {day:%Y-%m-%d}{label}")
    return "\n".join(lines)