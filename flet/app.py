"""凤辣子 — Flet 主应用 (常驻托盘 + 前台跟踪 + 三页签统计).

生命周期:
  - 启动即隐藏窗口, 驻留系统托盘 (pystray 独立线程)
  - tick 协程每秒轮询前台 → TrackerLoop 累计 → 切换/每 10s flush 入库
  - 托盘命令经队列桥接 (线程安全), 关窗拦截为最小化到托盘
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

import flet as ft

import foreground
from store import Store
from theme import BG, build_theme
from tracking import TrackerLoop, is_trackable
from tray import (APP_TITLE, CMD_PAUSE, CMD_QUIT, CMD_RESUME, CMD_SHOW,
                  TrayController)
from widgets.apps_view import AppsView
from widgets.format import format_duration
from widgets.history_view import HistoryView
from widgets.stats_view import StatsView

APP_NAME = "UsageTrackerV5"   # 独立数据目录 (pyqt=V3 / fluent=V4 / flet=V5, 互不干扰)
APP_NAME_ZH = "凤辣子"
WINDOW_TITLE = APP_NAME_ZH   # 与 singleton.WINDOW_TITLE 一致 (唤醒匹配)


def app_data_dir() -> str:
    """%LOCALAPPDATA%/UsageTrackerV5 — 独立数据目录 (与 pyqt V3 / fluent V4 隔离)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


def _tray_icon_image():
    """托盘图标: 优先 resources/icon.ico; 缺失时回退纯色块."""
    from PIL import Image
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "resources", "icon.ico")
    if os.path.exists(p):
        return Image.open(p).convert("RGBA")
    return Image.new("RGBA", (64, 64), (15, 118, 110, 255))


def main(page: ft.Page, db_path: str | None = None) -> None:
    """Flet 入口: 主题/窗口/三页签/跟踪循环/托盘桥接."""
    page.title = WINDOW_TITLE
    page.window.width = 480
    page.window.height = 640
    page.window.min_width = 420
    page.window.min_height = 560
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources", "icon.ico")
    if os.path.exists(icon_path):
        page.window.icon = icon_path
    page.theme = build_theme()
    page.bgcolor = BG
    page.padding = 24
    page.window.visible = False      # 常驻后台: 启动即隐藏

    store = Store(db_path or os.path.join(app_data_dir(), "usage.db"))
    loop = TrackerLoop(store)
    stats_view = StatsView(store)
    apps_view = AppsView(store)
    history_view = HistoryView(store)

    tabs = ft.Tabs(
        expand=True,
        length=3,
        selected_index=0,
        content=ft.Column(
            spacing=0,
            controls=[
                ft.TabBar(tabs=[
                    ft.Tab(label="使用时段"),
                    ft.Tab(label="各应用"),
                    ft.Tab(label="近 7 天"),
                ]),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        stats_view.control,
                        apps_view.control,
                        history_view.control,
                    ],
                ),
            ],
        ),
    )
    page.add(tabs)

    state = {"running": True}

    # ---------- 视图刷新 ----------
    def refresh_views() -> None:
        stats_view.refresh(page.width)
        apps_view.refresh()
        history_view.refresh()
        page.update()

    async def show_window() -> None:
        page.window.visible = True
        await page.window.to_front()
        refresh_views()

    async def quit_app() -> None:
        state["running"] = False
        loop.flush()
        tray.stop()
        try:
            await page.window.destroy()
        except RuntimeError:
            pass   # 会话关闭竞态: destroy 已生效, 忽略响应错误

    # ---------- 托盘 (pystray 线程; 命令经队列) ----------
    tray = TrayController(_tray_icon_image(), is_paused=lambda: loop.is_paused)
    tray.start()

    def tooltip_text() -> str:
        total = format_duration(loop.today_seconds())
        if loop.is_paused:
            return f"已暂停 · 今日 {total}"
        if loop.current_app:
            return f"{loop.current_app} · 今日 {total}"
        return f"{APP_NAME_ZH} · 今日 {total}"

    # ---------- 窗口事件 ----------
    def on_window_event(e: ft.WindowEvent) -> None:
        if e.type == ft.WindowEventType.CLOSE:
            page.window.visible = False      # 关窗最小化到托盘

    def on_resize(e) -> None:
        stats_view.refresh(page.width)
        page.update()

    page.window.prevent_close = True
    page.window.on_event = on_window_event
    page.on_resize = on_resize

    # ---------- 跟踪循环 (Flet 事件循环内) ----------
    async def tick_loop() -> None:
        while state["running"]:
            await asyncio.sleep(1)
            now = datetime.now()
            fg = foreground.get_foreground()
            trackable = fg if is_trackable(fg, os.getpid()) else None
            flushed = loop.step(now, trackable)
            for cmd in tray.commands():
                if cmd == CMD_SHOW:
                    await show_window()
                elif cmd == CMD_PAUSE:
                    loop.pause()
                elif cmd == CMD_RESUME:
                    loop.resume()
                elif cmd == CMD_QUIT:
                    await quit_app()
                    return
            if flushed and page.window.visible:
                refresh_views()
            tray.set_tooltip(tooltip_text())

    page.run_task(tick_loop)

    # 启动: 初始渲染 + 托盘通知
    refresh_views()
    tray.notify("敢偷玩游戏？可仔细你的皮！", APP_NAME_ZH)
