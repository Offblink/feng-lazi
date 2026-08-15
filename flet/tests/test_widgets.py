"""widgets 纯函数 + 视图控件树测试 (无需 Flet 客户端)."""
from datetime import date, timedelta

import pytest

from session import Record
from store import Store
from widgets import time_gantt
from widgets.app_row import app_block, bar, bar_ratio, display_name
from widgets.apps_view import AppsView
from widgets.format import format_duration
from widgets.history_view import HistoryView
from widgets.stats_view import StatsView


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def rec(d, start, end, name, seconds, path=None):
    return Record(d, start, end, path or f"C:/Apps/{name}", name, seconds)


class FakeDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 8, 12)


# ---------- 纯函数 ----------

def test_display_name_uses_path_basename():
    assert display_name("C:/Apps/Chrome.exe", "chrome.exe") == "Chrome.exe"
    assert display_name("", "chrome.exe") == "chrome.exe"


def test_bar_ratio_clamps():
    assert bar_ratio(0, 100) == 0.0
    assert bar_ratio(50, 100) == 0.5
    assert bar_ratio(100, 100) == 1.0
    assert bar_ratio(150, 100) == 1.0
    assert bar_ratio(50, 0) == 0.0


def test_bar_builds_fill_and_track():
    full = bar(1.0)
    assert len(full.content.controls) == 1        # 满比例只有填充
    empty = bar(0.0)
    assert empty.content is None                  # 零比例只剩轨道
    half = bar(0.5)
    assert half.content.controls[0].expand == 500  # 500/1000 权重
def test_seg_rect_from_start_point():
    assert time_gantt.seg_rect(0, 720, 352) == (0, 176)       # 0-12 时 → 半宽
    x0, x1 = time_gantt.seg_rect(605, 607, 352)               # 10:05-10:07
    assert x0 == int(352 * 605 / 1440)
    assert x1 - x0 == max(int(352 * 2 / 1440), 2)
    x0, x1 = time_gantt.seg_rect(1439, 1440, 352)             # 末分钟段保底
    assert x1 - x0 == 2


def test_seg_times_formats():
    assert time_gantt.seg_times({"start": "10:05:00", "end": "10:23:30",
                                 "seconds": 1110}) == "10:05 - 10:23"
    assert time_gantt.seg_times({"start": "10:05:30", "end": "10:05:45",
                                 "seconds": 15}) == "10:05:30 - 10:05:45"


def test_format_duration_cases():
    assert format_duration(0) == "0 秒"
    assert format_duration(45) == "45 秒"
    assert format_duration(90) == "1 分 30 秒"
    assert format_duration(3661) == "1 小时 1 分"


# ---------- 视图控件树 ----------

def test_stats_view_empty_state(store, monkeypatch):
    monkeypatch.setattr("widgets.stats_view.date", FakeDate)
    view = StatsView(store)
    view.refresh(480)
    assert view._empty.visible
    assert not view._gantt_card.visible
    assert view._total_label.value == "0 秒"


def test_stats_view_shows_rows_and_segments(store, monkeypatch):
    monkeypatch.setattr("widgets.stats_view.date", FakeDate)
    store.add_records([
        rec("2026-08-12", "10:05:00", "10:07:00", "a.exe", 120),
        rec("2026-08-12", "11:30:00", "11:32:00", "a.exe", 120),
        rec("2026-08-12", "20:00:00", "22:00:00", "b.exe", 7200),
    ])
    view = StatsView(store)
    view.refresh(480)
    assert view._total_label.value == "2 小时 4 分"
    assert view._gantt_card.visible
    assert not view._empty.visible
    gantt_col = view._gantt_list.controls[0]
    assert gantt_col is not None
    # 甘特图: 2 应用行 + 1 横轴
    assert len(gantt_col.controls) == 3


def test_apps_view_rows_and_empty(store, monkeypatch):
    monkeypatch.setattr("widgets.apps_view.date", FakeDate)
    view = AppsView(store)
    view.refresh()
    assert view._empty.visible and not view._card.visible

    store.add_records([
        rec("2026-08-12", "10:00:00", "11:00:00", "a.exe", 3600),
        rec("2026-08-12", "14:00:00", "14:10:00", "b.exe", 600),
    ])
    view.refresh()
    assert view._total_label.value == "1 小时 10 分"
    assert view._card.visible and not view._empty.visible
    # 2 个应用块 + 1 个分隔线
    assert len(view._list.controls) == 3


def test_history_view_seven_days(store, monkeypatch):
    monkeypatch.setattr("widgets.history_view.date", FakeDate)
    store.add_records([
        rec("2026-08-11", "10:00:00", "11:00:00", "a.exe", 3600),
        rec("2026-08-09", "14:00:00", "14:02:00", "b.exe", 120),
    ])
    view = HistoryView(store)
    view.refresh()
    assert len(view._list.controls) == 7 * 2 - 1   # 7 块 + 6 分隔线
    # 昨天 = 第 7 块 (索引 12), 含头部 + 1 应用行
    yesterday = view._list.controls[12].content
    assert len(yesterday.controls) == 2           # 头部 + 1 应用行


def test_app_block_layout():
    block = app_block("C:/Apps/Chrome.exe", "chrome.exe", 120, 3600)
    assert len(block.controls) == 2               # 应用行 + 比例条
