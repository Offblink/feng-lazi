"""v4 视图测试 (qtbot): 甘特页渲染 / 空状态 / 铺满行为 / 坐标换算."""
import os
import sys
from datetime import date, timedelta

# 保证 v4/ 在 sys.path 最前 (pytest 会在导入测试模块时把项目根插到最前,
# 与项目根的 v3 同名包 widgets/store 冲突)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from session import Record
from store import Store
from widgets.app_row import AppRow
from widgets.apps_page import AppsPage
from widgets.gantt_page import GanttPage
from widgets.history_page import AppLine, DayBlock, HistoryPage
from widgets.time_gantt import TimeGantt, seg_times


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "usage.db"))
    yield s
    s.close()


def rec(d, start, end, name, seconds, path=None):
    return Record(d, start, end, path or f"C:/Apps/{name}", name, seconds)


def test_gantt_page_shows_total_and_rows(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, "10:05:00", "10:07:00", "a.exe", 120),
        rec(today, "11:30:00", "11:32:00", "a.exe", 120),
        rec(today, "20:00:00", "22:00:00", "b.exe", 7200),
    ])
    page = GanttPage(store)
    qtbot.addWidget(page)
    page.show()
    assert page.total_label.text() == "2 小时 4 分"
    rows = {r["app_name"]: r for r in page.gantt._rows}
    assert set(rows) == {"a.exe", "b.exe"}
    assert [s["start_min"] for s in rows["a.exe"]["segments"]] == [605, 690]
    assert rows["a.exe"]["segments"][0]["end_min"] == 607
    assert rows["b.exe"]["segments"][0]["start_min"] == 1200
    assert page.gantt_card.isVisible()
    assert not page.empty_label.isVisible()


def test_gantt_page_empty_state(store, qtbot):
    page = GanttPage(store)
    qtbot.addWidget(page)
    page.show()
    assert not page.gantt_card.isVisible()
    assert page.empty_label.isVisible()


def test_gantt_page_fills_height(store, qtbot):
    """少行时甘特铺满页面: 卡片吸收剩余高度, 行带随可用高度放大."""
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "11:00:00", "a.exe", 3600)])
    page = GanttPage(store)
    qtbot.addWidget(page)
    page.show()
    page.resize(520, 680)
    qtbot.wait(50)
    assert page.gantt_card.height() > page.height() // 2
    assert page.gantt._row_h() > TimeGantt.ROW_H


def test_gantt_page_scrolls_when_many_rows(store, qtbot):
    """多行时行高回落 ROW_H, 滚动区出现滚动条."""
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "10:01:00", f"app{i}.exe", (i + 1) * 60)
                       for i in range(30)])
    page = GanttPage(store)
    qtbot.addWidget(page)
    page.show()
    page.resize(520, 680)
    qtbot.wait(50)
    assert page.gantt._row_h() == TimeGantt.ROW_H
    qtbot.waitUntil(lambda: page.gantt_scroll.verticalScrollBar().maximum() > 0,
                    timeout=2000)


def test_seg_times_formats():
    assert seg_times({"start": "10:05:00", "end": "10:23:30", "seconds": 1110}) \
        == "10:05 - 10:23"
    assert seg_times({"start": "10:05:30", "end": "10:05:45", "seconds": 15}) \
        == "10:05:30 - 10:05:45"   # 不足 1 分钟含秒


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
    assert g._row_at(30.5) == 1        # 30.5 // 26 → int (空行保底 ROW_H)
    g.resize(502, 100)                  # plot_w = 502 - 150 = 352
    assert g._minute_at(150.0) == 0
    assert g._minute_at(151.0) == 4
    assert g._minute_at(500.0) == 1431
    assert g._minute_at(1000.0) == 1439  # 越界钳制


def test_apps_page_shows_total_and_rows(store, qtbot):
    today = date.today().isoformat()
    store.add_records([
        rec(today, "10:00:00", "11:00:00", "a.exe", 3600),
        rec(today, "14:00:00", "14:10:00", "b.exe", 600),
    ])
    page = AppsPage(store)
    qtbot.addWidget(page)
    assert page.total_label.text() == "1 小时 10 分"
    assert len(page.findChildren(AppRow)) == 2


def test_apps_page_empty_state(store, qtbot):
    page = AppsPage(store)
    qtbot.addWidget(page)
    page.show()
    assert page.empty_label.isVisible()
    assert not page.card.isVisible()


def test_apps_page_many_rows_scrollable(store, qtbot):
    today = date.today().isoformat()
    store.add_records([rec(today, "10:00:00", "10:01:00", f"app{i}.exe", (i + 1) * 60)
                       for i in range(30)])
    page = AppsPage(store)
    qtbot.addWidget(page)
    page.show()
    page.resize(520, 680)
    assert len(page.findChildren(AppRow)) == 30
    qtbot.waitUntil(lambda: page.scroll.verticalScrollBar().maximum() > 0,
                    timeout=2000)


def test_apps_page_refresh_picks_up_new_records(store, qtbot):
    today = date.today().isoformat()
    page = AppsPage(store)
    qtbot.addWidget(page)
    assert len(page.findChildren(AppRow)) == 0
    store.add_records([rec(today, "10:00:00", "10:00:30", "a.exe", 30)])
    page.refresh()
    assert len(page.findChildren(AppRow)) == 1
    assert page.total_label.text() == "30 秒"


def test_display_name_uses_path_basename():
    from widgets.app_row import display_name
    assert display_name("C:/Apps/Chrome.exe", "chrome.exe") == "Chrome.exe"
    assert display_name("", "chrome.exe") == "chrome.exe"


def test_history_page_shows_seven_days(store, qtbot):
    today = date.today()
    store.add_records([
        rec((today - timedelta(days=1)).isoformat(), "10:00:00", "11:00:00",
            "a.exe", 3600),
        rec((today - timedelta(days=3)).isoformat(), "14:00:00", "14:02:00",
            "b.exe", 120),
    ])
    page = HistoryPage(store)
    qtbot.addWidget(page)
    blocks = page.findChildren(DayBlock)
    assert len(blocks) == 7                              # 恒为 7 天
    assert len(page.findChildren(AppLine)) == 2          # 2 天有数据
    assert len(blocks[3].findChildren(AppLine)) == 1     # 3 天前
    assert len(blocks[5].findChildren(AppLine)) == 1     # 昨天
    assert len(blocks[6].findChildren(AppLine)) == 0     # 今天无数据


def test_history_page_empty_day_placeholder(store, qtbot):
    page = HistoryPage(store)
    qtbot.addWidget(page)
    assert len(page.findChildren(DayBlock)) == 7
    assert len(page.findChildren(AppLine)) == 0           # 全部空日
