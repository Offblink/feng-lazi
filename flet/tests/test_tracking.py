"""TrackerLoop 节拍编排测试 (纯逻辑, 对应 PyQt 版 test_integration.py 语义)."""
import os
from datetime import date, datetime

import pytest

from store import Store
from tracking import TrackerLoop, is_trackable


class FakeFg:
    def __init__(self, name, pid=999, hwnd=0):
        self.name = name
        self.exe_path = f"C:/Apps/{name}"
        self.pid = pid
        self.hwnd = hwnd


@pytest.fixture
def loop(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    clock = {"now": datetime(2026, 8, 12, 10, 0, 0)}

    class FakeDatetime(datetime):
        @classmethod
        def now(cls):
            return clock["now"]

    tr = TrackerLoop(s)
    yield tr, clock, s
    s.close()


def advance(clock, seconds):
    clock["now"] = datetime(2026, 8, 12, 10, 0, seconds)


def test_ticks_accumulate_and_auto_flush(loop):
    tr, clock, store = loop
    for s in range(1, 11):
        advance(clock, s)
        tr.step(clock["now"], FakeFg("a.exe"))
    assert store.today_total("2026-08-12") == 9   # 10 次 tick = 9 秒


def test_app_switch_flushes_previous_app(loop):
    tr, clock, store = loop
    for s in range(1, 6):
        advance(clock, s)
        tr.step(clock["now"], FakeFg("a.exe"))
    for s in range(6, 11):
        advance(clock, s)
        tr.step(clock["now"], FakeFg("b.exe"))

    assert store.today_total("2026-08-12") == 9
    breakdown = {r["app_name"]: r["seconds"]
                 for r in store.daily_breakdown("2026-08-12")}
    assert breakdown == {"a.exe": 5, "b.exe": 4}


def test_pause_stops_accumulation_then_resume(loop):
    tr, clock, store = loop
    tr.pause()
    for s in range(1, 11):
        advance(clock, s)
        tr.step(clock["now"], FakeFg("a.exe"))
    assert store.today_total("2026-08-12") == 0
    assert tr.is_paused

    tr.resume()
    for s in range(11, 16):
        advance(clock, s)
        tr.step(clock["now"], FakeFg("a.exe"))
    tr.flush(clock["now"])
    assert store.today_total("2026-08-12") == 4


def test_no_foreground_records_nothing(loop):
    tr, clock, store = loop
    for s in range(1, 6):
        advance(clock, s)
        tr.step(clock["now"], None)
    tr.flush(clock["now"])
    assert store.today_total("2026-08-12") == 0


def test_is_trackable_filters(loop):
    assert not is_trackable(None)
    assert not is_trackable(FakeFg("self.exe", pid=os.getpid()),
                            self_pid=os.getpid())
    assert not is_trackable(FakeFg("logonui.exe"))       # 系统进程排除
    assert is_trackable(FakeFg("a.exe"))                 # 普通应用可统计


def test_current_app_and_paused(loop):
    tr, clock, _store = loop
    advance(clock, 1)
    tr.step(clock["now"], FakeFg("a.exe"))
    assert tr.current_app == "a.exe"
    tr.pause()
    assert tr.current_app is None
    tr.resume()


def test_today_seconds_base_plus_pending(loop):
    tr, clock, store = loop
    advance(clock, 0)
    tr.step(clock["now"], FakeFg("a.exe"))
    advance(clock, 4)
    tr.step(clock["now"], FakeFg("a.exe"))
    assert tr.today_seconds("2026-08-12") == 4
    tr.flush(clock["now"])
    assert tr.today_seconds("2026-08-12") == 4   # 入库后不重复计数


def test_step_returns_flushed_records(loop):
    tr, clock, _store = loop
    for s in range(1, 11):
        advance(clock, s)
        recs = tr.step(clock["now"], FakeFg("a.exe"))
    assert recs and recs[0].seconds == 9
