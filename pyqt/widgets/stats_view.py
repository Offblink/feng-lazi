"""今日使用时段视图: 日期 + 总时长 header + 24 小时甘特图 (每应用一行)."""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from widgets.format import format_duration
from widgets.time_gantt import TimeGantt


class StatsView(QWidget):
    """今日使用时段: 总时长 + 每款应用按精确起止时刻的甘特图; 空日占位."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self._store = store

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.date_label = QLabel(self)
        self.date_label.setObjectName("muted")
        self.total_label = QLabel(self)
        self.total_label.setObjectName("totalTime")
        header.addWidget(self.date_label)
        header.addWidget(self.total_label)
        root.addLayout(header)

        # --- 使用时段甘特图卡片 ---
        # stretch 1: 有数据时铺满剩余页面高度 (甘特行高随可用高度放大);
        # 空态时卡片隐藏, 由下方空态 label 吸收空间.
        self.gantt_card = QFrame(self)
        self.gantt_card.setObjectName("card")
        gantt_layout = QVBoxLayout(self.gantt_card)
        gantt_layout.setContentsMargins(16, 12, 16, 10)
        gantt_layout.setSpacing(8)

        gantt_head = QHBoxLayout()
        gantt_title = QLabel("使用时段", self.gantt_card)
        gantt_title.setObjectName("sectionTitle")
        self.gantt_hint = QLabel("横轴为 24 小时", self.gantt_card)
        self.gantt_hint.setObjectName("appDuration")
        gantt_head.addWidget(gantt_title)
        gantt_head.addStretch(1)
        gantt_head.addWidget(self.gantt_hint)
        gantt_layout.addLayout(gantt_head)

        self.gantt = TimeGantt(parent=self.gantt_card)
        self.gantt_scroll = QScrollArea(self.gantt_card)
        self.gantt_scroll.setWidgetResizable(True)
        self.gantt_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gantt_scroll.setWidget(self.gantt)
        gantt_layout.addWidget(self.gantt_scroll)
        root.addWidget(self.gantt_card, 1)

        self.empty_label = QLabel("今日还没有使用记录", self)
        self.empty_label.setObjectName("appHint")
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
