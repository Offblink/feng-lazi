"""凤辣子 — 入口.

用法:
    python main.py          # 启动, 默认驻留系统托盘 (后台)
"""
import os
import sys


def _check_deps() -> None:
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("[UsageTracker] 缺少 PyQt6, 请先执行: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(1)


_check_deps()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
