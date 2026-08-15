"""singleton.py 单实例互斥 + 窗口唤醒测试 (Windows ctypes)."""
import ctypes
from ctypes import wintypes
from uuid import uuid4

from singleton import acquire, release, wake_window

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)
WM_CLOSE = 0x0010

user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR,
                                   wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, wintypes.HWND, wintypes.HANDLE,
                                   wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.RegisterClassW.argtypes = [wintypes.LPVOID]
user32.RegisterClassW.restype = wintypes.ATOM
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
user32.UnregisterClassW.restype = wintypes.BOOL
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                  wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR),
    ]


class _Wnd:
    """极简可查找窗口 (离屏), 供唤醒测试."""

    def __init__(self, title: str):
        self._proc = WNDPROC(self._wndproc)
        cls_name = f"wake-test-{uuid4().hex}"
        wc = WNDCLASS()
        wc.lpfnWndProc = self._proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = cls_name
        assert user32.RegisterClassW(ctypes.byref(wc)) != 0
        self._cls = cls_name
        self.hwnd = user32.CreateWindowExW(
            0, cls_name, title, 0x00000000,   # WS_OVERLAPPED
            -32000, -32000, 200, 120, None, None, wc.hInstance, None)
        assert self.hwnd

    @staticmethod
    def _wndproc(hwnd, msg, wp, lp):
        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def destroy(self):
        user32.DestroyWindow(self.hwnd)
        user32.UnregisterClassW(self._cls, kernel32.GetModuleHandleW(None))


def test_mutex_single_instance():
    name = f"singleton-test-{uuid4().hex}"
    assert acquire(name)                 # 首个实例持有
    assert not acquire(name)             # 第二实例被识别
    release(name)
    assert acquire(name)                 # 释放后可再持有
    release(name)


def test_wake_window_finds_and_shows():
    title = f"wake-title-{uuid4().hex}"
    w = _Wnd(title)
    try:
        assert wake_window(title)        # 找到并唤醒
        assert not wake_window("__不存在的标题__")
    finally:
        w.destroy()
