"""TrayApp 托盘生命周期测试 (qtbot)."""
from uuid import uuid4

import pytest
from PyQt6.QtCore import QSharedMemory
from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from app import TrayApp, make_tray_icon


def _ipc_name():
    return f"tray-test-{uuid4().hex}"   # 每测试唯一, 避免跨测试共享内存冲突


@pytest.fixture
def tray_app(qtbot, tmp_path):
    w = TrayApp(db_path=str(tmp_path / "usage.db"), ipc_name=_ipc_name())
    w.start()
    qtbot.addWidget(w)
    yield w
    w._tick_timer.stop()
    w.tray_icon.hide()


def test_start_hides_window(tray_app):
    assert not tray_app.isVisible()


def test_tray_icon_visible(tray_app):
    assert tray_app.tray_icon.isVisible()


def test_icon_not_null(tray_app):
    assert not tray_app.tray_icon.icon().isNull()


def test_context_menu_actions(tray_app):
    texts = [a.text() for a in tray_app.tray_icon.contextMenu().actions()]
    assert texts == ["显示统计", "暂停统计", "", "退出"]


def test_restore_shows_window(tray_app, qtbot):
    tray_app._restore_from_tray()
    qtbot.waitUntil(tray_app.isVisible, timeout=2000)
    assert tray_app.isVisible()


def test_double_click_restores(tray_app, qtbot):
    tray_app.tray_icon.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
    qtbot.waitUntil(tray_app.isVisible, timeout=2000)
    assert tray_app.isVisible()


def test_close_minimizes_to_tray(tray_app, qtbot):
    tray_app.show()
    tray_app.close()
    assert not tray_app.isVisible()
    assert tray_app.tray_icon.isVisible()


def test_quit_hides_tray(tray_app, monkeypatch):
    calls = []
    monkeypatch.setattr(QApplication, "quit", lambda: calls.append("quit"))
    tray_app._quit_application()
    assert calls == ["quit"]
    assert not tray_app.tray_icon.isVisible()


def test_second_instance_wakes_window(qtbot, tmp_path):
    """第二实例经 QLocalServer 唤醒: 窗口从隐藏变为可见."""
    name = _ipc_name()
    w = TrayApp(db_path=str(tmp_path / "usage.db"), ipc_name=name)
    w.start()
    qtbot.addWidget(w)
    assert not w.isVisible()

    sock = QLocalSocket()                  # 模拟第二实例的连接
    sock.connectToServer(name)
    assert sock.waitForConnected(1000)
    sock.disconnectFromServer()

    qtbot.waitUntil(w.isVisible, timeout=2000)
    w._tick_timer.stop()
    w.tray_icon.hide()


def test_shared_memory_single_instance():
    """QSharedMemory 判定: 第一实例持有, 第二实例被识别."""
    name = f"sm-test-{uuid4().hex}"
    first = QSharedMemory(name)
    assert not first.attach()
    assert first.create(1)                 # 第一实例成功持有
    second = QSharedMemory(name)
    assert second.attach() or not second.create(1)   # 第二实例被识别
    first.detach()


def test_startup_notification_calls_show_message(tray_app, monkeypatch):
    calls = []
    monkeypatch.setattr(tray_app.tray_icon, "showMessage",
                        lambda *args, **kwargs: calls.append(args))
    tray_app.show_startup_notification()
    assert calls
    assert "可仔细你的皮" in calls[0][1]


def test_make_tray_icon_draws():
    icon = make_tray_icon()
    assert not icon.isNull()
