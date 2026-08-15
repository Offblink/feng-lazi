"""凤辣子 — 入口 (Flet 版).

用法:
    python main.py          # 启动, 默认驻留系统托盘 (后台)
"""
import os
import sys


def _check_deps() -> None:
    missing = []
    for mod in ("flet", "pystray", "PIL"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"[凤辣子] 缺少依赖 {', '.join(missing)}, "
              f"请先执行: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)


_check_deps()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flet as ft  # noqa: E402
import singleton  # noqa: E402


def main() -> int:
    if not singleton.acquire():
        # 已有实例在跑: 唤醒其窗口后静默退出
        singleton.wake_window()
        return 0
    import app  # noqa: E402
    # FLET_APP_HIDDEN: 客户端首帧不显示窗口 (flet_desktop 据此设
    # FLET_HIDE_WINDOW_ON_START), 避免启动闪烁; 窗口由托盘"显示统计"唤起
    ft.run(app.main, view=ft.AppView.FLET_APP_HIDDEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
