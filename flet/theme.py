"""theme.py — Flet 主题令牌 (taste skill: Minimal & Clean 浅色预设).

VARIANCE=4 / MOTION=2 / DENSITY=4. 锌灰中性色 + 单一深青 accent, 全程贯穿.
色板与 ../pyqt/theme.py 对齐 (Segoe UI Variable, 8px 圆角, 无渐变无阴影堆砌).
"""
from __future__ import annotations

import flet as ft

# --- 色板: 锌灰中性 + 单一深青 accent ---
BG          = "#FAFAF9"   # 页面背景
SURFACE     = "#FFFFFF"   # 卡片/列表背景
BORDER      = "#E4E4E7"   # 描边/分隔线
TEXT        = "#18181B"   # 主文本
TEXT_MUTED  = "#71717A"   # 次要文本
BAR_TRACK   = "#F4F4F5"   # 比例条轨道
BAR_FILL    = "#0F766E"   # 比例条填充 (同 accent)
HOVER       = "#F4F4F5"   # 悬停底色
ACCENT      = "#0F766E"   # 深青 (teal-700) — 唯一 accent

# --- 排版 / 圆角 (8px 网格) ---
FONT_FAMILY = "Segoe UI Variable"   # Win11 原生; Flutter 缺失时自动回退
RADIUS      = 8
PAGE_PAD    = 24


def build_theme() -> ft.Theme:
    """应用级主题: 色板 + 字体 + 卡片/列表样式."""
    return ft.Theme(
        font_family=FONT_FAMILY,
        use_material3=True,
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary="#FFFFFF",
            primary_container=HOVER,
            on_primary_container=TEXT,
            secondary=TEXT_MUTED,
            surface=SURFACE,
            on_surface=TEXT,
            on_surface_variant=TEXT_MUTED,
            outline=BORDER,
            outline_variant=BORDER,
            surface_container_lowest=SURFACE,
            surface_container_low=HOVER,
            surface_container=HOVER,
            surface_container_high=BORDER,
            surface_container_highest=BORDER,
        ),
    )
