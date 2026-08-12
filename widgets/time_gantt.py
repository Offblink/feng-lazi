"""使用时段甘特图: 每款应用一行, 横轴 24 小时.

行 = 应用 (图标 + 名称 + 总时长), 列 = 小时; 连续使用的相邻小时合并为一段.
悬停到有数据的时段显示 tooltip: 应用 · 时段 · 时长.
"""
import os

from PyQt6.QtCore import QFileInfo, QSize, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFileIconProvider, QSizePolicy, QToolTip, QWidget,
)

from theme import ACCENT, BAR_TRACK, TEXT, TEXT_MUTED
from widgets.format import format_duration

_ICONS = QFileIconProvider()


def spans_from_hours(hours: list[int]) -> list[tuple[int, int]]:
    """连续非零小时合并为 [start, end) 时段段列表."""
    spans: list[tuple[int, int]] = []
    start = None
    for hour, secs in enumerate(hours):
        if secs > 0 and start is None:
            start = hour
        elif secs == 0 and start is not None:
            spans.append((start, hour))
            start = None
    if start is not None:
        spans.append((start, len(hours)))
    return spans


class TimeGantt(QWidget):
    ROW_H = 26
    NAME_W = 150
    AXIS_H = 18

    def __init__(self, rows: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_height()

    def set_rows(self, rows: list[dict]) -> None:
        self._rows = rows
        self._apply_height()
        self.update()

    def _apply_height(self):
        self.setFixedHeight(len(self._rows) * self.ROW_H + self.AXIS_H + 4)

    def sizeHint(self) -> QSize:
        return QSize(420, len(self._rows) * self.ROW_H + self.AXIS_H + 4)

    def _row_at(self, y: int) -> int:
        return y // self.ROW_H

    def _hour_at(self, x: int) -> int:
        plot_w = max(self.width() - self.NAME_W, 1)
        hour = int((x - self.NAME_W) / plot_w * 24)
        return max(0, min(hour, 23))

    def mouseMoveEvent(self, event):
        row = self._row_at(event.position().y())
        if 0 <= row < len(self._rows):
            app = self._rows[row]
            hour = self._hour_at(event.position().x())
            secs = app["hours"][hour]
            if secs > 0:
                name = os.path.basename(app["app_path"]) or app["app_name"]
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{name} · {hour}-{hour + 1} 时 · {format_duration(secs)}",
                    self)
                return
        QToolTip.hideText()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        plot_x = self.NAME_W
        plot_w = max(w - plot_x, 1)
        fm = p.fontMetrics()

        for i, row in enumerate(self._rows):
            cy = i * self.ROW_H + self.ROW_H // 2
            name = os.path.basename(row["app_path"]) or row["app_name"]
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight,
                                   self.NAME_W - 28)

            icon = _ICONS.icon(QFileInfo(row["app_path"])).pixmap(16, 16)
            p.drawPixmap(6, cy - 8, icon)
            p.setPen(QColor(TEXT))
            p.drawText(26, cy + fm.ascent() // 2 - 2, elided)

            # 轨道 + 使用段
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(BAR_TRACK))
            p.drawRoundedRect(plot_x, cy - 4, plot_w, 8, 4, 4)
            p.setBrush(QColor(ACCENT))
            for start, end in spans_from_hours(row["hours"]):
                x0 = plot_x + int(plot_w * start / 24)
                x1 = plot_x + int(plot_w * end / 24)
                p.drawRoundedRect(x0, cy - 4, max(x1 - x0, 2), 8, 4, 4)

        # 横轴刻度 0/6/12/18/24
        base_y = len(self._rows) * self.ROW_H + 2
        p.setPen(QColor(TEXT_MUTED))
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)
        for label in (0, 6, 12, 18, 24):
            x = plot_x + int(plot_w * label / 24)
            if label == 0:
                rect = (plot_x, base_y, 20, self.AXIS_H)
            elif label == 24:
                rect = (x - 20, base_y, 20, self.AXIS_H)
            else:
                rect = (x - 10, base_y, 20, self.AXIS_H)
            p.drawText(*rect, Qt.AlignmentFlag.AlignHCenter, str(label))
        p.end()
