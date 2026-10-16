from datetime import datetime, timedelta, timezone

from app import db, store
import pytest
from pydantic import ValidationError

from app.models import AddEvent, Event, UpdateEvent

NOW = datetime(2026, 10, 5, 9, 0)
SESSION = "test-session"
OTHER = "other-session"

def make_event(title="Dentist", start=datetime(2026, 10, 6, 10, 0), **kwargs) -> Event:
    return Event(title=title, start_day_time=start, **kwargs)

def test_add_returns_id_and_event_is_listed():
    event_id = store.insert_event(SESSION, make_event("Dentist"))

    events = store.list_events(SESSION)
    assert list(events) == [event_id]
    assert events[event_id].title == "Dentist"
    assert events[event_id].start_day_time == datetime(2026, 10, 6, 10, 0)

def test_generated_ids_are_unique():
    ids = {store.insert_event(SESSION, make_event()) for _ in range(20)}
    assert len(ids) == 20 # if not 20 -> some ids are dupes!

def test_optional_fields_default_to_none():
    event_id = store.insert_event(SESSION, make_event())

    stored = store.list_events(SESSION)[event_id]
    assert stored.end_day_time is None
    assert stored.location is None

def test_add_accepts_llm_add_event():
    event_id = store.insert_event(SESSION, AddEvent(title="Bowling", start_day_time=datetime(2026, 10, 8, 18, 0)))

    assert store.list_events(SESSION)[event_id].title == "Bowling"

def test_timezone_aware_datetime_is_stored_naive():
    aware = datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc)
    event_id = store.insert_event(SESSION, make_event(start=aware))

    stored = store.list_events(SESSION)[event_id]
    assert stored.start_day_time.tzinfo is None
    assert stored.start_day_time == aware.astimezone().replace(tzinfo=None)

def test_list_is_ordered_by_start_time():
    store.insert_event(SESSION, make_event("late", datetime(2026, 10, 9, 9, 0)), "late")
    store.insert_event(SESSION, make_event("early", datetime(2026, 10, 6, 9, 0)), "early")
    store.insert_event(SESSION, make_event("mid", datetime(2026, 10, 7, 9, 0)), "mid")

    assert list(store.list_events(SESSION)) == ["early", "mid", "late"]

def test_list_empty():
    assert store.list_events(SESSION) == {}

# remove

def test_remove_returns_event_and_deletes_it():
    event_id = store.insert_event(SESSION, make_event("Dentist"))

    removed = store.remove_event(SESSION, event_id)

    assert removed is not None
    assert removed.title == "Dentist"
    assert store.list_events(SESSION) == {}

def test_remove_unknown_id_returns_none():
    assert store.remove_event(SESSION, "nope") is None

def test_remove_leaves_other_events():
    keep = store.insert_event(SESSION, make_event("keep"))
    drop = store.insert_event(SESSION, make_event("drop"))

    store.remove_event(SESSION, drop)

    assert list(store.list_events(SESSION)) == [keep]

def test_remove_twice_second_returns_none():
    event_id = store.insert_event(SESSION, make_event())

    assert store.remove_event(SESSION, event_id) is not None
    assert store.remove_event(SESSION, event_id) is None

# clear

def test_clear_store_removes_everything():
    store.insert_event(SESSION, make_event("a"))
    store.insert_event(SESSION, make_event("b"))

    store.clear_store(SESSION)

    assert store.list_events(SESSION) == {}

# search_events (seed: dentist 14:00-16:00, date 15:00-17:00, same day)

def _seed_search():
    day = datetime(2026, 10, 16)
    store.insert_event(SESSION, make_event("Dentist appointment", day.replace(hour=14),
                                           end_day_time=day.replace(hour=16)), "dentist")
    store.insert_event(SESSION, make_event("Date with Sam", day.replace(hour=15),
                                           end_day_time=day.replace(hour=17)), "date")

def test_search_by_name_is_case_insensitive():
    _seed_search()

    assert list(store.search_events(SESSION, query="dentist")) == ["dentist"]

@pytest.mark.parametrize("start, end, expected", [
    # start and end
    (datetime(2026, 10, 16), datetime(2026, 10, 17), ["dentist", "date"]),
    (datetime(2026, 10, 17), datetime(2026, 10, 18), []),
    # just start (inclusive)
    (datetime(2026, 10, 16, 15), None, ["date"]),
    (datetime(2026, 10, 17), None, []),
    # just end (exclusive: the date starting at 15:00 is not included)
    (None, datetime(2026, 10, 16, 15), ["dentist"]),
    (None, datetime(2026, 10, 16, 14), []),
])
def test_search_by_range(start, end, expected):
    _seed_search()

    assert list(store.search_events(SESSION, start_time=start, end_time=end)) == expected

def test_search_never_returns_other_sessions_events():
    _seed_search()
    store.insert_event(OTHER, make_event("Dentist appointment", datetime(2026, 10, 16, 14)), "theirs")

    assert "theirs" not in store.search_events(SESSION, query="dentist")

# events_near (default window: 1 day back, 14 days ahead)

def test_events_near_includes_events_inside_window():
    inside = store.insert_event(SESSION, make_event("inside", NOW + timedelta(days=3)))

    assert list(store.events_near(SESSION, NOW)) == [inside]

def test_events_near_excludes_events_outside_window():
    store.insert_event(SESSION, make_event("too old", NOW - timedelta(days=2)))
    store.insert_event(SESSION, make_event("too far", NOW + timedelta(days=15)))

    assert store.events_near(SESSION, NOW) == {}

def test_events_near_ordered_by_start_time():
    store.insert_event(SESSION, make_event("c", NOW + timedelta(days=5)), "c")
    store.insert_event(SESSION, make_event("a", NOW + timedelta(days=1)), "a")
    store.insert_event(SESSION, make_event("b", NOW + timedelta(days=3)), "b")

    assert list(store.events_near(SESSION, NOW)) == ["a", "b", "c"]

def test_events_near_across_month_and_year_boundary():
    now = datetime(2026, 12, 30, 9, 0)
    jan = store.insert_event(SESSION, make_event("new year", datetime(2027, 1, 2, 9, 0)))
    store.insert_event(SESSION, make_event("too far", datetime(2027, 1, 20, 9, 0)))

    assert list(store.events_near(SESSION, now)) == [jan]

def test_format_for_prompt_is_correct_formating():
    # since in parse.py the candidates come from events_near which is already sorted,
    # we only need to look at the formating and not the sorting
    event = make_event("Dentist")
    id = store.insert_event(SESSION, event)
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

# conflicts

def test_conflicts_same_day_overlap_without_exclude_id():
    store.insert_event(SESSION, make_event("Dentist", datetime(2026, 10, 6, 15, 0),
                                        end_day_time=datetime(2026, 10, 6, 16, 0)), "dentist")
    new = make_event("Team sync", datetime(2026, 10, 6, 15, 30),
                     end_day_time=datetime(2026, 10, 6, 16, 30))

    conflicts = store.find_conflicts(SESSION, new)

    assert list(conflicts) == ["dentist"]

def test_conflicts_back_to_back_is_not_a_conflict():
    store.insert_event(SESSION, make_event("Dentist", datetime(2026, 10, 6, 15, 0),
                                        end_day_time=datetime(2026, 10, 6, 16, 0)), "dentist")
    gym = make_event("Gym", datetime(2026, 10, 6, 16, 0),
                     end_day_time=datetime(2026, 10, 6, 17, 0))

    assert store.find_conflicts(SESSION, gym) == {}

# pending (held conflicting adds and updates)

def test_pending_round_trip():
    store.set_pending(SESSION, "add", None, make_event("Gym", datetime(2026, 10, 6, 15, 30)))
    pending = store.get_pending(SESSION)
    assert pending is not None
    assert pending["action"] == "add"
    assert pending["event"].title == "Gym"

    confirmed = store.confirm_pending(SESSION)

    assert confirmed is not None
    assert confirmed["action"] == "add"
    assert store.list_events(SESSION)[confirmed["id"]].title == "Gym"
    assert store.get_pending(SESSION) is None

def test_set_pending_replaces_previous():
    store.set_pending(SESSION, "add", None, make_event("Gym"))
    store.set_pending(SESSION, "add", None, make_event("Swim"))

    pending = store.get_pending(SESSION)
    assert pending is not None
    assert pending["event"].title == "Swim"

def test_add_without_conflict_is_added():
    result = store.add_event(SESSION, AddEvent(title="Gym", start_day_time=datetime(2026, 10, 6, 15, 0)))

    assert result["status"] == "added"
    assert store.list_events(SESSION)[result["id"]].title == "Gym"
    assert store.get_pending(SESSION) is None

def test_conflicting_add_is_held_not_added():
    store.insert_event(SESSION, make_event("Dentist", datetime(2026, 10, 6, 15, 0),
                                           end_day_time=datetime(2026, 10, 6, 16, 0)), "dentist")

    result = store.add_event(SESSION, AddEvent(title="Gym", start_day_time=datetime(2026, 10, 6, 15, 30)))

    assert result["status"] == "needs_confirmation"
    assert list(result["conflicts"]) == ["dentist"]
    assert list(store.list_events(SESSION)) == ["dentist"]
    pending = store.get_pending(SESSION)
    assert pending is not None
    assert pending["event"].title == "Gym"

def test_conflicting_update_is_held_then_confirmed():
    store.insert_event(SESSION, make_event("Dentist", datetime(2026, 10, 6, 10, 0),
                                        end_day_time=datetime(2026, 10, 6, 11, 0)), "dentist")
    store.insert_event(SESSION, make_event("Gym", datetime(2026, 10, 6, 15, 0),
                                        end_day_time=datetime(2026, 10, 6, 16, 0)), "gym")

    result = store.update_event(SESSION, "dentist",
                                UpdateEvent(event_id="dentist", start_day_time=datetime(2026, 10, 6, 15, 30)))

    assert result is not None
    assert result["status"] == "needs_confirmation"
    assert list(result["conflicts"]) == ["gym"]
    assert store.list_events(SESSION)["dentist"].start_day_time == datetime(2026, 10, 6, 10, 0)

    assert store.confirm_pending(SESSION) == {"action": "update", "id": "dentist"}

    events = store.list_events(SESSION)
    assert len(events) == 2  # moved, not copied
    assert events["dentist"].start_day_time == datetime(2026, 10, 6, 15, 30)

def test_confirm_held_update_of_deleted_event_returns_none():
    store.set_pending(SESSION, "update", "gone", make_event("Dentist"))

    assert store.confirm_pending(SESSION) is None

# sessions: each session only sees and changes its own events

def test_list_only_returns_own_session_events():
    mine = store.insert_event(SESSION, make_event("mine"))
    theirs = store.insert_event(OTHER, make_event("theirs"))

    assert list(store.list_events(SESSION)) == [mine]
    assert list(store.list_events(OTHER)) == [theirs]

def test_events_near_only_returns_own_session_events():
    mine = store.insert_event(SESSION, make_event("mine", NOW + timedelta(days=1)))
    store.insert_event(OTHER, make_event("theirs", NOW + timedelta(days=1)))

    assert list(store.events_near(SESSION, NOW)) == [mine]

def test_remove_cannot_delete_other_sessions_event():
    theirs = store.insert_event(OTHER, make_event("theirs"))

    assert store.remove_event(SESSION, theirs) is None
    assert list(store.list_events(OTHER)) == [theirs]

def test_clear_store_only_clears_own_session():
    store.insert_event(SESSION, make_event("mine"))
    theirs = store.insert_event(OTHER, make_event("theirs"))

    store.clear_store(SESSION)

    assert store.list_events(SESSION) == {}
    assert list(store.list_events(OTHER)) == [theirs]

def test_clear_all_clears_every_session():
    store.insert_event(SESSION, make_event("mine"))
    store.insert_event(OTHER, make_event("theirs"))

    store.clear_all()

    assert store.list_events(SESSION) == {}
    assert store.list_events(OTHER) == {}

# touch_session / delete_stale_sessions

def _last_seen(session_id):
    connection = db.get_connection()
    row = connection.execute("SELECT last_seen FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    db.close_connection(connection)
    return row["last_seen"] if row else None

def _set_last_seen(session_id, when: datetime):
    connection = db.get_connection()
    connection.execute("UPDATE sessions SET last_seen = ? WHERE session_id = ?", (when.isoformat(), session_id))
    db.close_connection(connection)

def test_touch_session_creates_then_updates_row():
    store.touch_session(SESSION)
    _set_last_seen(SESSION, datetime(2000, 1, 1))

    store.touch_session(SESSION)

    last_seen = _last_seen(SESSION)
    assert last_seen is not None
    assert last_seen > datetime(2000, 1, 1).isoformat()

def test_delete_stale_sessions_removes_old_session_and_its_events():
    store.touch_session(SESSION)
    store.insert_event(SESSION, make_event("old"))
    _set_last_seen(SESSION, datetime.now() - timedelta(days=10))

    store.delete_stale_sessions(7)

    assert _last_seen(SESSION) is None
    assert store.list_events(SESSION) == {}

def test_delete_stale_sessions_keeps_recent_session():
    store.touch_session(OTHER)
    kept = store.insert_event(OTHER, make_event("recent"))
    store.touch_session(SESSION)
    store.insert_event(SESSION, make_event("old"))
    _set_last_seen(SESSION, datetime.now() - timedelta(days=10))

    store.delete_stale_sessions(7)

    assert list(store.list_events(OTHER)) == [kept]
    assert _last_seen(OTHER) is not None

# update_event

def _seed(**kwargs) -> str:
    return store.insert_event(SESSION, make_event(**kwargs), "e1")

def test_update_changes_only_given_fields():
    _seed(location="Clinic", end_day_time=datetime(2026, 10, 6, 11, 0))

    result = store.update_event(SESSION, "e1", UpdateEvent(event_id="e1", title="Checkup"))
    assert result is not None
    updated = result["event"]

    assert updated.title == "Checkup"
    assert updated.start_day_time == datetime(2026, 10, 6, 10, 0)
    assert updated.end_day_time == datetime(2026, 10, 6, 11, 0)
    assert updated.location == "Clinic"
    assert store.list_events(SESSION)["e1"] == updated

def test_update_unknown_id_returns_none():
    assert store.update_event(SESSION, "nope", UpdateEvent(event_id="nope", title="x")) is None

def test_update_cannot_change_other_sessions_event():
    _seed()

    result = store.update_event(OTHER, "e1", UpdateEvent(event_id="e1", title="Hacked"))

    assert result is None
    assert store.list_events(SESSION)["e1"].title == "Dentist"

def test_update_start_shifts_end_by_same_amount():
    _seed(end_day_time=datetime(2026, 10, 6, 11, 30))

    result = store.update_event(SESSION, "e1", UpdateEvent(event_id="e1", start_day_time=datetime(2026, 10, 8, 15, 0)))
    assert result is not None
    updated = result["event"]

    assert updated.start_day_time == datetime(2026, 10, 8, 15, 0)
    assert updated.end_day_time == datetime(2026, 10, 8, 16, 30)

def test_update_start_without_existing_end_leaves_end_none():
    _seed()

    result = store.update_event(SESSION, "e1", UpdateEvent(event_id="e1", start_day_time=datetime(2026, 10, 8, 15, 0)))
    assert result is not None
    updated = result["event"]

    assert updated.end_day_time is None

def test_update_explicit_end_is_not_shifted():
    _seed(end_day_time=datetime(2026, 10, 6, 11, 0))

    result = store.update_event(SESSION, "e1", UpdateEvent(
        event_id="e1", start_day_time=datetime(2026, 10, 8, 15, 0), end_day_time=datetime(2026, 10, 8, 18, 0)))
    assert result is not None
    updated = result["event"]

    assert updated.end_day_time == datetime(2026, 10, 8, 18, 0)

def test_update_end_before_existing_start_raises_and_row_unchanged():
    _seed()

    with pytest.raises(ValidationError):
        store.update_event(SESSION, "e1", UpdateEvent(event_id="e1", end_day_time=datetime(2026, 10, 6, 9, 0)))

    stored = store.list_events(SESSION)["e1"]
    assert stored.end_day_time is None
    assert stored.start_day_time == datetime(2026, 10, 6, 10, 0)

def test_update_timezone_aware_start_is_stored_naive():
    _seed()
    aware = datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc)

    store.update_event(SESSION, "e1", UpdateEvent(event_id="e1", start_day_time=aware))

    assert store.list_events(SESSION)["e1"].start_day_time.tzinfo is None
