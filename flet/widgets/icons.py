"""icons.py — 应用 exe 图标提取 (ctypes + Pillow) → base64 PNG.

替代 PyQt 的 QFileIconProvider: ExtractIconExW 取图标 → GetIconInfo → GetDIBits
读 32bpp 像素 → PIL RGBA → 缩放到目标尺寸 → PNG base64 (供 ft.Image src_base64).
失败 (无图标/系统进程/非 exe) 返回 None, 由调用方回退首字母头像.
"""
from __future__ import annotations

import base64
import ctypes
import io
import os
from ctypes import wintypes

from PIL import Image, ImageDraw, ImageFont

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32

# 64 位下必须显式声明: 默认 c_int 会截断句柄/指针
gdi32.GetObjectW.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID]
gdi32.GetObjectW.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
gdi32.SelectObject.restype = wintypes.HANDLE
gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, wintypes.UINT,
                            wintypes.UINT, wintypes.LPVOID, wintypes.LPVOID,
                            wintypes.UINT]
gdi32.GetDIBits.restype = ctypes.c_int
user32.GetIconInfo.argtypes = [wintypes.HICON, wintypes.LPVOID]
user32.GetIconInfo.restype = wintypes.BOOL
user32.DestroyIcon.argtypes = [wintypes.HICON]
user32.DestroyIcon.restype = wintypes.BOOL
shell32.ExtractIconExW.argtypes = [wintypes.LPCWSTR, ctypes.c_int,
                                   wintypes.LPVOID, wintypes.LPVOID, ctypes.c_uint]
shell32.ExtractIconExW.restype = ctypes.c_uint


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG), ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD), ("bmBitsPixel", wintypes.WORD),
        ("bmBits", wintypes.LPVOID),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]


def _hicon_to_png(hicon: int, size: int) -> Image.Image | None:
    """HICON → PIL 图像 (RGBA, 已缩放)."""
    info = ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(info)):
        return None
    try:
        hbm = info.hbmColor
        if not hbm:
            return None   # 纯掩码图标: 无彩色位图
        bm = BITMAP()
        if not gdi32.GetObjectW(hbm, ctypes.sizeof(BITMAP), ctypes.byref(bm)):
            return None
        w, h = bm.bmWidth, bm.bmHeight
        if w <= 0 or h <= 0:
            return None

        hdc = gdi32.CreateCompatibleDC(None)
        if not hdc:
            return None
        try:
            gdi32.SelectObject(hdc, hbm)
            bih = BITMAPINFOHEADER()
            bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bih.biWidth = w
            bih.biHeight = -h           # 自顶向下
            bih.biPlanes = 1
            bih.biBitCount = 32
            buf = ctypes.create_string_buffer(w * h * 4)
            if not gdi32.GetDIBits(hdc, hbm, 0, h, buf,
                                   ctypes.byref(bih), 0):
                return None
            img = Image.frombytes("RGBA", (w, h), buf.raw, "raw", "BGRa")
        finally:
            gdi32.DeleteDC(hdc)
        if size and (w != size or h != size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return img
    finally:
        if info.hbmColor:
            gdi32.DeleteObject(info.hbmColor)
        if info.hbmMask:
            gdi32.DeleteObject(info.hbmMask)


def app_icon_base64(exe_path: str, size: int = 32) -> str | None:
    """exe 图标 → 'data:image/png;base64,...' ; 失败返回 None."""
    if not exe_path or not os.path.isfile(exe_path):
        return None
    large = wintypes.HICON()
    small = wintypes.HICON()
    n = shell32.ExtractIconExW(exe_path, 0, ctypes.byref(large),
                               ctypes.byref(small), 1)
    try:
        hic = large.value or small.value
        if n <= 0 or not hic:
            return None
        img = _hicon_to_png(hic, size)
        if img is None:
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    finally:
        if large.value:
            user32.DestroyIcon(large.value)
        if small.value:
            user32.DestroyIcon(small.value)


def letter_avatar_base64(name: str, size: int = 32, bg: str = "#0F766E",
                         fg: str = "#FFFFFF") -> str:
    """首字母圆形头像 (accent 底 + 白字), 图标提取失败时的回退."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, size - 1, size - 1), fill=bg)
    ch = (name[0] if name else "?").upper()
    try:
        font = ImageFont.truetype("segoeui.ttf", int(size * 0.55))
    except OSError:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), ch, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1]),
              ch, font=font, fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def app_icon(exe_path: str, name: str, size: int = 32) -> str:
    """应用图标 data URI: 优先 exe 真图标, 失败回退首字母头像."""
    return app_icon_base64(exe_path, size) or letter_avatar_base64(name, size)
