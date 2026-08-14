"""v4 主题 — qfluentwidgets 集成.

系统深浅色跟随 (Theme.AUTO), 单一深青 accent. 自定义绘制控件 (甘特/比例条)
经 palette() 取当前主题色板, 而非写死 QSS 变量.
"""
from qfluentwidgets import isDarkTheme

# 品牌 accent (深青); 亮暗两版, 暗色用更亮的青保证对比度
ACCENT_LIGHT = "#0F766E"   # teal-700
ACCENT_DARK  = "#14B8A6"   # teal-500

# 亮色: 锌灰中性 (沿用 v3 设计令牌)
_LIGHT = {
    "text":       "#18181B",
    "text_muted": "#71717A",
    "track":      "#F4F4F5",
    "border":     "#E4E4E7",
    "accent":     ACCENT_LIGHT,
}

# 暗色: 近黑背景 + 亮青
_DARK = {
    "text":       "#F2F2F2",
    "text_muted": "#A0A0A0",
    "track":      "#303030",
    "border":     "#3A3A3A",
    "accent":     ACCENT_DARK,
}


def palette() -> dict:
    """当前主题色板 (自定义绘制用)."""
    return _DARK if isDarkTheme() else _LIGHT


def accent() -> str:
    """当前主题 accent 色."""
    return palette()["accent"]
