"""今日统计视图: 日期 + 总时长 header, 时间分布卡片, 应用比例条列表."""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from theme import BORDER
from widgets.app_row import AppRow
from widgets.format import format_duration
from widgets.hour_bars import HourBars, HOURS


class StatsView(QWidget):
    """今日统计: 总时长 + 24 小时分布 + 各应用比例条列表."""

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

        # --- 时间分布卡片 ---
        self.dist_card = QFrame(self)
        self.dist_card.setObjectName("card")
        dist_layout = QVBoxLayout(self.dist_card)
        dist_layout.setContentsMargins(16, 12, 16, 10)
        dist_layout.setSpacing(8)

        dist_head = QHBoxLayout()
        dist_title = QLabel("时间分布", self.dist_card)
        dist_title.setObjectName("sectionTitle")
        self.peak_label = QLabel(self.dist_card)
        self.peak_label.setObjectName("appDuration")
        dist_head.addWidget(dist_title)
        dist_head.addStretch(1)
        dist_head.addWidget(self.peak_label)
        dist_layout.addLayout(dist_head)

        self.hour_bars = HourBars(parent=self.dist_card)
        dist_layout.addWidget(self.hour_bars)
        root.addWidget(self.dist_card)

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
        self._refresh_distribution(today.isoformat())

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

    def _refresh_distribution(self, date_str: str):
        hours = self._store.hourly_breakdown(date_str)
        self.hour_bars.set_hours([h["seconds"] for h in hours])
        peak_hour, peak_secs = max(
            ((h["hour"], h["seconds"]) for h in hours), key=lambda x: x[1])
        if peak_secs > 0:
            self.peak_label.setText(
                f"峰值 {peak_hour}-{peak_hour + 1} 时 · {format_duration(peak_secs)}")
        else:
            self.peak_label.setText("")

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
