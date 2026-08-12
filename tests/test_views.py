"""统计视图测试 (qtbot): 今日数据渲染 / 空状态 / 近7天 / 时间分布 / 展示名."""
from datetime import date, timedelta

import pytest

from session import Record
from store import Store
from widgets.app_row import AppRow, display_name
from widgets.format import format_duration
from widgets.history_view import AppLine, DayBlock, HistoryView
from widgets.stats_view import StatsView
from widgets.time_gantt import TimeGantt, spans_from_hours


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def rec(d, h, name, seconds, path=None):
    return Record(d, h, path or f"C:/Apps/{name}", name, seconds)


def test_stats_view_shows_total_and_rows(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, 10, "a.exe", 3600),
        rec(today, 14, "b.exe", 600),
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
    store.add_records([rec(today, 10, f"app{i}.exe", (i + 1) * 60)
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
    store.add_records([rec(today, 10, "a.exe", 30)])
    view.refresh()
    assert len(view.findChildren(AppRow)) == 1
    assert view.total_label.text() == "30 秒"


def test_spans_merge_consecutive_hours():
    assert spans_from_hours([0] * 24) == []
    assert spans_from_hours([60, 60, 0, 30, 0, 0, 45]) == [(0, 2), (3, 4), (6, 7)]
    assert spans_from_hours([60, 60, 0, 30]) == [(0, 2), (3, 4)]
    hours = [0] * 24
    hours[23] = 10
    assert spans_from_hours(hours) == [(23, 24)]


def test_gantt_shows_rows_and_spans(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, 10, "a.exe", 300),
        rec(today, 11, "a.exe", 120),
        rec(today, 20, "b.exe", 7200),
    ])
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    gantts = view.findChildren(TimeGantt)
    assert len(gantts) == 1
    gantt = gantts[0]
    rows = {r["app_name"]: r for r in gantt._rows}
    assert set(rows) == {"a.exe", "b.exe"}
    assert rows["a.exe"]["hours"][10] == 300
    assert rows["a.exe"]["hours"][11] == 120
    assert rows["b.exe"]["hours"][20] == 7200
    assert spans_from_hours(rows["a.exe"]["hours"]) == [(10, 12)]
    assert view.gantt_card.isVisible()


def test_gantt_coordinate_conversion():
    g = TimeGantt()
    assert g._row_at(30.5) == 1        # 30.5 // 26 → int
    g.resize(502, 100)                  # plot_w = 502 - 150 = 352
    assert g._hour_at(151.0) == 0
    assert g._hour_at(150.0) == 0
    assert g._hour_at(500.0) == 23      # 越界钳制


def test_gantt_hidden_when_no_data(store, qtbot):
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    assert not view.gantt_card.isVisible()


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
        rec((today - timedelta(days=1)).isoformat(), 10, "a.exe", 3600),
        rec((today - timedelta(days=3)).isoformat(), 14, "b.exe", 120),
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
