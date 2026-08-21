"""凤辣子 v4 — 入口 (qfluentwidgets Fluent 重写实验).

用法:
    python main.pyw          # 启动 Fluent 版本主窗口
"""
import os
import subprocess
import sys


def _relaunch_in_venv() -> None:
    """不在项目 venv 中运行时, 自动改用 venv 的 pythonw 重启自身.

    双击 main.pyw 时 Windows 用全局 python 解释器运行 (.pyw 文件关联),
    而全局环境可能装有其他 PyQt/Fluent 版本 (PyQt5 系与 PyQt6 系共用
    同名顶层包 qfluentwidgets/qframelesswindow, 互相覆盖), 导致绑定
    校验失败、启动即退. 这里强制切到项目 venv, 与全局环境彻底隔离.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    venv_pythonw = os.path.join(here, ".venv", "Scripts", "pythonw.exe")
    if not os.path.exists(venv_pythonw):
        return  # 无 venv: 按原逻辑跑全局 (依赖校验会给出提示)
    # sys.prefix 指向 venv 目录 => 已在 venv 内, 无需重启
    venv_dir = os.path.normcase(os.path.realpath(os.path.join(here, ".venv")))
    if os.path.normcase(os.path.realpath(sys.prefix)) == venv_dir:
        return
    subprocess.Popen([venv_pythonw, __file__], cwd=here)
    sys.exit(0)


_relaunch_in_venv()


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
