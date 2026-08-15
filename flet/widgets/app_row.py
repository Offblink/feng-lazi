"""应用行 (Flet): 图标 + 名称 + 时长 + 相对比例条."""
from __future__ import annotations

import os

import flet as ft

from theme import BAR_FILL, BAR_TRACK, TEXT, TEXT_MUTED
from widgets.format import format_duration
from widgets.icons import app_icon


def display_name(app_path: str, fallback: str) -> str:
    """展示名: exe 文件名字面量 (保留原始大小写); 路径缺失时用存储名."""
    return os.path.basename(app_path) or fallback


def bar_ratio(seconds: int, max_seconds: int) -> float:
    """比例条填充比例, 钳制到 [0, 1]."""
    if max_seconds <= 0:
        return 0.0
    return max(0.0, min(1.0, seconds / max_seconds))


def bar(ratio: float, height: int = 6) -> ft.Container:
    """比例条: 圆角轨道 + accent 填充 (Row expand 权重, 确定性布局)."""
    ratio = max(0.0, min(1.0, ratio))
    fill_w = round(ratio * 1000)
    children = []
    if fill_w > 0:
        children.append(ft.Container(bgcolor=BAR_FILL, expand=fill_w))
    return ft.Container(
        height=height,
        border_radius=height // 2,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor=BAR_TRACK,
        content=ft.Row(spacing=0, controls=children) if children else None,
    )


def app_row(app_path: str, app_name: str, seconds: int,
            max_seconds: int) -> ft.Row:
    """单个应用一行: 图标 + 名称 + 时长."""
    icon_uri = app_icon(app_path, app_name)
    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Image(src=icon_uri, width=18, height=18,
                     fit=ft.BoxFit.CONTAIN),
            ft.Text(
                display_name(app_path, app_name),
                size=13,
                weight=ft.FontWeight.W_500,
                color=TEXT,
                expand=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Text(format_duration(seconds), size=13, color=TEXT_MUTED),
        ],
    )


def app_block(app_path: str, app_name: str, seconds: int,
              max_seconds: int) -> ft.Column:
    """应用行 + 其下比例条 (今日各应用列表项)."""
    return ft.Column(
        spacing=6,
        controls=[
            app_row(app_path, app_name, seconds, max_seconds),
            bar(bar_ratio(seconds, max_seconds)),
        ],
    )
