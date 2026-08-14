"""凤辣子 v4 — 入口 (qfluentwidgets Fluent 重写实验).

用法:
    python main.pyw          # 启动 Fluent 版本主窗口
"""
import os
import sys


def _check_deps() -> None:
    try:
        import PyQt6  # noqa: F401
        import qfluentwidgets  # noqa: F401
    except ImportError:
        print("[UsageTrackerV4] 缺少依赖, 请先执行: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(1)


_check_deps()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
