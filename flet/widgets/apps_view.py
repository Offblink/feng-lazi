"""今日各应用视图: 日期 + 总时长 header + 各应用使用总时长列表 (比例条)."""
from __future__ import annotations

from datetime import date

import flet as ft

from theme import BORDER, SURFACE, TEXT, TEXT_MUTED, RADIUS
from widgets.app_row import app_block
from widgets.format import format_duration


class AppsView:
    """今日各应用使用总时长: 秒数降序的比例条列表; 空日占位."""

    def __init__(self, store) -> None:
        self._store = store

        self._date_label = ft.Text("", size=12, color=TEXT_MUTED)
        self._total_label = ft.Text("", size=34, weight=ft.FontWeight.W_600,
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
        self._empty = ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            content=ft.Text("今日还没有使用记录", size=13, color=TEXT_MUTED),
        )

        self._root = ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Column(spacing=2, controls=[self._date_label,
                                               self._total_label]),
                self._card,
                self._empty,
            ],
        )

    @property
    def control(self) -> ft.Control:
        return self._root

    def refresh(self) -> None:
        today = date.today()
        rows = self._store.daily_breakdown(today.isoformat())

        self._date_label.value = f"{today.month} 月 {today.day} 日"
        self._total_label.value = format_duration(
            self._store.today_total(today.isoformat()))

        blocks: list[ft.Control] = []
        if rows:
            max_seconds = rows[0]["seconds"]
            for i, row in enumerate(rows):
                if i > 0:
                    blocks.append(ft.Divider(height=1, thickness=1,
                                             color=BORDER))
                block = app_block(row["app_path"], row["app_name"],
                                  row["seconds"], max_seconds)
                blocks.append(ft.Container(
                    padding=ft.Padding(left=16, top=10, right=16, bottom=10),
                    content=block))
        self._list.controls = blocks
        self._card.visible = bool(rows)
        self._empty.visible = not bool(rows)
