import argparse
from enum import IntEnum, auto
from datetime import datetime, date, timedelta

from app.llm import parse_command
from app import store
from app.models import UserInput, CalendarCommand  
from app.date_utils import Weekdays, next_weekday

# 3 Goals:
# Test add, test remove, test correct date arithmetic

# Add and Date:
starting_datetimes: list[datetime] = [
    datetime(2026, 10, 5, 23, 13, 0, 0),
    datetime(2026, 10, 7, 23, 13, 0, 0),
    datetime(2026, 10, 9, 23, 13, 0, 0)
]

prompts: dict[str, Weekdays] = {
    "Lunch with Alex Friday 1pm": Weekdays.FRIDAY,
    "Bowling Thursday": Weekdays.THURSDAY,
    "Math midterm on Monday": Weekdays.MONDAY, 
}

def eval_dates():
    add_fails = 0
    date_fails = 0
    num_total = 0

    for now in starting_datetimes:
        for prompt in prompts:
            num_total += 1

            result = parse_command(prompt, now).command
            expected = next_weekday(now, prompts[prompt])
            # Check add
            if (result.action != "add"):
                add_fails += 1
                print(f"FAIL  now={now:%a %m-%d}  {prompt!r:32}  expected add, got {result.action}")
                continue
            elif (result.start_day_time.date() != expected):
                date_fails += 1
            mark = "PASS" if result.start_day_time.date() == expected else "FAIL"
            print(f"{mark}  now={now:%a %m-%d}  {prompt!r:32}  expected {expected:%a %m-%d}  got {result.start_day_time:%a %m-%d}")

    print(f"\n{num_total} cases | action fails: {add_fails} | date fails: {date_fails}")

def test():
    assert next_weekday(starting_datetimes[0], Weekdays.THURSDAY) == date(2026, 10, 8)
    assert next_weekday(starting_datetimes[1], Weekdays.SUNDAY) == date(2026, 10, 11)
    assert next_weekday(starting_datetimes[2], Weekdays.MONDAY) == date(2026, 10, 12)
    assert next_weekday(starting_datetimes[2], Weekdays.FRIDAY) == date(2026, 10, 9)  
    eval_dates()


if __name__ == "__main__":
    test()