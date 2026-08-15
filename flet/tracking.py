"""tracking.py — 前台跟踪编排 (纯逻辑, 可单测).

对应 PyQt 版 TrayApp._on_tick / _flush / _today_seconds 的内联逻辑:
每秒 step(now, fg); 应用切换立即 flush, 每 FLUSH_EVERY_TICKS 定期 flush;
暂停/恢复透传 Tracker; today_seconds = 已入库 + pending.
不依赖 Flet / Win32 (fg 由调用方先用 is_trackable 过滤).
"""
from __future__ import annotations

from datetime import date, datetime

from session import Tracker
from store import Store

FLUSH_EVERY_TICKS = 10   # 每 10 秒定期入库


def is_trackable(fg, self_pid: int | None = None) -> bool:
    """是否计入统计: 无前台 / 自身进程 / 桌面与托盘等系统窗口 → False."""
    if fg is None:
        return False
    if self_pid is not None and fg.pid == self_pid:
        return False
    import foreground
    return foreground.is_trackable(fg)


class TrackerLoop:
    """节拍编排: 持有 Tracker + Store, 提供 step/flush/today_seconds."""

    def __init__(self, store: Store, tracker: Tracker | None = None,
                 flush_every: int = FLUSH_EVERY_TICKS) -> None:
        self._store = store
        self._tracker = tracker or Tracker()
        self._flush_every = max(1, flush_every)
        self._tick_count = 0
        self._last_app_path: str | None = None

    # ---------- 状态透传 ----------
    @property
    def is_paused(self) -> bool:
        return self._tracker.is_paused

    @property
    def current_app(self) -> str | None:
        return self._tracker.current_app

    def pause(self) -> None:
        self._tracker.pause()

    def resume(self) -> None:
        self._tracker.resume()

    # ---------- 节拍 ----------
    def step(self, now: datetime, fg) -> list:
        """每秒一步. fg: 已过滤 (None 表示无前台/不可统计). 返回本次 flush 的记录."""
        if fg is not None and self._last_app_path is not None \
                and fg.exe_path != self._last_app_path:
            self.flush(now)   # 应用切换: 立即入库
        self._last_app_path = fg.exe_path if fg is not None else None
        self._tracker.tick(now, fg)
        self._tick_count += 1
        if self._tick_count % self._flush_every == 0:
            return self.flush(now)
        return []

    def flush(self, now: datetime | None = None) -> list:
        """结算待入库记录并写入 Store."""
        records = self._tracker.flush(now)
        if records:
            self._store.add_records(records)
        return records

    def today_seconds(self, date_str: str | None = None) -> int:
        """今日总时长 = 已入库 + 尚未入库的开放段/已结束段."""
        ds = date_str or date.today().isoformat()
        return self._store.today_total(ds) + self._tracker.pending_seconds(ds)
