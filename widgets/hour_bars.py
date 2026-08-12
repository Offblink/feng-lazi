"""时间分布条: 今日 24 小时柱状图 (自定义绘制, Minimal & Clean)."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from theme import ACCENT, BAR_TRACK, TEXT_MUTED

HOURS = 24


class HourBars(QWidget):
    """24 根柱: 每根高度 = 该小时秒数 / 当日峰值. 底部 0/6/12/18/24 刻度."""

    def __init__(self, hours: list[int] | None = None, parent=None):
        super().__init__(parent)
        self._hours = hours or [0] * HOURS
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_hours(self, hours: list[int]) -> None:
        self._hours = list(hours)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        label_h = 16
        plot_h = h - label_h - 4
        max_v = max(self._hours) or 1
        gap = 2
        bar_w = (w - gap * (HOURS - 1)) / HOURS

        p.setPen(Qt.PenStyle.NoPen)
        for i, secs in enumerate(self._hours):
            x = int(i * (bar_w + gap))
            bw = max(int(bar_w), 1)
            p.setBrush(QColor(BAR_TRACK))
            p.drawRoundedRect(x, 0, bw, plot_h, 2, 2)
            if secs > 0:
                bar_h = max(int(plot_h * secs / max_v), 3)
                p.setBrush(QColor(ACCENT))
                p.drawRoundedRect(x, plot_h - bar_h, bw, bar_h, 2, 2)

        p.setPen(QColor(TEXT_MUTED))
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)
        for label in (0, 6, 12, 18, 24):
            x = label / HOURS * w
            text = str(label)
            if label == 0:
                rect = (int(x), plot_h + 2, 24, label_h)
            elif label == HOURS:
                rect = (int(x) - 24, plot_h + 2, 24, label_h)
            else:
                rect = (int(x) - 12, plot_h + 2, 24, label_h)
            p.drawText(*rect, Qt.AlignmentFlag.AlignHCenter, text)
        p.end()
