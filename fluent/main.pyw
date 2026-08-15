"""凤辣子 v4 — 入口 (qfluentwidgets Fluent 重写实验).

用法:
    python main.pyw          # 启动 Fluent 版本主窗口
"""
import os
import sys


def _check_deps() -> None:
    try:
        import PyQt6  # noqa: F401
    except ImportError:
        print("[UsageTrackerV4] 缺少依赖, 请先执行: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(1)
    try:
        import qfluentwidgets  # noqa: F401
    except ImportError:
        print("[UsageTrackerV4] 缺少依赖, 请先执行: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(1)
    # 绑定校验: qfluentwidgets 必须是 PyQt6 版 (PyQt6-Fluent-Widgets).
    # PyQt5 版 (PyQt-Fluent-Widgets) 与 PyQt6 混用时, qframelesswindow 会构造
    # PyQt5 QWidget, 因无 PyQt5 QApplication 而崩溃:
    #   "QWidget: Must construct a QApplication before a QWidget"
    # qfluentwidgets 导入即拉入 qframelesswindow, 其硬编码的绑定必在 sys.modules 中.
    if "PyQt6.QtCore" not in sys.modules or "PyQt5.QtCore" in sys.modules:
        print("[UsageTrackerV4] qfluentwidgets 检测为 PyQt5 版, 与 PyQt6 不兼容."
              "\n请安装 PyQt6 版: pip install PyQt6-Fluent-Widgets",
              file=sys.stderr)
        sys.exit(1)


_check_deps()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
