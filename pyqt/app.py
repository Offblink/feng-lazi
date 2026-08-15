"""凤辣子 — 主应用 (PyQt6).

常驻系统托盘; 托盘交互参照 Get It (源文件/app.py):
  - QSystemTrayIcon + 右键菜单 (显示统计/暂停统计/退出) + 双击恢复
  - closeEvent → 最小化到托盘
  - 退出前清理 (flush 入库 + 隐藏托盘)

实时跟踪: QTimer 每秒探测前台窗口 → Tracker 累计 → 切换/每 10s/退出 flush 入库.
"""
import os
import sys
from datetime import date, datetime

from PyQt6.QtCore import Qt, QSharedMemory, QTimer
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QSystemTrayIcon, QTabWidget,
)

import foreground
from session import Tracker
from store import Store
from widgets.apps_view import AppsView
from widgets.format import format_duration
from widgets.history_view import HistoryView
from widgets.stats_view import StatsView

APP_NAME = "UsageTracker"
APP_NAME_ZH = "凤辣子"   # 应用中文名 (王熙凤绰号)
FLUSH_EVERY_TICKS = 10   # 每 10 秒定期入库
APP_IPC_SINGLETON = "FengLaziSingleton"   # QSharedMemory 单例锁
APP_IPC_SERVER = "FengLaziIPC"            # QLocalServer 唤醒管道


def app_data_dir() -> str:
    """%LOCALAPPDATA%/UsageTracker — 数据目录 (锁文件/数据库)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def make_tray_icon() -> QIcon:
    """应用/托盘图标: 优先 resources/icon.ico (参照 Get It), 缺失时回退运行时绘制."""
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources", "icon.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    return _draw_fallback_icon()


def _draw_fallback_icon() -> QIcon:
    """运行时绘制: 深青圆角方块 + 白色时钟. 无外部资源依赖."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#0F766E"))
    p.drawRoundedRect(0, 0, 64, 64, 15, 15)
    pen = QPen(QColor("#FFFFFF"), 5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(15, 15, 34, 34)
    p.drawLine(32, 32, 32, 22)
    p.drawLine(32, 32, 40, 36)
    p.end()
    return QIcon(pm)


class TrayApp(QMainWindow):
    """主窗口 + 系统托盘 (常驻后台) + 前台跟踪."""

    def __init__(self, db_path: str | None = None, ipc_name: str | None = None):
        super().__init__()
        self._db_path = db_path or os.path.join(app_data_dir(), "usage.db")
        self._ipc_name = ipc_name or APP_IPC_SERVER

        self._store: Store = Store(self._db_path)
        self._tracker: Tracker | None = None
        self._tick_timer: QTimer | None = None
        self._tick_count = 0
        self._last_app_path: str | None = None

        self.setWindowTitle(APP_NAME_ZH)
        self.setWindowIcon(make_tray_icon())
        self.resize(480, 640)
        self.setMinimumSize(420, 560)

        self._create_central_widget()
        self._create_tray_icon()
        self._create_ipc_server()

    # ---------- 单实例唤醒 (参照 Get It) ----------
    def _create_ipc_server(self):
        """第二实例启动时经 QLocalServer 唤醒本窗口."""
        self._ipc_server = QLocalServer(self)
        self._ipc_server.listen(self._ipc_name)
        self._ipc_server.newConnection.connect(self._restore_from_tray)

    # ---------- 中央统计视图 ----------
    def _create_central_widget(self):
        self.tabs = QTabWidget(self)
        self.stats_view = StatsView(self._store, self.tabs)
        self.apps_view = AppsView(self._store, self.tabs)
        self.history_view = HistoryView(self._store, self.tabs)
        self.tabs.addTab(self.stats_view, "使用时段")
        self.tabs.addTab(self.apps_view, "各应用")
        self.tabs.addTab(self.history_view, "近 7 天")
        self.setCentralWidget(self.tabs)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "stats_view"):
            self.stats_view.refresh()
            self.apps_view.refresh()
            self.history_view.refresh()

    # ========================
    # 前台跟踪
    # ========================
    def _start_tracking(self):
        self._tracker = Tracker()
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start()

    def _on_tick(self):
        now = datetime.now()
        fg = foreground.get_foreground()
        trackable = None
        # 排除自身进程 + 桌面/托盘/系统进程 (foreground.is_trackable)
        if fg is not None and fg.pid != os.getpid() and foreground.is_trackable(fg):
            trackable = fg
        if trackable is not None and self._last_app_path is not None \
                and trackable.exe_path != self._last_app_path:
            self._flush()   # 应用切换: 立即入库
        self._last_app_path = trackable.exe_path if trackable else None
        self._tracker.tick(now, trackable)
        self._tick_count += 1
        if self._tick_count % FLUSH_EVERY_TICKS == 0:
            self._flush()
            if self.isVisible():   # 窗口开着时每 10s 刷新统计
                self.stats_view.refresh()
                self.apps_view.refresh()
                self.history_view.refresh()
        self._update_tooltip()

    def _flush(self):
        if self._tracker is not None and self._store is not None:
            self._store.add_records(self._tracker.flush(datetime.now()))

    def _today_seconds(self) -> int:
        today = date.today().isoformat()
        base = self._store.today_total(today) if self._store else 0
        pending = self._tracker.pending_seconds(today) if self._tracker else 0
        return base + pending

    def _update_tooltip(self):
        total = format_duration(self._today_seconds())
        if self._tracker.is_paused:
            tip = f"已暂停 · 今日 {total}"
        elif self._tracker.current_app:
            tip = f"{self._tracker.current_app} · 今日 {total}"
        else:
            tip = f"{APP_NAME_ZH} · 今日 {total}"
        self.tray_icon.setToolTip(tip)

    # ========================
    # 系统托盘 (参照 Get It)
    # ========================
    def _create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(make_tray_icon())
        self.tray_icon.setToolTip(APP_NAME_ZH)

        menu = QMenu()
        show_action = QAction("显示统计", self)
        show_action.triggered.connect(self._restore_from_tray)
        self.pause_action = QAction("暂停统计", self)
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self._on_pause_toggled)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_application)
        menu.addAction(show_action)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_pause_toggled(self, checked):
        if self._tracker is not None:
            if checked:
                self._tracker.pause()
            else:
                self._tracker.resume()
            self._update_tooltip()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def show_startup_notification(self):
        """启动时右下角系统通知 (王熙凤口吻)."""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                APP_NAME_ZH,
                "敢偷玩游戏？可仔细你的皮！",
                QSystemTrayIcon.MessageIcon.Information,
                3000)

    def _minimize_to_tray(self):
        self.hide()

    def _restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_application(self):
        if self._tick_timer is not None:
            self._tick_timer.stop()
        self._flush()
        self._store.close()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self._minimize_to_tray()

    # ---------- 生命周期 ----------
    def start(self):
        """常驻后台: 开始跟踪, 只显示托盘, 不弹主窗口."""
        self._start_tracking()
        self.hide()


def _wake_existing_instance() -> None:
    """已有实例在跑: 经 QLocalServer 唤醒其窗口, 本实例静默退出."""
    sock = QLocalSocket()
    sock.connectToServer(APP_IPC_SERVER)
    if sock.waitForConnected(500):
        sock.disconnectFromServer()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME_ZH)
    app.setQuitOnLastWindowClosed(False)  # 关窗不退出 — 常驻托盘

    from theme import apply as apply_theme
    apply_theme(app)

    # 单实例 (参照 Get It): QSharedMemory 判定, 第二实例唤醒现有窗口后退出
    shared = QSharedMemory(APP_IPC_SINGLETON)
    if shared.attach() or not shared.create(1):
        _wake_existing_instance()
        return 0

    window = TrayApp()
    window.start()
    window.show_startup_notification()
    # 兜底: 任何正常退出路径 (含 Windows 注销/关机前的事件循环退出) 都先 flush
    app.aboutToQuit.connect(window._flush)
    code = app.exec()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
