"""近 7 天视图: 每日总时长 + 当日 top 3 应用; 空日占位."""
from __future__ import annotations

from datetime import date, timedelta

import flet as ft

from theme import BORDER, SURFACE, TEXT, TEXT_MUTED, RADIUS
from widgets.app_row import display_name
from widgets.format import format_duration

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
TOP_N = 3


def _day_label(day: date) -> str:
    if day == date.today():
        return "今天"
    return f"{_WEEKDAYS[day.weekday()]} {day.month} 月 {day.day} 日"


class HistoryView:
    """近 7 天统计: 卡片内逐日区块."""

    def __init__(self, store) -> None:
        self._store = store

        self._title = ft.Text("近 7 天", size=13, weight=ft.FontWeight.W_600,
                              color=TEXT)
        self._list = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO,
                               expand=True)
        self._card = ft.Container(
            bgcolor=SURFACE,
            border=ft.Border.all(1, BORDER),
            border_radius=RADIUS,
            padding=ft.Padding(left=0, top=4, right=0, bottom=4),
            content=self._list,
        )
        self._root = ft.Column(
            expand=True,
            spacing=12,
            controls=[self._title, self._card],
        )

    @property
    def control(self) -> ft.Control:
        return self._root

    def refresh(self) -> None:
        blocks: list[ft.Control] = []
        days = self._store.last_n_days(7, date.today())
        for i, day in enumerate(days):
            if i > 0:
                blocks.append(ft.Divider(height=1, thickness=1, color=BORDER))
            blocks.append(self._day_block(day))
        self._list.controls = blocks

    def _day_block(self, day: dict) -> ft.Container:
        d = date.fromisoformat(day["date"])
        top = self._store.daily_breakdown(day["date"])[:TOP_N]

        head = ft.Row(
            controls=[
                ft.Text(_day_label(d), size=13, weight=ft.FontWeight.W_600,
                        color=TEXT),
                ft.Container(expand=True),
                ft.Text(format_duration(day["seconds"]), size=12,
                        color=TEXT_MUTED),
            ])
        lines: list[ft.Control] = [head]
        if top:
            for row in top:
                name = ft.Text(display_name(row["app_path"], row["app_name"]),
                               size=13, weight=ft.FontWeight.W_500, color=TEXT,
                               expand=True, max_lines=1,
                               overflow=ft.TextOverflow.ELLIPSIS)
                duration = ft.Text(format_duration(row["seconds"]), size=13,
                                   color=TEXT_MUTED)
                lines.append(ft.Row(spacing=10, controls=[name, duration]))
        else:
            lines.append(ft.Text("无使用记录", size=12, color=TEXT_MUTED))

        return ft.Container(
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            content=ft.Column(spacing=6, controls=lines),
        )
