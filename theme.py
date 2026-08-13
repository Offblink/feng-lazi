"""theme.py — 设计令牌 (taste skill: Minimal & Clean 浅色预设).

VARIANCE=4 / MOTION=2 / DENSITY=4. 锌灰中性色 + 单一深青 accent, 全程贯穿.
Windows 11 Fluent 风格近似: Segoe UI Variable, 8px 圆角, 无渐变无阴影堆砌.
"""
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

# --- 色板: 锌灰中性 + 单一深青 accent ---
BG          = "#FAFAF9"   # 窗口背景
SURFACE     = "#FFFFFF"   # 卡片/列表背景
BORDER      = "#E4E4E7"   # 描边/分隔线
TEXT        = "#18181B"   # 主文本
TEXT_MUTED  = "#71717A"   # 次要文本
BAR_TRACK   = "#F4F4F5"   # 比例条轨道
BAR_FILL    = "#0F766E"   # 比例条填充 (同 accent)
HOVER       = "#F4F4F5"   # 悬停底色
ACCENT      = "#0F766E"   # 深青 (teal-700) — 唯一 accent

# --- 排版 ---
FONT_FAMILY = "Segoe UI Variable"  # Win11 原生; 缺失时 Qt 自动回退
SECTION_PT  = 13          # 区块标题
BODY_PT     = 10          # 正文
MUTED_PT    = 9           # 次要文本

# --- 间距 / 圆角 (8px 网格) ---
RADIUS      = 8
MARGIN      = 24

QSS = f"""
QMainWindow, QDialog, QWidget {{ background: {BG}; color: {TEXT}; }}
QLabel {{ background: transparent; }}
QLabel#appHint  {{ color: {TEXT_MUTED}; font-size: {MUTED_PT}pt; }}
QLabel#sectionTitle {{ font-size: {SECTION_PT}pt; font-weight: 600; color: {TEXT}; }}
QLabel#totalTime {{ font-size: 34pt; font-weight: 600; color: {TEXT}; }}
QLabel#muted {{ color: {TEXT_MUTED}; font-size: {MUTED_PT}pt; }}
QLabel#appName {{ font-weight: 500; }}
QLabel#appDuration {{ color: {TEXT_MUTED}; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {RADIUS}px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; color: {TEXT_MUTED}; padding: 6px 16px;
                border-bottom: 2px solid transparent; font-size: {BODY_PT}pt; }}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ color: {TEXT}; }}
QMenu {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: {RADIUS}px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {HOVER}; }}
QMenu::item:disabled {{ color: {TEXT_MUTED}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
           padding: 4px 8px; font-size: {MUTED_PT}pt; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #D4D4D8; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: #A1A1AA; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #D4D4D8; border-radius: 5px; min-width: 24px; }}
QScrollBar::handle:horizontal:hover {{ background: #A1A1AA; }}
"""


def apply(app: QApplication) -> None:
    font = QFont(FONT_FAMILY)
    font.setPointSize(BODY_PT)
    app.setFont(font)
    app.setStyleSheet(QSS)
