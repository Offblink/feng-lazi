"""session.Tracker 累计逻辑测试 (纯逻辑, 无需 Qt)."""
from datetime import datetime

from session import Record, Tracker


class Fg:
    """伪造的 ForegroundInfo."""

    def __init__(self, name, path=None):
        self.name = name
        self.exe_path = path or f"C:/Apps/{name}"


def at(h, m=0, s=0):
    return datetime(2026, 8, 12, h, m, s)


def test_accumulates_until_switch():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 1), Fg("a.exe"))
    tr.tick(at(10, 0, 3), Fg("b.exe"))   # 第 3 秒切到 b
    recs = tr.flush(at(10, 0, 4))
    assert {(r.app_name, r.seconds) for r in recs} == {("a.exe", 3), ("b.exe", 1)}


def test_no_foreground_clears_segment_and_counts_nothing():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 2), None)          # 切到桌面, 段结束
    tr.tick(at(10, 0, 5), Fg("b.exe"))   # 回来用 b, 但 flush 时无增量
    recs = tr.flush(at(10, 0, 5))
    assert [(r.app_name, r.seconds) for r in recs] == [("a.exe", 2)]


def test_delta_capped_after_suspend():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 5, 0), Fg("a.exe"))   # 5 分钟后才恢复
    recs = tr.flush(at(10, 5, 0))
    assert recs[0].seconds == 60         # 上限 60s


def test_pause_resume():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.pause()
    tr.tick(at(10, 0, 2), Fg("a.exe"))
    assert tr.is_paused and tr.current_app is None
    tr.resume()
    tr.tick(at(10, 0, 4), Fg("a.exe"))
    recs = tr.flush(at(10, 0, 5))
    assert [r.seconds for r in recs] == [1]   # 仅恢复后的 1s


def test_flush_continuity_across_flushes():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    first = tr.flush(at(10, 0, 5))
    assert first[0].seconds == 5
    tr.tick(at(10, 0, 6), Fg("a.exe"))
    tr.tick(at(10, 0, 8), Fg("a.exe"))
    second = tr.flush(at(10, 0, 10))
    assert sum(r.seconds for r in second) == 5


def test_midnight_crossing_credits_new_date():
    tr = Tracker()
    tr.tick(datetime(2026, 8, 12, 23, 59, 59), Fg("a.exe"))
    tr.tick(datetime(2026, 8, 13, 0, 0, 1), Fg("a.exe"))
    recs = tr.flush(datetime(2026, 8, 13, 0, 0, 1))
    assert recs == [Record("2026-08-13", 0, "C:/Apps/a.exe", "a.exe", 2)]


def test_hour_crossing_credits_tick_hour():
    tr = Tracker()
    tr.tick(datetime(2026, 8, 12, 10, 59, 59), Fg("a.exe"))
    tr.tick(datetime(2026, 8, 12, 11, 0, 2), Fg("a.exe"))   # 3 秒跨小时
    recs = tr.flush(datetime(2026, 8, 12, 11, 0, 2))
    assert recs == [Record("2026-08-12", 11, "C:/Apps/a.exe", "a.exe", 3)]


def test_hour_attribution_by_tick_time():
    tr = Tracker()
    tr.tick(datetime(2026, 8, 12, 10, 0, 0), Fg("a.exe"))
    tr.tick(datetime(2026, 8, 12, 10, 0, 4), Fg("a.exe"))
    recs = tr.flush(datetime(2026, 8, 12, 10, 0, 4))
    assert {(r.hour, r.app_name, r.seconds) for r in recs} == {(10, "a.exe", 4)}

    tr2 = Tracker()   # 独立 tracker, 避免大间隔触发 60s 上限污染
    tr2.tick(datetime(2026, 8, 12, 14, 0, 0), Fg("b.exe"))
    tr2.tick(datetime(2026, 8, 12, 14, 0, 3), Fg("b.exe"))
    recs2 = tr2.flush(datetime(2026, 8, 12, 14, 0, 3))
    assert {(r.hour, r.app_name, r.seconds) for r in recs2} == {(14, "b.exe", 3)}


def test_empty_tracker_flush():
    tr = Tracker()
    assert tr.flush(at(9, 0, 0)) == []
    tr.tick(at(9, 0, 0), None)
    assert tr.flush(at(9, 0, 1)) == []


def test_pending_seconds_tracks_unflushed():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 4), Fg("a.exe"))
    assert tr.pending_seconds("2026-08-12") == 4
    assert tr.pending_seconds("2026-08-13") == 0
    tr.flush(at(10, 0, 4))
    assert tr.pending_seconds("2026-08-12") == 0
