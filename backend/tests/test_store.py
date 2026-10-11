from datetime import datetime, timedelta, timezone

from app import store
from app.models import AddEvent, Event

NOW = datetime(2026, 10, 5, 9, 0)

def make_event(title="Dentist", start=datetime(2026, 10, 6, 10, 0), **kwargs) -> Event:
    return Event(title=title, start_day_time=start, **kwargs)

def test_add_returns_id_and_event_is_listed():
    event_id = store.add_event(make_event("Dentist"))

    events = store.list_events()
    assert list(events) == [event_id]
    assert events[event_id].title == "Dentist"
    assert events[event_id].start_day_time == datetime(2026, 10, 6, 10, 0)

def test_generated_ids_are_unique():
    ids = {store.add_event(make_event()) for _ in range(20)}
    assert len(ids) == 20 # if not 20 -> some ids are dupes!

def test_optional_fields_default_to_none():
    event_id = store.add_event(make_event())

    stored = store.list_events()[event_id]
    assert stored.end_day_time is None
    assert stored.location is None

def test_add_accepts_llm_add_event():
    event_id = store.add_event(AddEvent(title="Bowling", start_day_time=datetime(2026, 10, 8, 18, 0)))

    assert store.list_events()[event_id].title == "Bowling"

def test_timezone_aware_datetime_is_stored_naive():
    aware = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    event_id = store.add_event(make_event(start=aware))

    stored = store.list_events()[event_id]
    assert stored.start_day_time.tzinfo is None
    assert stored.start_day_time == aware.astimezone().replace(tzinfo=None)

def test_list_is_ordered_by_start_time():
    store.add_event(make_event("late", datetime(2026, 10, 9, 9, 0)), "late")
    store.add_event(make_event("early", datetime(2026, 10, 6, 9, 0)), "early")
    store.add_event(make_event("mid", datetime(2026, 10, 7, 9, 0)), "mid")

    assert list(store.list_events()) == ["early", "mid", "late"]

def test_list_empty():
    assert store.list_events() == {}

# remove

def test_remove_returns_event_and_deletes_it():
    event_id = store.add_event(make_event("Dentist"))

    removed = store.remove_event(event_id)

    assert removed is not None
    assert removed.title == "Dentist"
    assert store.list_events() == {}

def test_remove_unknown_id_returns_none():
    assert store.remove_event("nope") is None

def test_remove_leaves_other_events():
    keep = store.add_event(make_event("keep"))
    drop = store.add_event(make_event("drop"))

    store.remove_event(drop)

    assert list(store.list_events()) == [keep]

def test_remove_twice_second_returns_none():
    event_id = store.add_event(make_event())

    assert store.remove_event(event_id) is not None
    assert store.remove_event(event_id) is None

# clear

def test_clear_store_removes_everything():
    store.add_event(make_event("a"))
    store.add_event(make_event("b"))

    store.clear_store()

    assert store.list_events() == {}

# events_near (default window: 1 day back, 14 days ahead)

def test_events_near_includes_events_inside_window():
    inside = store.add_event(make_event("inside", NOW + timedelta(days=3)))

    assert list(store.events_near(NOW)) == [inside]

def test_events_near_excludes_events_outside_window():
    store.add_event(make_event("too old", NOW - timedelta(days=2)))
    store.add_event(make_event("too far", NOW + timedelta(days=15)))

    assert store.events_near(NOW) == {}

def test_events_near_ordered_by_start_time():
    store.add_event(make_event("c", NOW + timedelta(days=5)), "c")
    store.add_event(make_event("a", NOW + timedelta(days=1)), "a")
    store.add_event(make_event("b", NOW + timedelta(days=3)), "b")

    assert list(store.events_near(NOW)) == ["a", "b", "c"]

def test_events_near_across_month_and_year_boundary():
    now = datetime(2026, 12, 30, 9, 0)
    jan = store.add_event(make_event("new year", datetime(2027, 1, 2, 9, 0)))
    store.add_event(make_event("too far", datetime(2027, 1, 20, 9, 0)))

    assert list(store.events_near(now)) == [jan]

def test_format_for_prompt_is_correct_formating():
    # since in parse.py the candidates come from events_near which is already sorted,
    # we only need to look at the formating and not the sorting
    event = make_event("Dentist")
    id = store.add_event(event)
    # Date first (with weekday), then title, then id
    assert store.format_for_prompt({id: event}) == f"2026-10-06 10:00 (Tuesday) | Dentist | id={id}"

def test_format_for_prompt_empty():
    assert store.format_for_prompt({}) == "(no events)"

def test_format_for_prompt_one_line_per_event_in_given_order():
    a = make_event("Standup", datetime(2026, 10, 7, 9, 0))
    b = make_event("Standup", datetime(2026, 10, 8, 9, 0))

    # Same title on different days: the date is what tells them apart
    assert store.format_for_prompt({"s1": a, "s2": b}) == (
        "2026-10-07 09:00 (Wednesday) | Standup | id=s1\n"
        "2026-10-08 09:00 (Thursday) | Standup | id=s2"
    )