"""session.py — 前台使用时长累计 (纯逻辑, 可单测).

每秒调用 tick(now, fg); 应用切换/无前台/暂停时结束当前段;
flush(now) 结算到 now 并返回待入库记录. 不依赖 Win32 / Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# 单次 tick 最大计入秒数: 防休眠/挂起后时间跳变导致虚增
MAX_TICK_DELTA = 60


@dataclass(frozen=True)
class Record:
    date: str       # 'YYYY-MM-DD'
    hour: int       # 0-23, 该段秒数入账的小时
    app_path: str
    app_name: str
    seconds: int


class Tracker:
    """按 tick 增量累计前台应用时长."""

    def __init__(self) -> None:
        self._current: tuple[str, str] | None = None   # (path, name) 当前段
        self._pending: dict[tuple[str, int, str, str], int] = {}  # (date, hour, path, name) -> 秒
        self._last: datetime | None = None
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_app(self) -> str | None:
        """当前正在计时的应用名; 暂停/无前台时为 None."""
        return self._current[1] if self._current else None

    def pending_seconds(self, date_str: str) -> int:
        """缓冲中某日的秒数 (已累计但尚未 flush 入库)."""
        return sum(s for (d, _h, _p, _n), s in self._pending.items() if d == date_str)

    def pause(self) -> None:
        if not self._paused:
            self._paused = True
            self._current = None

    def resume(self) -> None:
        self._paused = False

    def tick(self, now: datetime, fg) -> None:
        """每秒调用. fg: ForegroundInfo | None (无前台/不可统计时传 None).

        段内秒数按 tick 时刻的日期+小时入账 (跨午夜/跨小时按新时间计).
        """
        delta = self._delta(now)
        if self._current is not None and delta > 0:
            key = (now.date().isoformat(), now.hour, self._current[0], self._current[1])
            self._pending[key] = self._pending.get(key, 0) + delta
        self._last = now
        if self._paused or fg is None:
            self._current = None
        else:
            self._current = (fg.exe_path, fg.name)

    def flush(self, now: datetime | None = None) -> list[Record]:
        """结算当前段至 now, 返回全部待入库记录并清空缓冲."""
        if self._current is not None and now is not None:
            delta = self._delta(now)
            if delta > 0:
                key = (now.date().isoformat(), now.hour, self._current[0], self._current[1])
                self._pending[key] = self._pending.get(key, 0) + delta
            self._last = now
        records = [Record(date=d, hour=h, app_path=p, app_name=n, seconds=s)
                   for (d, h, p, n), s in self._pending.items() if s > 0]
        self._pending.clear()
        return records

    def _delta(self, now: datetime) -> int:
        if self._last is None:
            return 0
        seconds = (now - self._last).total_seconds()
        return max(0, min(int(seconds), MAX_TICK_DELTA))
