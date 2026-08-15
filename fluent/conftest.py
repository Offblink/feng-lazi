"""v4 测试环境:
- 强制 offscreen 平台: windows 平台下 qtbot.wait 事件循环会触发图标提取的
  COM apartment 异常 (0x8001010D, 非致命但噪音大); offscreen 无此问题.
- 确保 v4 目录在 sys.path 最前: pytest 导入测试模块时会把项目根插到最前,
  与项目根的 v3 同名包 (widgets/store) 冲突.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# 本机同时装有 PySide6/PyQt5: 强制 pytest-qt 使用 PyQt6, 否则 qtbot 会先猜中
# PySide6, 与测试里 PyQt6 的控件混用导致 "Need to pass a QWidget to addWidget".
os.environ.setdefault("PYTEST_QT_API", "pyqt6")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
