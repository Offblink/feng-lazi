"""tray.py 托盘控制器测试: 命令队列 / 菜单回调 / 勾选状态 / 生命周期."""
from PIL import Image

from tray import (CMD_PAUSE, CMD_QUIT, CMD_RESUME, CMD_SHOW, TrayController)


class FakeIcon:
    """记录调用; 不真正启动托盘."""

    def __init__(self, name, image, title, menu):
        self.name = name
        self.image = image
        self.title = title
        self.menu = menu
        self.stopped = False
        self.notified = []

    def run_detached(self):
        self.ran = True

    def stop(self):
        self.stopped = True

    def notify(self, message, title=None):
        self.notified.append((message, title))


def _img():
    return Image.new("RGBA", (32, 32), (255, 0, 0, 255))


def _controller(paused=False):
    state = {"paused": paused}
    c = TrayController(_img(), is_paused=lambda: state["paused"],
                       icon_cls=FakeIcon)
    return c, state


def test_menu_callbacks_enqueue_commands():
    c, _state = _controller()
    c._on_show(None, None)
    c._on_quit(None, None)
    assert c.commands() == [CMD_SHOW, CMD_QUIT]


def test_pause_toggle_uses_current_state():
    c, state = _controller(paused=False)
    c._on_pause_toggle(None, None)          # 未暂停 → 暂停
    assert c.commands() == [CMD_PAUSE]
    state["paused"] = True
    c._on_pause_toggle(None, None)          # 已暂停 → 恢复
    assert c.commands() == [CMD_RESUME]


def test_checked_reflects_paused():
    c, state = _controller(paused=False)
    assert not c._checked(None)
    state["paused"] = True
    assert c._checked(None)


def test_menu_structure():
    c, _state = _controller()
    menu = c._build_menu()
    items = [i.text for i in menu.items]
    assert items == ["显示统计", "暂停统计", "- - - -", "退出"]  # 分隔线


def test_start_and_stop():
    c, _state = _controller()
    c.start()
    assert c._icon is not None and c._icon.ran
    icon = c._icon
    c.stop()
    assert c._icon is None
    assert icon.stopped


def test_notify_and_tooltip_forward():
    c, _state = _controller()
    c._icon = FakeIcon("凤辣子", _img(), "t", None)
    c.notify("消息", "标题")
    assert c._icon.notified == [("消息", "标题")]
    c.set_tooltip("a.exe · 今日 9 秒")
    assert c._icon.title == "a.exe · 今日 9 秒"


def test_commands_drains_queue():
    c, _state = _controller()
    c._q.put(CMD_SHOW)
    c._q.put(CMD_SHOW)
    assert c.commands() == [CMD_SHOW, CMD_SHOW]
    assert c.commands() == []              # 已取空
