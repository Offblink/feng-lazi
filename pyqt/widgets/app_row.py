"""应用行: 图标 + 名称 + 时长 + 相对比例条 (自定义绘制)."""
import os

from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFileIconProvider, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from theme import BAR_FILL, BAR_TRACK
from widgets.format import format_duration

_ICON_PROVIDER = QFileIconProvider()   # 自带 exe 图标缓存


def display_name(app_path: str, fallback: str) -> str:
    """展示名: exe 文件名字面量 (保留原始大小写); 路径缺失时用存储名."""
    return os.path.basename(app_path) or fallback


class BarWidget(QWidget):
    """6px 高比例条: 轨道 + accent 填充."""

    def __init__(self, ratio: float, parent=None):
        super().__init__(parent)
        self._ratio = max(0.0, min(1.0, ratio))
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        r = self.rect()
        p.setBrush(QColor(BAR_TRACK))
        p.drawRoundedRect(r, 3, 3)
        if self._ratio > 0:
            width = max(int(r.width() * self._ratio), 2)
            p.setBrush(QColor(BAR_FILL))
            p.drawRoundedRect(0, 0, width, r.height(), 3, 3)
        p.end()


class AppRow(QWidget):
    """单个应用的一行统计."""

    def __init__(self, app_path: str, app_name: str, seconds: int,
                 max_seconds: int, parent=None):
        super().__init__(parent)
        ratio = seconds / max_seconds if max_seconds > 0 else 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        icon = QLabel(self)
        icon.setFixedSize(18, 18)
        icon.setPixmap(_ICON_PROVIDER.icon(QFileInfo(app_path)).pixmap(18, 18))
        name = QLabel(display_name(app_path, app_name), self)
        name.setObjectName("appName")
        duration = QLabel(format_duration(seconds), self)
        duration.setObjectName("appDuration")
        top.addWidget(icon)
        top.addWidget(name, 1)
        top.addWidget(duration)
        layout.addLayout(top)

        self.bar = BarWidget(ratio, self)
        layout.addWidget(self.bar)
