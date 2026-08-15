"""今日使用时段页: 日期 + 总时长 header + 24 小时甘特图 (铺满剩余高度)."""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from qfluentwidgets import CaptionLabel, CardWidget, DisplayLabel, StrongBodyLabel

from widgets.format import format_duration
from widgets.time_gantt import TimeGantt


def _make_scroll(parent=None) -> QScrollArea:
    """透明滚动区: 卡片内不画背景."""
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.viewport().setAutoFillBackground(False)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    return scroll


class GanttPage(QWidget):
    """今日使用时段: 总时长 + 每款应用按精确起止时刻的甘特图; 空日占位."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setObjectName("GanttPage")
        self._store = store

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.date_label = CaptionLabel(self)
        self.date_label.setObjectName("muted")
        self.total_label = DisplayLabel("0 秒", self)
        header.addWidget(self.date_label)
        header.addWidget(self.total_label)
        root.addLayout(header)

        # --- 使用时段甘特图卡片 (stretch 1: 铺满剩余页面高度) ---
        self.gantt_card = CardWidget(self)
        gantt_layout = QVBoxLayout(self.gantt_card)
        gantt_layout.setContentsMargins(20, 14, 20, 12)
        gantt_layout.setSpacing(8)

        gantt_head = QHBoxLayout()
        gantt_title = StrongBodyLabel("使用时段", self.gantt_card)
        self.gantt_hint = CaptionLabel("横轴为 24 小时", self.gantt_card)
        gantt_head.addWidget(gantt_title)
        gantt_head.addStretch(1)
        gantt_head.addWidget(self.gantt_hint)
        gantt_layout.addLayout(gantt_head)

        self.gantt = TimeGantt(parent=self.gantt_card)
        self.gantt_scroll = _make_scroll(self.gantt_card)
        self.gantt_scroll.setWidget(self.gantt)
        gantt_layout.addWidget(self.gantt_scroll, 1)
        root.addWidget(self.gantt_card, 1)

        self.empty_label = CaptionLabel("今日还没有使用记录", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        root.addWidget(self.empty_label, 1)

        self.refresh()

    def refresh(self):
        today = date.today()
        apps = self._store.app_segments(today.isoformat())

        self.date_label.setText(f"{today.month} 月 {today.day} 日")
        self.total_label.setText(format_duration(self._store.today_total(today.isoformat())))
        self.gantt.set_rows(apps)
        self.gantt_card.setVisible(bool(apps))
        self.empty_label.setVisible(not bool(apps))
