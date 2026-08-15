"""今日各应用页: 日期 + 总时长 header + 各应用使用总时长列表 (比例条)."""
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from qfluentwidgets import CaptionLabel, CardWidget, DisplayLabel

from theme import palette
from widgets.app_row import AppRow
from widgets.format import format_duration
from widgets.gantt_page import _make_scroll


class AppsPage(QWidget):
    """今日各应用使用总时长: 秒数降序的比例条列表; 空日占位."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setObjectName("AppsPage")
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

        # --- 应用列表卡片 ---
        self.card = CardWidget(self)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(0, 8, 0, 8)
        self.card_layout.setSpacing(0)

        self.scroll = _make_scroll(self)
        self.scroll.setWidget(self.card)
        root.addWidget(self.scroll, 1)

        self.empty_label = CaptionLabel("今日还没有使用记录", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()
        root.addWidget(self.empty_label, 1)

        self.refresh()

    def refresh(self):
        today = date.today()
        rows = self._store.daily_breakdown(today.isoformat())

        self.date_label.setText(f"{today.month} 月 {today.day} 日")
        self.total_label.setText(format_duration(self._store.today_total(today.isoformat())))

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

    def _clear_card(self):
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _separator(self) -> QFrame:
        sep = QFrame(self.card)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {palette()['border']}; border: none;")
        return sep
