"""使用时段甘特图: 每款应用一行, 横轴 24 小时 (分钟级精确段).

行 = 应用 (图标 + 名称), 段 = 一次连续使用, 按精确起止时刻定位 (起始点驱动渲染).
悬停到使用段显示 tooltip: 应用 · 起止时刻 · 时长.
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

_MINUTES_PER_DAY = 24 * 60


def seg_times(seg: dict) -> str:
    """tooltip 时段文案: ≥1 分钟用 HH:MM, 更短的段含秒."""
    if seg["seconds"] < 60:
        return f"{seg['start']} - {seg['end']}"
    return f"{seg['start'][:5]} - {seg['end'][:5]}"


class TimeGantt(QWidget):
    ROW_H = 26
    NAME_W = 150
    AXIS_H = 18

    def __init__(self, rows: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self._rows = rows or []
        self.setMouseTracking(True)
        # 垂直 Expanding: 少行时随页面高度放大 (行高铺满), 多行时回到 ROW_H 走滚动.
        # 最小高度 = 内容高度: 视口更矮时保持内容尺寸出现滚动条 (widgetResizable 依赖 qSmartMinSize).
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_min_height()
        self.update()

    def set_rows(self, rows: list[dict]) -> None:
        self._rows = rows
        self._apply_min_height()
        self.update()

    def _apply_min_height(self):
        self.setMinimumHeight(len(self._rows) * self.ROW_H + self.AXIS_H + 4)

    def _row_h(self) -> int:
        """行带高: 少行时用可用高度平分, 多行时保底 ROW_H (滚动)."""
        n = len(self._rows)
        if n == 0:
            return self.ROW_H
        return max(self.ROW_H, (self.height() - self.AXIS_H - 4) // n)

    def sizeHint(self) -> QSize:
        return QSize(420, len(self._rows) * self.ROW_H + self.AXIS_H + 4)

    def _row_at(self, y: float) -> int:
        return int(y) // self._row_h()

    def _minute_at(self, x: int) -> int:
        plot_w = max(self.width() - self.NAME_W, 1)
        minute = int((x - self.NAME_W) / plot_w * _MINUTES_PER_DAY)
        return max(0, min(minute, _MINUTES_PER_DAY - 1))

    def _seg_rect(self, plot_x: int, plot_w: int,
                  start_min: int, end_min: int) -> tuple[int, int]:
        """段矩形 [x0, x1): 起始点驱动; 亚像素段保底 2px 可见."""
        x0 = plot_x + int(plot_w * start_min / _MINUTES_PER_DAY)
        x1 = plot_x + int(plot_w * end_min / _MINUTES_PER_DAY)
        return x0, max(x1, x0 + 2)

    def mouseMoveEvent(self, event):
        row = self._row_at(event.position().y())
        if 0 <= row < len(self._rows):
            app = self._rows[row]
            x = event.position().x()
            plot_w = max(self.width() - self.NAME_W, 1)
            for seg in app["segments"]:
                x0, x1 = self._seg_rect(self.NAME_W, plot_w,
                                        seg["start_min"], seg["end_min"])
                if x0 <= x <= x1:
                    name = os.path.basename(app["app_path"]) or app["app_name"]
                    QToolTip.showText(
                        event.globalPosition().toPoint(),
                        f"{name} · {seg_times(seg)} · {format_duration(seg['seconds'])}",
                        self)
                    return
        QToolTip.hideText()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        plot_x = self.NAME_W
        plot_w = max(w - plot_x, 1)
        rh = self._row_h()
        n = len(self._rows)
        track_h = max(6, rh - 8)   # 轨道随行带高度伸缩
        fm = p.fontMetrics()

        for i, row in enumerate(self._rows):
            cy = i * rh + rh // 2
            name = os.path.basename(row["app_path"]) or row["app_name"]
            elided = fm.elidedText(name, Qt.TextElideMode.ElideRight,
                                   self.NAME_W - 28)

            icon = _ICONS.icon(QFileInfo(row["app_path"])).pixmap(16, 16)
            p.drawPixmap(6, cy - 8, icon)
            p.setPen(QColor(TEXT))
            p.drawText(26, cy + fm.ascent() // 2 - 2, elided)

            # 轨道 + 使用段 (精确起止定位)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(BAR_TRACK))
            p.drawRoundedRect(plot_x, cy - track_h // 2, plot_w, track_h, 4, 4)
            p.setBrush(QColor(ACCENT))
            for seg in row["segments"]:
                x0, x1 = self._seg_rect(plot_x, plot_w,
                                        seg["start_min"], seg["end_min"])
                p.drawRoundedRect(x0, cy - track_h // 2, x1 - x0, track_h, 4, 4)

        # 横轴刻度 0/6/12/18/24
        base_y = n * rh + 2
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
