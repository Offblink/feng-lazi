"""使用时段甘特图 (Flet): 每应用一行, 横轴 24 小时, 分钟级精确段.

行 = 应用 (图标 + 名称); 段 = 一次连续使用, 按精确起止时刻定位 (起始点驱动).
段矩形用像素坐标 (自 Flet 客户端不支持百分比定位, 见 PLAN.md 风险记录):
track_w 由视图按窗口宽度计算, 与 PyQt 版 _seg_rect 语义一致 (亚像素段保底 2px).
悬停到使用段显示 tooltip: 应用 · 起止时刻 · 时长.
"""
from __future__ import annotations

import os

import flet as ft

from theme import ACCENT, BAR_TRACK, TEXT, TEXT_MUTED
from widgets.format import format_duration
from widgets.icons import app_icon

MINUTES_PER_DAY = 24 * 60
NAME_W = 150       # 名称列宽
ROW_H = 26         # 行高
TRACK_H = 10       # 轨道高
AXIS_H = 18        # 横轴高
MIN_SEG_W = 2      # 亚像素段保底宽度


def seg_times(seg: dict) -> str:
    """tooltip 时段文案: ≥1 分钟用 HH:MM, 更短的段含秒."""
    if seg["seconds"] < 60:
        return f"{seg['start']} - {seg['end']}"
    return f"{seg['start'][:5]} - {seg['end'][:5]}"


def seg_rect(start_min: int, end_min: int, track_w: int,
             min_w: int = MIN_SEG_W) -> tuple[int, int]:
    """段矩形 [x0, x1): 起始点驱动; 亚像素段保底 min_w px."""
    x0 = int(track_w * start_min / MINUTES_PER_DAY)
    x1 = int(track_w * end_min / MINUTES_PER_DAY)
    return x0, max(x1, x0 + min_w)


def axis_labels(track_w: int) -> ft.Row:
    """横轴刻度 0/6/12/18/24, 定位到轨道等宽范围."""
    labels = []
    for h in (0, 6, 12, 18, 24):
        x = int(track_w * h / 24)
        labels.append(
            ft.Container(
                width=40,
                alignment=ft.Alignment.CENTER_LEFT if h == 0 else (
                    ft.Alignment.CENTER_RIGHT if h == 24 else ft.Alignment.CENTER),
                margin=ft.Padding(left=max(0, x - 20), top=0, right=0, bottom=0),
                content=ft.Text(str(h), size=10, color=TEXT_MUTED),
            ))
    return ft.Row(spacing=0, controls=labels)


def _track(app: dict, track_w: int) -> ft.Stack:
    """24 小时轨道 + 使用段 (像素定位)."""
    controls = [
        ft.Container(bgcolor=BAR_TRACK, border_radius=TRACK_H // 2,
                     expand=True, height=TRACK_H),
    ]
    for seg in app["segments"]:
        x0, x1 = seg_rect(seg["start_min"], seg["end_min"], track_w)
        name = os.path.basename(app["app_path"]) or app["app_name"]
        seg_box = ft.Container(
            bgcolor=ACCENT,
            border_radius=TRACK_H // 2,
            left=x0,
            width=x1 - x0,
            height=TRACK_H,
            tooltip=f"{name} · {seg_times(seg)} · {format_duration(seg['seconds'])}",
        )
        controls.append(seg_box)
    return ft.Stack(height=TRACK_H, controls=controls)


def gantt_row(app: dict, track_w: int) -> ft.Row:
    """单个应用一行: 图标 + 名称 + 轨道段."""
    name = os.path.basename(app["app_path"]) or app["app_name"]
    icon_uri = app_icon(app["app_path"], name)
    return ft.Row(
        spacing=0,
        height=ROW_H,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                width=NAME_W,
                spacing=8,
                controls=[
                    ft.Image(src=icon_uri, width=16, height=16,
                             fit=ft.BoxFit.CONTAIN),
                    ft.Text(name, size=12, color=TEXT, max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
            ),
            _track(app, track_w),
        ],
    )


def gantt(rows: list[dict], track_w: int) -> ft.Column:
    """甘特图: 应用行列表 + 底部横轴."""
    return ft.Column(
        spacing=0,
        controls=[gantt_row(r, track_w) for r in rows]
                 + [ft.Container(height=AXIS_H, content=axis_labels(track_w))],
    )
