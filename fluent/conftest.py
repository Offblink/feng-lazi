"""v4 测试环境:
- 强制 offscreen 平台: windows 平台下 qtbot.wait 事件循环会触发图标提取的
  COM apartment 异常 (0x8001010D, 非致命但噪音大); offscreen 无此问题.
- 确保 v4 目录在 sys.path 最前: pytest 导入测试模块时会把项目根插到最前,
  与项目根的 v3 同名包 (widgets/store) 冲突.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
