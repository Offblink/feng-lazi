"""store.py — SQLite 持久化 (WAL, 增量 upsert).

表: usage(date, hour, app_path, app_name, seconds), 主键 (date, hour, app_path).
v2 起记录小时维度; v1 旧库 (无 hour 列) 无法还原小时 → 自动备份为 .v1.bak 后重建.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    date     TEXT    NOT NULL,
    hour     INTEGER NOT NULL,
    app_path TEXT    NOT NULL,
    app_name TEXT    NOT NULL,
    seconds  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, hour, app_path)
);
"""


class Store:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate_v1()
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def _migrate_v1(self) -> None:
        """旧版 schema (usage 无 hour 列) 整体备份后重建, 避免错误数据混入."""
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='usage'"
        ).fetchone()
        if not row:
            return
        columns = [r[1] for r in self.conn.execute("PRAGMA table_info(usage)")]
        if "hour" in columns:
            return
        self.conn.close()
        for suffix in ("", "-wal", "-shm"):
            src = self._db_path + suffix
            if os.path.exists(src):
                os.replace(src, src + ".v1.bak")
        self.conn = sqlite3.connect(self._db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")

    def add_records(self, records) -> None:
        """增量 upsert: 同 (date, hour, app_path) 累加秒数, 更新展示名."""
        for r in records:
            if r.seconds <= 0:
                continue
            self.conn.execute(
                "INSERT INTO usage(date, hour, app_path, app_name, seconds) "
                "VALUES(?,?,?,?,?) "
                "ON CONFLICT(date, hour, app_path) DO UPDATE SET "
                "seconds = usage.seconds + excluded.seconds, app_name = excluded.app_name",
                (r.date, r.hour, r.app_path, r.app_name, r.seconds))
        self.conn.commit()

    def today_total(self, date_str: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(seconds), 0) FROM usage WHERE date = ?",
            (date_str,)).fetchone()
        return int(row[0])

    def hourly_breakdown(self, date_str: str) -> list[dict]:
        """某日 24 小时各自的累计秒数 (全应用合并), 恒为 24 项."""
        rows = self.conn.execute(
            "SELECT hour, SUM(seconds) FROM usage WHERE date = ? GROUP BY hour",
            (date_str,)).fetchall()
        by_hour = {h: int(s) for h, s in rows}
        return [{"hour": h, "seconds": by_hour.get(h, 0)} for h in range(24)]

    def daily_breakdown(self, date_str: str) -> list[dict]:
        """某日各应用时长 (跨小时聚合), 秒数降序."""
        rows = self.conn.execute(
            "SELECT app_path, app_name, SUM(seconds) FROM usage WHERE date = ? "
            "GROUP BY app_path ORDER BY SUM(seconds) DESC",
            (date_str,)).fetchall()
        return [{"app_path": p, "app_name": n, "seconds": int(s)} for p, n, s in rows]

    def last_n_days(self, n: int, end_date: date) -> list[dict]:
        """最近 n 天每日总时长 (含无数据的天, seconds=0)."""
        start = end_date - timedelta(days=n - 1)
        rows = self.conn.execute(
            "SELECT date, SUM(seconds) FROM usage WHERE date BETWEEN ? AND ? GROUP BY date",
            (start.isoformat(), end_date.isoformat())).fetchall()
        by_date = {d: int(s) for d, s in rows}
        return [{"date": (start + timedelta(days=i)).isoformat(),
                 "seconds": by_date.get((start + timedelta(days=i)).isoformat(), 0)}
                for i in range(n)]

    def close(self) -> None:
        self.conn.close()
