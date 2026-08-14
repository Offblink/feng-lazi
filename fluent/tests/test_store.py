"""store.Store SQLite 持久化测试 (v3: 精确时段段 + v1/v2 迁移)."""
import os
import sys

# 保证 v4/ 在 sys.path 最前 (防与项目根 v3 同名包冲突)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def rec(d, start, end, name, seconds, path=None):
    return Record(d, start, end, path or f"C:/Apps/{name}", name, seconds)


def test_upsert_replaces_open_segment(store):
    """同 (date, start, app_path) 覆盖: 开放段 10s 刷新扩展而非累加."""
    store.add_records([rec("2026-08-12", "10:00:00", "10:00:10", "a.exe", 10)])
    store.add_records([rec("2026-08-12", "10:00:00", "10:00:25", "a.exe", 25)])
    assert store.today_total("2026-08-12") == 25


def test_daily_breakdown_sums_segments(store):
    store.add_records([
        rec("2026-08-12", "09:00:00", "09:00:03", "a.exe", 3),
        rec("2026-08-12", "10:00:00", "10:00:06", "a.exe", 6),
        rec("2026-08-12", "10:00:00", "10:00:09", "b.exe", 9),
    ])
    names = [r["app_name"] for r in store.daily_breakdown("2026-08-12")]
    assert names == ["b.exe", "a.exe"]
    assert store.daily_breakdown("2026-08-12")[1]["seconds"] == 9


def test_app_segments_positions_and_order(store):
    store.add_records([
        rec("2026-08-12", "10:05:00", "10:08:00", "a.exe", 180),
        rec("2026-08-12", "11:30:00", "11:45:00", "a.exe", 900),
        rec("2026-08-12", "20:00:00", "22:00:00", "b.exe", 7200),
    ])
    apps = store.app_segments("2026-08-12")
    assert [a["app_name"] for a in apps] == ["b.exe", "a.exe"]   # 总秒数降序
    a = apps[1]
    assert a["seconds"] == 1080
    assert [s["start_min"] for s in a["segments"]] == [605, 690]  # 按开始时刻排序
    assert a["segments"][0]["end_min"] == 608
    assert a["segments"][1]["end_min"] == 705
    assert apps[0]["segments"][0]["start_min"] == 1200
    assert apps[0]["segments"][0]["end_min"] == 1320
    assert store.app_segments("2026-08-13") == []


def test_app_segments_midnight_end_is_1440(store):
    store.add_records([rec("2026-08-12", "23:50:00", "00:00:00", "a.exe", 600)])
    apps = store.app_segments("2026-08-12")
    seg = apps[0]["segments"][0]
    assert seg["start_min"] == 1430
    assert seg["end_min"] == 1440   # 次日零点 = 24:00


def test_days_isolated(store):
    store.add_records([rec("2026-08-11", "10:00:00", "10:00:07", "a.exe", 7)])
    assert store.today_total("2026-08-12") == 0


def test_last_n_days_includes_empty_days(store):
    store.add_records([rec("2026-08-10", "10:00:00", "10:01:00", "a.exe", 60)])
    days = store.last_n_days(3, date(2026, 8, 12))
    assert [d["date"] for d in days] == ["2026-08-10", "2026-08-11", "2026-08-12"]
    assert [d["seconds"] for d in days] == [60, 0, 0]


def test_zero_seconds_ignored(store):
    store.add_records([rec("2026-08-12", "10:00:00", "10:00:00", "a.exe", 0)])
    assert store.today_total("2026-08-12") == 0


def _make_legacy_db(db, columns, rows):
    conn = sqlite3.connect(db)
    cols = ", ".join(f"{c} TEXT" for c in columns[:-1]) + ", seconds INTEGER"
    pk = ", ".join(columns[:-1])
    conn.execute(f"CREATE TABLE usage ({cols}, PRIMARY KEY({pk}))")
    for r in rows:
        conn.execute(f"INSERT INTO usage VALUES({','.join('?' * len(r))})", r)
    conn.commit()
    conn.close()


def test_v2_db_backed_up_and_rebuilt(tmp_path):
    """v2 schema (含 hour 列) → 备份 .v2.bak, 新库为 segments 空表."""
    db = str(tmp_path / "usage.db")
    _make_legacy_db(db, ["date", "hour", "app_path", "app_name", "seconds"],
                    [("2026-08-12", 21, "C:/a.exe", "a.exe", 99)])

    s = Store(db)
    assert s.today_total("2026-08-12") == 0            # 新库不含旧数据
    assert os.path.exists(db + ".v2.bak")               # 旧库已备份
    tables = [r[0] for r in s.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    assert "segments" in tables and "usage" not in tables
    s.close()

    bak = sqlite3.connect(db + ".v2.bak")
    total = bak.execute("SELECT SUM(seconds) FROM usage").fetchone()[0]
    assert total == 99
    bak.close()


def test_v1_db_backed_up_as_v1(tmp_path):
    """v1 schema (无 hour 列) → 仍备份 .v1.bak."""
    db = str(tmp_path / "usage.db")
    _make_legacy_db(db, ["date", "app_path", "app_name", "seconds"],
                    [("2026-08-12", "C:/a.exe", "a.exe", 99)])

    s = Store(db)
    assert s.today_total("2026-08-12") == 0
    assert os.path.exists(db + ".v1.bak")
    s.close()
