"""store.Store SQLite 持久化测试."""
from datetime import date

import pytest

from session import Record
from store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def test_upsert_accumulates(store):
    store.add_records([Record("2026-08-12", "C:/a.exe", "a.exe", 10)])
    store.add_records([Record("2026-08-12", "C:/a.exe", "a.exe", 5)])
    assert store.today_total("2026-08-12") == 15


def test_daily_breakdown_sorted(store):
    store.add_records([
        Record("2026-08-12", "C:/a.exe", "a.exe", 3),
        Record("2026-08-12", "C:/b.exe", "b.exe", 9),
        Record("2026-08-12", "C:/c.exe", "c.exe", 5),
    ])
    names = [r["app_name"] for r in store.daily_breakdown("2026-08-12")]
    assert names == ["b.exe", "c.exe", "a.exe"]


def test_days_isolated(store):
    store.add_records([Record("2026-08-11", "C:/a.exe", "a.exe", 7)])
    assert store.today_total("2026-08-12") == 0


def test_last_n_days_includes_empty_days(store):
    store.add_records([Record("2026-08-10", "C:/a.exe", "a.exe", 60)])
    days = store.last_n_days(3, date(2026, 8, 12))
    assert [d["date"] for d in days] == ["2026-08-10", "2026-08-11", "2026-08-12"]
    assert [d["seconds"] for d in days] == [60, 0, 0]


def test_zero_seconds_ignored(store):
    store.add_records([Record("2026-08-12", "C:/a.exe", "a.exe", 0)])
    assert store.today_total("2026-08-12") == 0
