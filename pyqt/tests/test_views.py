"""统计视图测试 (qtbot): 今日数据渲染 / 空状态 / 近7天 / 精确时段 / 展示名."""
from datetime import date, timedelta

import pytest

from session import Record
from store import Store
from widgets.app_row import AppRow, display_name
from widgets.apps_view import AppsView
from widgets.format import format_duration
from widgets.history_view import AppLine, DayBlock, HistoryView
from widgets.stats_view import StatsView
from widgets.time_gantt import TimeGantt, seg_times


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def rec(d, start, end, name, seconds, path=None):
    return Record(d, start, end, path or f"C:/Apps/{name}", name, seconds)


def test_apps_view_shows_total_and_rows(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, "10:00:00", "11:00:00", "a.exe", 3600),
        rec(today, "14:00:00", "14:10:00", "b.exe", 600),
    ])
    view = AppsView(store)
    qtbot.addWidget(view)
    assert view.total_label.text() == "1 小时 10 分"
    assert len(view.findChildren(AppRow)) == 2


def test_apps_view_empty_state(store, qtbot):
    view = AppsView(store)
    qtbot.addWidget(view)
    view.show()
    assert view.empty_label.isVisible()
    assert not view.card.isVisible()


def test_apps_view_many_rows_scrollable(store, qtbot):
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "10:01:00", f"app{i}.exe", (i + 1) * 60)
                       for i in range(30)])
    view = AppsView(store)
    qtbot.addWidget(view)
    view.show()
    view.resize(480, 400)
    assert len(view.findChildren(AppRow)) == 30
    qtbot.waitUntil(lambda: view.scroll.verticalScrollBar().maximum() > 0,
                    timeout=2000)


def test_apps_view_refresh_picks_up_new_records(store, qtbot):
    today = date.today().isoformat()
    view = AppsView(store)
    qtbot.addWidget(view)
    assert len(view.findChildren(AppRow)) == 0
    store.add_records([rec(today, "10:00:00", "10:00:30", "a.exe", 30)])
    view.refresh()
    assert len(view.findChildren(AppRow)) == 1
    assert view.total_label.text() == "30 秒"


def test_seg_times_formats():
    assert seg_times({"start": "10:05:00", "end": "10:23:30", "seconds": 1110}) \
        == "10:05 - 10:23"
    assert seg_times({"start": "10:05:30", "end": "10:05:45", "seconds": 15}) \
        == "10:05:30 - 10:05:45"   # 不足 1 分钟含秒


def test_gantt_shows_rows_and_segments(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, "10:05:00", "10:07:00", "a.exe", 120),
        rec(today, "11:30:00", "11:32:00", "a.exe", 120),
        rec(today, "20:00:00", "22:00:00", "b.exe", 7200),
    ])
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    assert view.total_label.text() == "2 小时 4 分"
    gantts = view.findChildren(TimeGantt)
    assert len(gantts) == 1
    gantt = gantts[0]
    rows = {r["app_name"]: r for r in gantt._rows}
    assert set(rows) == {"a.exe", "b.exe"}
    assert [s["start_min"] for s in rows["a.exe"]["segments"]] == [605, 690]
    assert rows["a.exe"]["segments"][0]["end_min"] == 607
    assert rows["b.exe"]["segments"][0]["start_min"] == 1200
    assert view.gantt_card.isVisible()
    assert not view.empty_label.isVisible()


def test_gantt_segment_rect_from_start_point():
    g = TimeGantt()
    g.resize(502, 100)                  # plot_w = 502 - 150 = 352
    x0, x1 = g._seg_rect(150, 352, 0, 720)      # 0-12 时 → 整半宽
    assert x0 == 150 and x1 == 326
    x0, x1 = g._seg_rect(150, 352, 605, 607)    # 10:05-10:07 → 由起始点定位
    assert x0 == 150 + int(352 * 605 / 1440)
    assert x1 - x0 == max(int(352 * 2 / 1440), 2)
    x0, x1 = g._seg_rect(150, 352, 1439, 1440)  # 末分钟段保底可见
    assert x1 - x0 == 2


def test_gantt_coordinate_conversion():
    g = TimeGantt()
    assert g._row_at(30.5) == 1        # 30.5 // 26 → int
    g.resize(502, 100)                  # plot_w = 502 - 150 = 352
    assert g._minute_at(150.0) == 0
    assert g._minute_at(151.0) == 4
    assert g._minute_at(500.0) == 1431
    assert g._minute_at(1000.0) == 1439  # 越界钳制


def test_gantt_hidden_when_no_data(store, qtbot):
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    assert not view.gantt_card.isVisible()
    assert view.empty_label.isVisible()


def test_gantt_rows_fixed_height(store, qtbot):
    """行高固定 ROW_H, 不随应用数量拉伸: 少行无滚动条, 内容高度 = 行数 * ROW_H."""
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "11:00:00", "a.exe", 3600),
                       rec(today, "20:00:00", "22:00:00", "b.exe", 7200)])
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    view.resize(480, 640)
    qtbot.wait(50)                          # 布局生效
    assert view.gantt._row_h() == TimeGantt.ROW_H
    assert view.gantt.height() == 2 * TimeGantt.ROW_H + TimeGantt.AXIS_H + 4
    assert view.gantt_scroll.verticalScrollBar().maximum() == 0


def test_gantt_scrolls_when_many_rows(store, qtbot):
    """多行时内容高度超视口, 滚动区出现滚动条."""
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "10:01:00", f"app{i}.exe", (i + 1) * 60)
                       for i in range(30)])
    view = StatsView(store)
    qtbot.addWidget(view)
    view.show()
    view.resize(480, 640)
    qtbot.wait(50)
    assert view.gantt._row_h() == TimeGantt.ROW_H
    qtbot.waitUntil(lambda: view.gantt_scroll.verticalScrollBar().maximum() > 0,
                    timeout=2000)


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
        rec((today - timedelta(days=1)).isoformat(), "10:00:00", "11:00:00",
            "a.exe", 3600),
        rec((today - timedelta(days=3)).isoformat(), "14:00:00", "14:02:00",
            "b.exe", 120),
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
