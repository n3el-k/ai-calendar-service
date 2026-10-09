import argparse
import tempfile
from pathlib import Path
from datetime import datetime, date
from instructor.core.exceptions import InstructorRetryException 

from app.llm.parse import parse_command
from app import db, store
from app.models import Event
from app.date_utils import Weekdays, next_weekday

# 3 Goals:
# Test add, test remove, test correct date arithmetic

# Add and Date:
starting_datetimes: list[datetime] = [
    datetime(2026, 10, 5, 9, 0, 0, 0),
    datetime(2026, 10, 7, 9, 0, 0, 0),
    datetime(2026, 10, 9, 9, 0, 0, 0),
    datetime(2026, 12, 30, 9, 0, 0, 0),  # Wed, crosses into a new month and year
]

# One prompt per weekday, phrased differently
prompts: dict[str, Weekdays] = {
    "Lunch with Alex Friday 1pm": Weekdays.FRIDAY,
    "Bowling Thursday": Weekdays.THURSDAY,
    "Math midterm on Monday": Weekdays.MONDAY,
    "Dentist appointment Tuesday at 10am": Weekdays.TUESDAY,
    "Coffee with Sam on Wednesday morning": Weekdays.WEDNESDAY,
    "soccer game saturday 3pm": Weekdays.SATURDAY,
    "Add brunch with my parents this Sunday at 11": Weekdays.SUNDAY,
}

def eval_add_and_dates():
    add_fails = 0
    date_fails = 0
    num_total = 0
    print("TEST ADD + DATE\n")
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

# Test Remove
remove_now = datetime(2026, 10, 5, 9, 0) # Only need to set one date for remove test

seed: dict[str, Event] = {
    "dentist1": Event(title="Dentist appointment", start_day_time=datetime(2026, 10, 6, 10, 0)),  # Tue (tomorrow)
    "dinner1":  Event(title="Dinner with Alex",   start_day_time=datetime(2026, 10, 9, 19, 0)),  # Fri
    "standup1": Event(title="Team standup",        start_day_time=datetime(2026, 10, 7, 9, 0)),   # Wed
    "standup2": Event(title="Team standup",        start_day_time=datetime(2026, 10, 8, 9, 0)),   # Thu
    "call1":    Event(title="Call with mom",       start_day_time=datetime(2026, 10, 5, 18, 0)),  # Mon (today)
    "lunch1":   Event(title="Lunch with Alex",     start_day_time=datetime(2026, 10, 8, 12, 0)),  # Thu
    "gym1":     Event(title="Gym session",         start_day_time=datetime(2026, 10, 10, 8, 0)),  # Sat
    "flight1":  Event(title="Flight to Denver",    start_day_time=datetime(2026, 10, 14, 6, 30)), # Wed next week
}

remove_prompts: dict[str, str | None] = {
    "Cancel my dentist appointment": "dentist1",      # match by name
    "Remove dinner with Alex": "dinner1",
    "Cancel Wednesday's standup": "standup1",         # same title, pick by day
    "Delete the standup on Thursday": "standup2",
    "Cancel tomorrow's appointment": "dentist1",      # relative day
    "Cancel my haircut": None,                        # nothing matches
    "Cancel lunch with Alex": "lunch1",               # same person as dinner1, different event
    "Delete my dinner on Friday": "dinner1",
    "I can't make the call with mom tonight": "call1",  # indirect wording, "tonight" = today
    "Cancel my gym session on Saturday": "gym1",
    "Remove my flight next week": "flight1",
    "Cancel the meeting with my professor": None,
}

def use_temp_db():
    db.DB_PATH = Path(tempfile.mkdtemp()) / "eval.db"
    db.init_db()

def seed_events(events: dict[str, Event]):
    store.clear_store()
    for event_id, event in events.items():
        store.add_event(event, event_id)

def eval_remove():
    print("\nTEST REMOVE:\n")
    num_total = 0
    fails = 0
    seed_events(seed)
    for prompt in remove_prompts:
        num_total +=1
        try:
            result = parse_command(prompt, remove_now).command
        except InstructorRetryException as e:
            fails += 1 
            print(f"FAIL  prompt={prompt!r:32} no valid answer after {e.n_attempts} attempts")        
            continue
        mark = "PASS"
        # Check that action == "remove"
        if (result.action != "remove"):
            fails += 1
            print(f"FAIL prompt={prompt!r:32}  expected remove, got {result.action}")
            continue
        # If remove, check that the corresponding ID for the remove is the same as the seed
        elif (result.event_id != remove_prompts[prompt]):
            fails += 1
            mark="FAIL"
        print(f"{mark}  prompt={prompt!r:32}  expected_id={remove_prompts[prompt]} got={result.event_id}")
    print(f"\n{num_total} cases | remove fails: {fails}")
    
def test():

    parser = argparse.ArgumentParser(description="Eval parse_command")
    parser.add_argument("suite", nargs="?", default="all", choices=["all", "add", "remove"])
    args = parser.parse_args()

    use_temp_db()

    if (args.suite == "add"):
        eval_add_and_dates()
    elif(args.suite == "remove"):
        eval_remove()
    else:
        eval_add_and_dates()
        eval_remove()
if __name__ == "__main__":
    test()