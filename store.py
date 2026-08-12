"""store.py — SQLite 持久化 (WAL, 增量 upsert).

表: usage(date, app_path, app_name, seconds), 主键 (date, app_path).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    date     TEXT    NOT NULL,
    app_path TEXT    NOT NULL,
    app_name TEXT    NOT NULL,
    seconds  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, app_path)
);
"""


class Store:
    def __init__(self, db_path: str) -> None:
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add_records(self, records) -> None:
        """增量 upsert: 同 (date, app_path) 累加秒数, 更新展示名."""
        for r in records:
            if r.seconds <= 0:
                continue
            self.conn.execute(
                "INSERT INTO usage(date, app_path, app_name, seconds) VALUES(?,?,?,?) "
                "ON CONFLICT(date, app_path) DO UPDATE SET "
                "seconds = usage.seconds + excluded.seconds, app_name = excluded.app_name",
                (r.date, r.app_path, r.app_name, r.seconds))
        self.conn.commit()

    def today_total(self, date_str: str) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(seconds), 0) FROM usage WHERE date = ?",
            (date_str,)).fetchone()
        return int(row[0])

    def daily_breakdown(self, date_str: str) -> list[dict]:
        """某日各应用时长, 秒数降序."""
        rows = self.conn.execute(
            "SELECT app_path, app_name, seconds FROM usage WHERE date = ? "
            "ORDER BY seconds DESC",
            (date_str,)).fetchall()
        return [{"app_path": p, "app_name": n, "seconds": s} for p, n, s in rows]

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
