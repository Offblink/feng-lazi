"""singleton.py — 单实例: Windows 命名互斥 + 唤醒现有窗口.

替代 PyQt 版的 QSharedMemory (互斥判定) + QLocalServer (第二实例唤醒窗口):
  - acquire(): CreateMutexW, ERROR_ALREADY_EXISTS → 已有实例
  - wake_window(): FindWindowW 按标题找窗口 → ShowWindow + SetForegroundWindow
仅 Windows; ctypes 标准库, 零依赖.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

MUTEX_NAME = "FengLaziFletSingleton"
WINDOW_TITLE = "凤辣子"
ERROR_ALREADY_EXISTS = 183
SW_SHOW = 5

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

# 64 位下必须显式声明: 默认 c_int 会截断句柄/窗口指针
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

_handles: dict[str, int] = {}


def acquire(name: str = MUTEX_NAME) -> bool:
    """尝试持有命名互斥. True = 本实例是首个 (持有互斥); False = 已有实例在跑."""
    h = kernel32.CreateMutexW(None, False, name)
    if not h:
        return False          # 创建失败: 保守判定为不可用
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(h)
        return False
    _handles[name] = h
    return True


def release(name: str = MUTEX_NAME) -> None:
    """释放互斥 (测试/退出时). 进程退出时内核自动回收."""
    h = _handles.pop(name, None)
    if h:
        kernel32.CloseHandle(h)


def wake_window(title: str = WINDOW_TITLE) -> bool:
    """唤醒已运行实例的窗口 (best-effort): 找到即显示并置前. 找不到返回 False."""
    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        return False
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.SetForegroundWindow(hwnd)
    return True
