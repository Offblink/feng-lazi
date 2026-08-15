"""近 7 天视图: 每日总时长 + 当日 top 3 应用; 空日占位."""
from datetime import date

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from theme import BORDER
from widgets.app_row import display_name
from widgets.format import format_duration

_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
TOP_N = 3


def _day_label(day: date) -> str:
    if day == date.today():
        return "今天"
    return f"{_WEEKDAYS[day.weekday()]} {day.month} 月 {day.day} 日"


class AppLine(QWidget):
    """一行: 应用名 + 时长 (次要文本)."""

    def __init__(self, app_path: str, app_name: str, seconds: int, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 2, 16, 2)
        lay.setSpacing(10)
        name = QLabel(display_name(app_path, app_name), self)
        name.setObjectName("appName")
        duration = QLabel(format_duration(seconds), self)
        duration.setObjectName("appDuration")
        lay.addWidget(name, 1)
        lay.addWidget(duration)


class DayBlock(QWidget):
    """一天: 日期 + 总时长, 下方 top 应用或占位."""

    def __init__(self, day: date, total: int, top: list[dict], parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(6)

        head = QHBoxLayout()
        day_label = QLabel(_day_label(day), self)
        day_label.setObjectName("sectionTitle")
        total_label = QLabel(format_duration(total), self)
        total_label.setObjectName("appDuration")
        head.addWidget(day_label)
        head.addStretch(1)
        head.addWidget(total_label)
        lay.addLayout(head)

        if top:
            for row in top:
                lay.addWidget(AppLine(row["app_path"], row["app_name"],
                                      row["seconds"], self))
        else:
            empty = QLabel("无使用记录", self)
            empty.setObjectName("appHint")
            lay.addWidget(empty)


class HistoryView(QWidget):
    """近 7 天统计: 卡片内逐日区块."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self._store = store

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("近 7 天", self)
        title.setObjectName("sectionTitle")
        root.addWidget(title)

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

        self.refresh()

    def refresh(self):
        self._clear()
        days = self._store.last_n_days(7, date.today())
        for i, day in enumerate(days):
            if i > 0:
                self.card_layout.addWidget(self._separator())
            d = date.fromisoformat(day["date"])
            top = self._store.daily_breakdown(day["date"])[:TOP_N]
            self.card_layout.addWidget(DayBlock(d, day["seconds"], top, self.card))

    def _clear(self):
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
