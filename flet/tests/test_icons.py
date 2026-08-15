"""widgets/icons.py 图标提取测试: 真 exe 图标 / 缺失回退 / 字母头像."""
import base64
import io
import sys

from PIL import Image

from widgets.icons import app_icon, app_icon_base64, letter_avatar_base64


def _decode(uri):
    assert uri.startswith("data:image/png;base64,")
    raw = base64.b64decode(uri.split(",", 1)[1])
    return Image.open(io.BytesIO(raw))


def test_extract_icon_from_real_exe():
    uri = app_icon_base64(sys.executable)   # python.exe 自带图标
    assert uri is not None
    img = _decode(uri)
    assert img.size == (32, 32)


def test_missing_path_returns_none():
    assert app_icon_base64("C:/不存在/xx.exe") is None
    assert app_icon_base64("") is None


def test_letter_avatar_shape_and_size():
    uri = letter_avatar_base64("chrome.exe")
    img = _decode(uri)
    assert img.size == (32, 32)
    assert img.mode == "RGBA"


def test_app_icon_falls_back_to_avatar():
    uri = app_icon("C:/不存在/xx.exe", "xx.exe")
    assert uri.startswith("data:image/png;base64,")
    assert _decode(uri).size == (32, 32)
