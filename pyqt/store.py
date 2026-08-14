"""store.py — SQLite 持久化 (WAL, 增量 upsert).

表: segments(date, start, end, app_path, app_name, seconds), 主键 (date, start, app_path).
v3 起按连续使用段记录精确起止时刻 (HH:MM:SS); v2 旧库 (仅小时维度) 无法还原分钟
→ 自动备份为 .v2.bak 后重建.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS segments (
    date     TEXT    NOT NULL,   -- 段开始日期 'YYYY-MM-DD'
    start    TEXT    NOT NULL,   -- 'HH:MM:SS' 段开始时刻
    end      TEXT    NOT NULL,   -- 'HH:MM:SS' 段结束时刻 ('00:00:00' = 次日零点)
    app_path TEXT    NOT NULL,
    app_name TEXT    NOT NULL,
    seconds  INTEGER NOT NULL,
    PRIMARY KEY (date, start, app_path)
);
"""


def _parse_minute(t: str) -> int:
    """'HH:MM:SS' → 自零点分钟数."""
    h, m, _s = t.split(":")
    return int(h) * 60 + int(m)


class Store:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate_legacy()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _migrate_legacy(self) -> None:
        """v1/v2 旧库 (usage 表) 整体备份后重建, 避免无法还原精确时刻的旧数据混入."""
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='usage'"
        ).fetchone()
        if not row:
            return
        columns = [r[1] for r in self.conn.execute("PRAGMA table_info(usage)")]
        suffix = ".v2.bak" if "hour" in columns else ".v1.bak"
        self.conn.close()
        for suf in ("", "-wal", "-shm"):
            src = self._db_path + suf
            if os.path.exists(src):
                os.replace(src, src + suffix)
        self.conn = sqlite3.connect(self._db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")

    def add_records(self, records) -> None:
        """增量 upsert: 段行按 (date, start, app_path) 整体覆盖.

        当前开放段每 10s 以最新 (end, seconds) 刷新同一行, 覆盖而非累加.
        """
        for r in records:
            if r.seconds <= 0:
                continue
            self.conn.execute(
                "INSERT INTO segments(date, start, end, app_path, app_name, seconds) "
                "VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(date, start, app_path) DO UPDATE SET "
                "end=excluded.end, seconds=excluded.seconds, app_name=excluded.app_name",
                (r.date, r.start, r.end, r.app_path, r.app_name, r.seconds))
        self.conn.commit()

    def today_total(self, date_str: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(seconds), 0) FROM segments WHERE date = ?",
            (date_str,)).fetchone()
        return int(row[0])

    def app_segments(self, date_str: str) -> list[dict]:
        """某日各应用的精确时段 (甘特图数据): 总秒数降序.

        每项含 segments: 按开始时刻排序的段列表, 每段为
        {start_min, end_min (自零点分钟数; end '00:00:00' → 1440),
         seconds, start, end (HH:MM:SS 原串, 供 tooltip)}.
        """
        rows = self.conn.execute(
            "SELECT app_path, app_name, start, end, seconds FROM segments "
            "WHERE date = ? ORDER BY start", (date_str,)).fetchall()
        apps: dict[str, dict] = {}
        for path, name, start, end, secs in rows:
            item = apps.setdefault(path, {"app_path": path, "app_name": name,
                                          "seconds": 0, "segments": []})
            item["segments"].append({
                "start_min": _parse_minute(start),
                "end_min": 1440 if end == "00:00:00" else _parse_minute(end),
                "seconds": int(secs),
                "start": start,
                "end": end,
            })
            item["seconds"] += int(secs)
        return sorted(apps.values(), key=lambda a: a["seconds"], reverse=True)

    def daily_breakdown(self, date_str: str) -> list[dict]:
        """某日各应用时长 (跨段聚合), 秒数降序."""
        rows = self.conn.execute(
            "SELECT app_path, app_name, SUM(seconds) FROM segments WHERE date = ? "
            "GROUP BY app_path ORDER BY SUM(seconds) DESC",
            (date_str,)).fetchall()
        return [{"app_path": p, "app_name": n, "seconds": int(s)} for p, n, s in rows]

    def last_n_days(self, n: int, end_date: date) -> list[dict]:
        """最近 n 天每日总时长 (含无数据的天, seconds=0)."""
        start = end_date - timedelta(days=n - 1)
        rows = self.conn.execute(
            "SELECT date, SUM(seconds) FROM segments WHERE date BETWEEN ? AND ? GROUP BY date",
            (start.isoformat(), end_date.isoformat())).fetchall()
        by_date = {d: int(s) for d, s in rows}
        return [{"date": (start + timedelta(days=i)).isoformat(),
                 "seconds": by_date.get((start + timedelta(days=i)).isoformat(), 0)}
                for i in range(n)]

    def close(self) -> None:
        self.conn.close()
