"""store.Store SQLite 持久化测试 (v2: 小时维度 + 迁移)."""
import os
import sqlite3
from datetime import date

import pytest

from session import Record
from store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def rec(d, h, name, seconds, path=None):
    return Record(d, h, path or f"C:/Apps/{name}", name, seconds)


def test_upsert_accumulates_per_hour(store):
    store.add_records([rec("2026-08-12", 10, "a.exe", 10)])
    store.add_records([rec("2026-08-12", 10, "a.exe", 5)])
    store.add_records([rec("2026-08-12", 11, "a.exe", 7)])   # 不同小时分开
    assert store.today_total("2026-08-12") == 22


def test_daily_breakdown_sums_across_hours(store):
    store.add_records([
        rec("2026-08-12", 9, "a.exe", 3),
        rec("2026-08-12", 10, "a.exe", 6),
        rec("2026-08-12", 10, "b.exe", 9),
    ])
    names = [r["app_name"] for r in store.daily_breakdown("2026-08-12")]
    assert names == ["b.exe", "a.exe"]
    assert store.daily_breakdown("2026-08-12")[1]["seconds"] == 9


def test_hourly_breakdown_always_24_slots(store):
    store.add_records([
        rec("2026-08-12", 10, "a.exe", 60),
        rec("2026-08-12", 10, "b.exe", 30),
        rec("2026-08-12", 22, "a.exe", 120),
    ])
    hours = store.hourly_breakdown("2026-08-12")
    assert len(hours) == 24
    assert [h["hour"] for h in hours] == list(range(24))
    assert hours[10]["seconds"] == 90
    assert hours[22]["seconds"] == 120
    assert hours[0]["seconds"] == 0


def test_days_isolated(store):
    store.add_records([rec("2026-08-11", 10, "a.exe", 7)])
    assert store.today_total("2026-08-12") == 0


def test_last_n_days_includes_empty_days(store):
    store.add_records([rec("2026-08-10", 10, "a.exe", 60)])
    days = store.last_n_days(3, date(2026, 8, 12))
    assert [d["date"] for d in days] == ["2026-08-10", "2026-08-11", "2026-08-12"]
    assert [d["seconds"] for d in days] == [60, 0, 0]


def test_zero_seconds_ignored(store):
    store.add_records([rec("2026-08-12", 10, "a.exe", 0)])
    assert store.today_total("2026-08-12") == 0


def test_v1_db_backed_up_and_rebuilt(tmp_path):
    """旧版 schema (无 hour 列) → 备份 .v1.bak, 新库为空."""
    db = str(tmp_path / "usage.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE usage (date TEXT, app_path TEXT, app_name TEXT,"
                 " seconds INTEGER, PRIMARY KEY(date, app_path))")
    conn.execute("INSERT INTO usage VALUES('2026-08-12', 'C:/a.exe', 'a.exe', 99)")
    conn.commit()
    conn.close()

    s = Store(db)
    assert s.today_total("2026-08-12") == 0            # 新库不含旧数据
    assert os.path.exists(db + ".v1.bak")               # 旧库已备份
    cols = [r[1] for r in s.conn.execute("PRAGMA table_info(usage)")]
    assert "hour" in cols
    s.close()

    # 备份里保留 v1 数据
    bak = sqlite3.connect(db + ".v1.bak")
    total = bak.execute("SELECT SUM(seconds) FROM usage").fetchone()[0]
    assert total == 99
    bak.close()
