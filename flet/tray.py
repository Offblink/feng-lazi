"""tray.py — 系统托盘 (pystray 独立线程).

Flet 无原生托盘 → pystray Icon.run_detached() 起独立线程.
菜单回调不直接触碰 Flet page (跨线程不安全): 推入命令队列,
由 Flet 事件循环内的 tick 协程每轮消费 (≤1s 延迟, 线程安全).
命令: "show" 显示窗口 / "pause" / "resume" 暂停统计 / "quit" 退出.
"""
from __future__ import annotations

import queue
from typing import Callable

import pystray
from PIL import Image

CMD_SHOW = "show"
CMD_PAUSE = "pause"
CMD_RESUME = "resume"
CMD_QUIT = "quit"

APP_TITLE = "凤辣子"


class TrayController:
    """托盘图标生命周期 + 命令队列. icon_cls / is_paused 可注入以便测试."""

    def __init__(self, icon_image: Image.Image, tooltip: str = APP_TITLE,
                 is_paused: Callable[[], bool] | None = None,
                 icon_cls=pystray.Icon) -> None:
        self._icon_image = icon_image
        self._tooltip = tooltip
        self._is_paused = is_paused or (lambda: False)
        self._icon_cls = icon_cls
        self._q: queue.Queue = queue.Queue()
        self._icon = None

    # ---------- 命令队列 (tick 协程消费) ----------
    def commands(self) -> list[str]:
        """取走当前全部命令."""
        out: list[str] = []
        while True:
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                return out

    # ---------- 菜单回调 (pystray 线程) ----------
    def _on_show(self, icon, item) -> None:
        self._q.put(CMD_SHOW)

    def _on_pause_toggle(self, icon, item) -> None:
        # 以应用当前暂停状态为准: 未暂停 → 暂停; 已暂停 → 恢复
        self._q.put(CMD_RESUME if self._is_paused() else CMD_PAUSE)

    def _on_quit(self, icon, item) -> None:
        self._q.put(CMD_QUIT)

    def _checked(self, item) -> bool:
        return self._is_paused()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("显示统计", self._on_show),
            pystray.MenuItem("暂停统计", self._on_pause_toggle, checked=self._checked),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    # ---------- 生命周期 ----------
    def start(self) -> None:
        self._icon = self._icon_cls(APP_TITLE, self._icon_image,
                                    self._tooltip, self._build_menu())
        self._icon.run_detached()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
            self._icon = None

    def notify(self, message: str, title: str = APP_TITLE) -> None:
        """系统托盘气泡通知."""
        if self._icon is not None:
            self._icon.notify(message, title)

    def set_tooltip(self, text: str) -> None:
        """托盘悬浮提示 = 当前应用 + 今日总时长."""
        if self._icon is not None:
            self._icon.title = text
