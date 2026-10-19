from app.date_utils import generate_next_n_days, next_weekday, Weekdays
from datetime import date, datetime

def test_next_occurance_weekday():
    assert next_weekday(datetime(2026, 10, 5, 9, 0, 0, 0), Weekdays.THURSDAY) == date(2026, 10, 8)
    assert next_weekday(datetime(2026, 10, 7, 9, 0, 0, 0), Weekdays.SUNDAY) == date(2026, 10, 11)
    assert next_weekday(datetime(2026, 10, 9, 9, 0, 0, 0), Weekdays.MONDAY) == date(2026, 10, 12)

def test_same_weekday_returns_next_week():
    assert next_weekday(datetime(2026, 10, 9, 9, 0, 0, 0), Weekdays.FRIDAY) == date(2026, 10, 16)
    assert next_weekday(datetime(2027, 1, 1, 9, 0, 0, 0), Weekdays.FRIDAY) == date(2027, 1, 8)

def test_generate_next_n_days():
    assert generate_next_n_days(datetime(2026, 10, 7, 9, 0, 0, 0), 7) == (
        "- Today: 2026-10-07 (Wednesday)\n"
        "- Thursday: 2026-10-08 (tomorrow)\n"
        "- Friday: 2026-10-09\n"
        "- Saturday: 2026-10-10\n"
        "- Sunday: 2026-10-11\n"
        "- Monday: 2026-10-12\n"
        "- Tuesday: 2026-10-13\n"
        "- Wednesday: 2026-10-14"
    )

def test_generate_week_crosses_year_boundary():
    lines = generate_next_n_days(datetime(2026, 12, 30, 9, 0, 0, 0), 7).splitlines()
    assert lines[0] == "- Today: 2026-12-30 (Wednesday)"
    assert lines[2] == "- Friday: 2027-01-01"
    assert lines[-1] == "- Wednesday: 2027-01-06"
