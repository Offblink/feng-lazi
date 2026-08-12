"""跟踪集成测试 (qtbot): tick → 累计 → flush 入库 → tooltip / 暂停 / 自身排除.

用假时钟 + 假前台探测, 不依赖真实桌面状态.
"""
import os
from datetime import date, datetime

import pytest

from app import TrayApp


class FakeFg:
    """伪造前台信息 (替代 foreground.get_foreground 返回值)."""

    def __init__(self, name, pid=999, hwnd=0):
        self.name = name
        self.exe_path = f"C:/Apps/{name}"
        self.pid = pid
        self.hwnd = hwnd


class FakeDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 8, 12)


@pytest.fixture
def running_app(qtbot, tmp_path, monkeypatch):
    import app as app_module

    clock = {"now": datetime(2026, 8, 12, 10, 0, 0)}

    class FakeDatetime(datetime):
        @classmethod
        def now(cls):
            return clock["now"]

    monkeypatch.setattr(app_module.foreground, "get_foreground", lambda: FakeFg("a.exe"))
    monkeypatch.setattr(app_module, "datetime", FakeDatetime)
    monkeypatch.setattr(app_module, "date", FakeDate)

    w = TrayApp(db_path=str(tmp_path / "usage.db"))
    w.start()
    qtbot.addWidget(w)
    yield w, clock
    w._tick_timer.stop()
    w.tray_icon.hide()


def advance(clock, seconds):
    clock["now"] = datetime(2026, 8, 12, 10, 0, seconds)


def test_ticks_accumulate_and_auto_flush(running_app):
    w, clock = running_app
    for s in range(1, 11):
        advance(clock, s)
        w._on_tick()
    assert w._store.today_total("2026-08-12") == 9   # 10 次 tick = 9 秒


def test_app_switch_flushes_previous_app(running_app, monkeypatch):
    w, clock = running_app
    import app as app_module

    for s in range(1, 6):
        advance(clock, s)
        w._on_tick()
    monkeypatch.setattr(app_module.foreground, "get_foreground", lambda: FakeFg("b.exe"))
    for s in range(6, 11):
        advance(clock, s)
        w._on_tick()

    total = w._store.today_total("2026-08-12")
    assert total == 9
    breakdown = {r["app_name"]: r["seconds"] for r in w._store.daily_breakdown("2026-08-12")}
    assert breakdown == {"a.exe": 5, "b.exe": 4}


def test_pause_stops_accumulation_then_resume(running_app):
    w, clock = running_app
    w.pause_action.setChecked(True)
    for s in range(1, 11):
        advance(clock, s)
        w._on_tick()
    assert w._store.today_total("2026-08-12") == 0
    assert w._tracker.is_paused

    w.pause_action.setChecked(False)
    for s in range(11, 16):
        advance(clock, s)
        w._on_tick()
    w._flush()
    assert w._store.today_total("2026-08-12") == 4


def test_self_process_excluded(running_app, monkeypatch):
    w, clock = running_app
    import app as app_module

    monkeypatch.setattr(app_module.foreground, "get_foreground",
                        lambda: FakeFg("self.exe", pid=os.getpid()))
    for s in range(1, 6):
        advance(clock, s)
        w._on_tick()
    w._flush()
    assert w._store.today_total("2026-08-12") == 0


def test_tooltip_shows_app_and_total(running_app):
    w, clock = running_app
    for s in range(1, 11):
        advance(clock, s)
        w._on_tick()
    tip = w.tray_icon.toolTip()
    assert tip.startswith("a.exe") and "9 秒" in tip


def test_tooltip_shows_paused(running_app):
    w, clock = running_app
    w.pause_action.setChecked(True)
    w._on_tick()
    assert w.tray_icon.toolTip().startswith("已暂停")
