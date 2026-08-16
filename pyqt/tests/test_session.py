"""session.Tracker 累计逻辑测试 (纯逻辑, 无需 Qt; v3: 精确起止段)."""
from datetime import datetime, timedelta

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
    a = next(r for r in recs if r.app_name == "a.exe")
    b = next(r for r in recs if r.app_name == "b.exe")
    assert (a.start, a.end) == ("10:00:00", "10:00:03")
    assert (b.start, b.end) == ("10:00:03", "10:00:04")


def test_no_foreground_clears_segment_and_counts_nothing():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 2), None)          # 切到桌面, 段结束
    tr.tick(at(10, 0, 5), Fg("b.exe"))   # 回来用 b, 但 flush 时无增量
    recs = tr.flush(at(10, 0, 5))
    assert [(r.app_name, r.seconds) for r in recs] == [("a.exe", 2)]
    assert recs[0].end == "10:00:02"


def test_delta_capped_after_suspend():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 5, 0), Fg("a.exe"))   # 5 分钟后才恢复
    recs = tr.flush(at(10, 5, 0))
    assert recs[0].seconds == 60         # 上限 60s
    assert recs[0].end == "10:05:00"     # 起止仍是真实墙钟


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


def test_flush_keeps_segment_open_and_cumulative():
    """flush 不结束段: 开放段以最新状态重复返回 (store 覆盖刷新)."""
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    first = tr.flush(at(10, 0, 5))
    assert [(r.start, r.end, r.seconds) for r in first] == [
        ("10:00:00", "10:00:05", 5)]
    tr.tick(at(10, 0, 6), Fg("a.exe"))
    tr.tick(at(10, 0, 8), Fg("a.exe"))
    second = tr.flush(at(10, 0, 10))
    assert [(r.start, r.end, r.seconds) for r in second] == [
        ("10:00:00", "10:00:10", 10)]    # 同段累计, 覆盖语义


def test_closed_segment_flushed_once_then_gone():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 3), None)          # 段结束
    tr.flush(at(10, 0, 3))
    assert tr.flush(at(10, 0, 4)) == []  # 已入库, 不再返回


def test_midnight_crossing_splits_segment():
    tr = Tracker()
    tr.tick(datetime(2026, 8, 12, 23, 59, 59), Fg("a.exe"))
    tr.tick(datetime(2026, 8, 13, 0, 0, 1), Fg("a.exe"))
    recs = tr.flush(datetime(2026, 8, 13, 0, 0, 1))
    assert recs == [Record("2026-08-13", "00:00:00", "00:00:01",
                           "C:/Apps/a.exe", "a.exe", 2)]   # 跨边界秒数计入新日期


def test_hour_crossing_stays_one_segment():
    tr = Tracker()
    tr.tick(datetime(2026, 8, 12, 10, 59, 59), Fg("a.exe"))
    tr.tick(datetime(2026, 8, 12, 11, 0, 2), Fg("a.exe"))   # 跨小时不拆段
    recs = tr.flush(datetime(2026, 8, 12, 11, 0, 2))
    assert recs == [Record("2026-08-12", "10:59:59", "11:00:02",
                           "C:/Apps/a.exe", "a.exe", 3)]


def test_pending_seconds_tracks_unflushed_only():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.tick(at(10, 0, 4), Fg("a.exe"))
    assert tr.pending_seconds("2026-08-12") == 4
    assert tr.pending_seconds("2026-08-13") == 0
    tr.flush(at(10, 0, 4))               # 开放段入库后不再计入
    assert tr.pending_seconds("2026-08-12") == 0


def test_pending_does_not_double_count_persisted_open_segment():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.flush(at(10, 0, 10))              # 10s 已入库
    tr.tick(at(10, 0, 13), Fg("a.exe"))  # 又累计 3s
    assert tr.pending_seconds("2026-08-12") == 3
    assert tr.pending_seconds("2026-08-12") + 10 == 13


def test_pending_after_close_counts_delta_over_persisted():
    tr = Tracker()
    tr.tick(at(10, 0, 0), Fg("a.exe"))
    tr.flush(at(10, 0, 10))              # 10s 已入库
    tr.tick(at(10, 0, 15), Fg("a.exe"))
    tr.tick(at(10, 0, 16), None)         # 段关闭, 共 16s
    assert tr.pending_seconds("2026-08-12") == 6   # 16 - 10 = 6, 不重复
    tr.flush(at(10, 0, 16))
    assert tr.pending_seconds("2026-08-12") == 0


def test_empty_tracker_flush():
    tr = Tracker()
    assert tr.flush(at(9, 0, 0)) == []
    tr.tick(at(9, 0, 0), None)
    assert tr.flush(at(9, 0, 1)) == []


def test_zero_second_segment_not_recorded():
    tr = Tracker()
    tr.tick(at(9, 0, 0), Fg("a.exe"))
    tr.tick(at(9, 0, 0), Fg("b.exe"))    # 无增量即切换
    assert tr.flush(at(9, 0, 0)) == []


def test_subsecond_ticks_accumulate_via_carry():
    """定时器提前触发 (每次间隔 <1s): 余数跨 tick 累计进位, 不整秒丢失."""
    tr = Tracker()
    base = datetime(2026, 8, 12, 10, 0, 0)
    tr.tick(base, Fg("a.exe"))
    for i in range(1, 11):
        tr.tick(base + timedelta(microseconds=i * 990_000), Fg("a.exe"))  # 每 990ms
    recs = tr.flush(base + timedelta(microseconds=10 * 990_000))
    assert recs and recs[0].seconds == 9   # 9.9s 墙钟 → 9 整秒


def test_jittered_ticks_count_wall_time():
    """早/晚触发混合: 计入 floor(墙钟间隔), 而非逐 tick int() 截断."""
    tr = Tracker()
    base = datetime(2026, 8, 12, 10, 0, 0)
    tr.tick(base, Fg("a.exe"))
    us = 0
    for i in range(1, 11):
        us += 990_000 if i % 2 else 1_010_000   # 交替 0.99s / 1.01s
        tr.tick(base + timedelta(microseconds=us), Fg("a.exe"))
    recs = tr.flush(base + timedelta(microseconds=us))
    assert recs and recs[0].seconds == 10   # 共 10.0s 墙钟 → 10 整秒
