"""foreground.py — Win32 前台窗口探测 (ctypes, 零依赖).

前台窗口句柄 → 所属进程 PID → 可执行文件完整路径.
排除规则对应需求"系统托盘的不算": 桌面 / 任务栏托盘 / 锁屏 / 系统外壳进程不计时.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# 系统/外壳进程: 前台属于它们时不算应用使用
EXCLUDED_PROCESSES = frozenset({
    "logonui.exe",               # 锁屏/登录
    "dwm.exe",                   # 桌面窗口管理器
    "searchhost.exe",            # 搜索
    "shellexperiencehost.exe",   # 系统 UI 宿主
    "startmenuexperiencehost.exe",
    "applicationframehost.exe",  # 旧式 UWP 宿主 (真实应用无法归因, 见 DESIGN.md)
    "textinputhost.exe",
    "shellhost.exe",
})

# 窗口类: 桌面 / 任务栏 / 托盘
EXCLUDED_CLASSES = frozenset({
    "Progman", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "WorkerW",
})


@dataclass(frozen=True)
class ForegroundInfo:
    hwnd: int
    pid: int
    exe_path: str
    name: str  # exe 文件名, 小写


def _query_exe_path(pid: int) -> str | None:
    """QueryFullProcessImageNameW; 提权进程 Access Denied 时回退
    GetProcessImageFileNameW + 卷映射 (设备路径 → 盘符路径)."""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(32768)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        buf2 = ctypes.create_unicode_buffer(32768)
        n = kernel32.GetProcessImageFileNameW(h, buf2, 32768)
        if n:
            return _device_path_to_drive(buf2.value)
        return None
    finally:
        kernel32.CloseHandle(h)


def _device_path_to_drive(device_path: str) -> str:
    """把 \\Device\\HarddiskVolumeN\\... 映射为 C:\\..."""
    drives = ctypes.create_unicode_buffer(512)
    kernel32.GetLogicalDriveStringsW(512, drives)
    for drive in drives.value.split("\x00"):
        if not drive:
            continue
        target = ctypes.create_unicode_buffer(512)
        kernel32.QueryDosDeviceW(drive.rstrip("\\"), target, 512)
        prefix = target.value
        if prefix and device_path.startswith(prefix):
            return drive + device_path[len(prefix):]
    return device_path  # 映射失败, 原样返回


def _window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_foreground() -> ForegroundInfo | None:
    """当前前台窗口对应的应用信息; 无前台窗口时返回 None."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    path = _query_exe_path(pid.value)
    if not path:
        return None
    return ForegroundInfo(hwnd=hwnd, pid=pid.value, exe_path=path,
                          name=os.path.basename(path).lower())


def is_trackable(info: ForegroundInfo, self_pid: int | None = None) -> bool:
    """是否计入统计: 排除系统进程 / 自身 / 桌面与任务栏窗口类."""
    if info.name in EXCLUDED_PROCESSES:
        return False
    if self_pid is not None and info.pid == self_pid:
        return False
    return _window_class(info.hwnd) not in EXCLUDED_CLASSES
