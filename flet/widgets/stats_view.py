"""今日使用时段视图: 日期 + 总时长 header + 24 小时甘特图 (每应用一行)."""
from __future__ import annotations

from datetime import date

import flet as ft

from theme import BORDER, SURFACE, TEXT, TEXT_MUTED, RADIUS
from widgets import time_gantt
from widgets.format import format_duration

# 轨道宽 = 窗口宽 - 页面左右 padding(24*2) - 卡片 padding(16*2) - 名称列(150)
TRACK_PAD = 24 * 2 + 16 * 2 + time_gantt.NAME_W


def _card(content: ft.Control) -> ft.Container:
    return ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=RADIUS,
        padding=ft.Padding(left=16, top=16, right=16, bottom=16),
        content=content,
    )


class StatsView:
    """今日使用时段: 总时长 + 每款应用按精确起止时刻的甘特图; 空日占位."""

    def __init__(self, store) -> None:
        self._store = store
        self._track_w = 300

        self._date_label = ft.Text("", size=12, color=TEXT_MUTED)
        self._total_label = ft.Text("", size=34, weight=ft.FontWeight.W_600,
                                    color=TEXT)
        self._gantt_list = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO,
                                     expand=True)
        gantt_head = ft.Row(
            controls=[
                ft.Text("使用时段", size=13, weight=ft.FontWeight.W_600,
                        color=TEXT),
                ft.Container(expand=True),
                ft.Text("横轴为 24 小时", size=11, color=TEXT_MUTED),
            ])
        self._gantt_card = _card(ft.Column(
            spacing=8,
            controls=[gantt_head, self._gantt_list],
        ))
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
                self._gantt_card,
                self._empty,
            ],
        )

    @property
    def control(self) -> ft.Control:
        return self._root

    def refresh(self, page_width: int | None = None) -> None:
        today = date.today()
        apps = self._store.app_segments(today.isoformat())
        if page_width is not None:
            self._track_w = max(200, page_width - TRACK_PAD)

        self._date_label.value = f"{today.month} 月 {today.day} 日"
        self._total_label.value = format_duration(
            self._store.today_total(today.isoformat()))
        self._gantt_list.controls = (
            [time_gantt.gantt(apps, self._track_w)] if apps else [])
        self._gantt_card.visible = bool(apps)
        self._empty.visible = not bool(apps)
