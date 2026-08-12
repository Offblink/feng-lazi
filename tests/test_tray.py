"""TrayApp 托盘生命周期测试 (qtbot)."""
import pytest
from PyQt6.QtCore import QLockFile
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from app import TrayApp, make_tray_icon


@pytest.fixture
def tray_app(qtbot, tmp_path):
    lock = QLockFile(str(tmp_path / "test.lock"))
    lock.setStaleLockTime(0)
    assert lock.tryLock(0)
    w = TrayApp(lock, db_path=str(tmp_path / "usage.db"))
    w.start()
    qtbot.addWidget(w)
    yield w
    w._tick_timer.stop()
    w.tray_icon.hide()
    lock.unlock()


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


def test_second_instance_blocked(tmp_path):
    path = str(tmp_path / "u.lock")
    lock1 = QLockFile(path)
    lock1.setStaleLockTime(0)
    assert lock1.tryLock(0)
    lock2 = QLockFile(path)
    lock2.setStaleLockTime(0)
    assert not lock2.tryLock(0)
    lock1.unlock()
