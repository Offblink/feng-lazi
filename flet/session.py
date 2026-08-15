"""session.py — 前台使用时长累计 (纯逻辑, 可单测).

每秒调用 tick(now, fg); 应用切换/无前台/暂停时结束当前段并记录精确起止时刻;
flush(now) 结算到 now 并返回待入库记录 (含当前开放段的最新状态, 供 10s 定期刷新).
段跨午夜时在 00:00:00 拆分, 跨边界秒数计入新日期的新段. 不依赖 Win32 / Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# 单次 tick 最大计入秒数: 防休眠/挂起后时间跳变导致虚增
MAX_TICK_DELTA = 60


@dataclass(frozen=True)
class Record:
    date: str       # 段开始日期 'YYYY-MM-DD'
    start: str      # 'HH:MM:SS' 段开始时刻
    end: str        # 'HH:MM:SS' 段结束时刻 ('00:00:00' = 次日零点)
    app_path: str
    app_name: str
    seconds: int


class Tracker:
    """按连续使用段累计前台应用时长 (段 = 同应用不间断前台)."""

    def __init__(self) -> None:
        self._current: tuple[str, str] | None = None   # (path, name) 当前段应用
        self._seg_start: datetime | None = None        # 当前段开始时刻
        self._seg_seconds: int = 0                     # 当前段已计入秒数
        self._last: datetime | None = None
        self._closed: list[Record] = []                # 已结束未入库的段
        self._persisted: dict[tuple[str, str], int] = {}  # (date, start) -> 已入库秒数
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_app(self) -> str | None:
        """当前正在计时的应用名; 暂停/无前台时为 None."""
        return self._current[1] if self._current else None

    def pending_seconds(self, date_str: str) -> int:
        """某日尚未入库 (或入库后新增) 的秒数, 避免与已入库的开放段重复计数."""
        total = 0
        for rec in self._closed:
            if rec.date == date_str:
                total += rec.seconds - self._persisted.get((rec.date, rec.start), 0)
        if self._current is not None and self._seg_start is not None \
                and self._seg_start.date().isoformat() == date_str:
            key = (self._seg_start.date().isoformat(),
                   self._seg_start.strftime("%H:%M:%S"))
            total += self._seg_seconds - self._persisted.get(key, 0)
        return total

    def pause(self) -> None:
        if not self._paused:
            self._paused = True
            end = self._last if self._last is not None else self._seg_start
            self._close_segment(end)

    def resume(self) -> None:
        self._paused = False

    def tick(self, now: datetime, fg) -> None:
        """每秒调用. fg: ForegroundInfo | None (无前台/不可统计时传 None).

        段内秒数按累计计入; 应用切换/无前台/暂停结束当前段;
        段跨午夜在 00:00:00 拆分, 跨边界秒数计入新日期的新段.
        """
        delta = self._delta(now)
        self._last = now

        if self._current is None:
            self._start_segment(now, fg)
            return

        if now.date() != self._seg_start.date():
            # 跨午夜: 旧段结算到 00:00:00, 新段从零点起并计入跨边界秒数
            boundary = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self._close_segment(boundary)
            self._start_segment(boundary, fg, delta)
            return

        if delta > 0:
            self._seg_seconds += delta

        if self._paused or fg is None or (fg.exe_path, fg.name) != self._current:
            self._close_segment(now)
            self._start_segment(now, fg)

    def flush(self, now: datetime | None = None) -> list[Record]:
        """结算当前段至 now; 返回待入库记录 (已结束段 + 当前段最新状态) 并清空缓冲."""
        if self._current is not None and now is not None:
            delta = self._delta(now)
            if delta > 0:
                self._seg_seconds += delta
            self._last = now
        records = list(self._closed)
        self._closed = []
        if self._current is not None and self._seg_seconds > 0:
            rec = self._open_record()
            records.append(rec)
            self._persisted[(rec.date, rec.start)] = rec.seconds
        else:
            for rec in records:
                self._persisted.pop((rec.date, rec.start), None)
        return records

    def _start_segment(self, now: datetime, fg, initial_seconds: int = 0) -> None:
        if self._paused or fg is None:
            return
        self._current = (fg.exe_path, fg.name)
        self._seg_start = now
        self._seg_seconds = initial_seconds

    def _close_segment(self, end: datetime) -> None:
        if self._current is not None and self._seg_start is not None \
                and self._seg_seconds > 0:
            self._closed.append(Record(
                date=self._seg_start.date().isoformat(),
                start=self._seg_start.strftime("%H:%M:%S"),
                end=end.strftime("%H:%M:%S"),
                app_path=self._current[0],
                app_name=self._current[1],
                seconds=self._seg_seconds))
        self._current = None
        self._seg_start = None
        self._seg_seconds = 0

    def _open_record(self) -> Record:
        end = self._last if self._last is not None else self._seg_start
        return Record(
            date=self._seg_start.date().isoformat(),
            start=self._seg_start.strftime("%H:%M:%S"),
            end=end.strftime("%H:%M:%S"),
            app_path=self._current[0],
            app_name=self._current[1],
            seconds=self._seg_seconds)

    def _delta(self, now: datetime) -> int:
        if self._last is None:
            return 0
        seconds = (now - self._last).total_seconds()
        return max(0, min(int(seconds), MAX_TICK_DELTA))
