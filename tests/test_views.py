"""统计视图测试 (qtbot): 今日数据渲染 / 空状态 / 近7天 / 展示名 / 时长格式."""
from datetime import date, timedelta

import pytest

from session import Record
from store import Store
from widgets.app_row import AppRow, display_name
from widgets.format import format_duration
from widgets.history_view import AppLine, DayBlock, HistoryView
from widgets.stats_view import StatsView


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def test_stats_view_shows_total_and_rows(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        Record(today, "C:/Apps/A.exe", "a.exe", 3600),
        Record(today, "C:/Apps/B.exe", "b.exe", 600),
    ])
    view = StatsView(store)
    qtbot.addWidget(view)
    assert view.total_label.text() == "1 小时 10 分"
    assert len(view.findChildren(AppRow)) == 2


def test_stats_view_empty_state(store, qtbot):
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    assert view.empty_label.isVisible()
    assert not view.card.isVisible()


def test_stats_view_many_rows_scrollable(store, qtbot):
    today = date.today().isoformat()
    store.add_records([Record(today, f"C:/Apps/App{i}.exe", f"app{i}.exe", (i + 1) * 60)
                       for i in range(30)])
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    view.resize(480, 400)
    assert len(view.findChildren(AppRow)) == 30
    qtbot.waitUntil(lambda: view.scroll.verticalScrollBar().maximum() > 0,
                    timeout=2000)


def test_stats_view_refresh_picks_up_new_records(store, qtbot):
    today = date.today().isoformat()
    view = StatsView(store)
    qtbot.addWidget(view)
    assert len(view.findChildren(AppRow)) == 0
    store.add_records([Record(today, "C:/Apps/A.exe", "a.exe", 30)])
    view.refresh()
    assert len(view.findChildren(AppRow)) == 1
    assert view.total_label.text() == "30 秒"


def test_display_name_uses_path_basename():
    assert display_name("C:/Apps/Chrome.exe", "chrome.exe") == "Chrome.exe"
    assert display_name("", "chrome.exe") == "chrome.exe"


def test_format_duration_cases():
    assert format_duration(0) == "0 秒"
    assert format_duration(45) == "45 秒"
    assert format_duration(90) == "1 分 30 秒"
    assert format_duration(3661) == "1 小时 1 分"


def test_history_view_shows_seven_days(store, qtbot):
    today = date.today()
    store.add_records([
        Record((today - timedelta(days=1)).isoformat(), "C:/Apps/A.exe", "a.exe", 3600),
        Record((today - timedelta(days=3)).isoformat(), "C:/Apps/B.exe", "b.exe", 120),
    ])
    view = HistoryView(store)
    qtbot.addWidget(view)
    blocks = view.findChildren(DayBlock)
    assert len(blocks) == 7                              # 恒为 7 天
    assert len(view.findChildren(AppLine)) == 2          # 2 天有数据
    assert len(blocks[3].findChildren(AppLine)) == 1     # 3 天前
    assert len(blocks[5].findChildren(AppLine)) == 1     # 昨天
    assert len(blocks[6].findChildren(AppLine)) == 0     # 今天无数据


def test_history_view_empty_day_placeholder(store, qtbot):
    view = HistoryView(store)
    qtbot.addWidget(view)
    assert len(view.findChildren(DayBlock)) == 7
    assert len(view.findChildren(AppLine)) == 0           # 全部空日
