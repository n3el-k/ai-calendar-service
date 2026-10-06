from app.date_utils import generate_week, next_weekday, Weekdays
from datetime import date, datetime

def test_next_occurance_weekday():
    assert next_weekday(datetime(2026, 10, 5, 9, 0, 0, 0), Weekdays.THURSDAY) == date(2026, 10, 8)
    assert next_weekday(datetime(2026, 10, 7, 9, 0, 0, 0), Weekdays.SUNDAY) == date(2026, 10, 11)
    assert next_weekday(datetime(2026, 10, 9, 9, 0, 0, 0), Weekdays.MONDAY) == date(2026, 10, 12)
    assert next_weekday(datetime(2026, 10, 9, 9, 0, 0, 0), Weekdays.FRIDAY) == date(2026, 10, 9)  

def same_weekday_returns_today():
    assert next_weekday(datetime(2026, 10, 9, 9, 0, 0, 0), Weekdays.FRIDAY) == date(2026, 10, 9)
    assert next_weekday(datetime(2027, 1, 1, 9, 0, 0, 0), Weekdays.FRIDAY) == date(2027, 1, 1)

def test_generate_week():
    assert generate_week(datetime(2026, 10, 7, 9, 0, 0, 0)) == (
        "- Wednesday: 2026-10-07 (today)\n"
        "- Thursday: 2026-10-08 (tomorrow)\n"
        "- Friday: 2026-10-09\n"
        "- Saturday: 2026-10-10\n"
        "- Sunday: 2026-10-11\n"
        "- Monday: 2026-10-12\n"
        "- Tuesday: 2026-10-13"
    )

def test_generate_week_crosses_year_boundary():
    lines = generate_week(datetime(2026, 12, 30, 9, 0, 0, 0)).splitlines()
    assert lines[0] == "- Wednesday: 2026-12-30 (today)"
    assert lines[2] == "- Friday: 2027-01-01"
    assert lines[-1] == "- Tuesday: 2027-01-05"
