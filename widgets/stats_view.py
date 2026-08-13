"""今日统计视图: 日期 + 总时长 header, 使用时段甘特图, 应用比例条列表."""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from theme import BORDER
from widgets.app_row import AppRow
from widgets.format import format_duration
from widgets.time_gantt import TimeGantt


class StatsView(QWidget):
    """今日统计: 总时长 + 每款应用的时段甘特图 + 各应用比例条列表."""

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
        self.gantt_scroll.setMaximumHeight(TimeGantt.ROW_H * 6 + TimeGantt.AXIS_H + 6)
        self.gantt_scroll.setWidget(self.gantt)
        gantt_layout.addWidget(self.gantt_scroll)
        root.addWidget(self.gantt_card)

        # --- 应用列表卡片 ---
        self.card = QFrame(self)
        self.card.setObjectName("card")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(0, 4, 0, 4)
        self.card_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidget(self.card)
        root.addWidget(self.scroll, 1)

        self.empty_label = QLabel("今日还没有使用记录", self)
        self.empty_label.setObjectName("appHint")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        root.addWidget(self.empty_label, 1)

        self.refresh()

    def refresh(self):
        today = date.today()
        total = self._store.today_total(today.isoformat())
        rows = self._store.daily_breakdown(today.isoformat())

        self.date_label.setText(f"{today.month} 月 {today.day} 日")
        self.total_label.setText(format_duration(total))
        self._refresh_gantt(today.isoformat())

        self._clear_card()
        if rows:
            self.empty_label.hide()
            self.scroll.show()
            self.card.show()
            max_seconds = rows[0]["seconds"]
            for i, row in enumerate(rows):
                if i > 0:
                    self.card_layout.addWidget(self._separator())
                self.card_layout.addWidget(AppRow(
                    row["app_path"], row["app_name"], row["seconds"],
                    max_seconds, self.card))
        else:
            self.scroll.hide()
            self.card.hide()
            self.empty_label.show()

    def _refresh_gantt(self, date_str: str):
        apps = self._store.app_segments(date_str)
        self.gantt.set_rows(apps)
        self.gantt_card.setVisible(bool(apps))

    def _clear_card(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _separator(self) -> QFrame:
        sep = QFrame(self.card)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {BORDER}; border: none;")
        return sep
