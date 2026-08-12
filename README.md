# 凤辣子 (feng-lazi)

PyQt6 前台应用使用时长统计工具。常驻系统托盘后台运行，只统计**前台窗口**对应的应用；桌面、任务栏、系统托盘、锁屏等状态不计时。名字取自《红楼梦》王熙凤的绰号，凤辣子盯得紧，你的每一秒它都记着。

> English: [README_EN.md](README_EN.md)

## 起因

我的弟弟总是偷玩游戏。为了防止意外继续发生，特地制作了这款应用。恰好最近我和他在一起看《红楼梦》87 版电视剧，因命此名。

## 《红楼梦》真的很好看！

> 最近跟我弟一起看《红楼梦》87 版，拍得真好，强烈推荐，中外友人都别错过。
> 说回这软件：起因就是我弟老偷着打游戏，防不胜防，我就做了个记时间的。电脑一开，前台是谁、用了多久，一笔一笔都记着，赖不掉。
> 它平时安安静静蹲在系统托盘里，不碍事；想查账，双击就开，今天用了啥、这七天怎么花的，清清楚楚。
> 名字是看剧看来的，凤辣子盯人最紧，正合适。我弟现在开游戏前都得掂量掂量，可仔细你的皮。

## 运行

```bash
pip install -r requirements.txt
python main.py
```

启动后无窗口，直接驻留系统托盘（后台）。开发/测试依赖见 `requirements-dev.txt`。

## 托盘操作

| 操作 | 效果 |
|---|---|
| 右键托盘图标 | 菜单: 显示统计 / 暂停统计 / 退出 |
| 双击托盘图标 | 打开统计窗口 |
| 关闭统计窗口 (X) | 最小化到托盘，继续统计 |
| 暂停统计 (勾选) | 期间不计时，tooltip 显示"已暂停" |

托盘 tooltip 实时显示: 当前应用 + 今日总时长。

## 统计规则

- 每秒探测前台窗口，按 1 秒粒度累计；切换应用 / 每 10 秒 / 退出时写入数据库
- 排除: 桌面(Progman/WorkerW)、任务栏托盘(Shell_TrayWnd)、锁屏(LogonUI)、dwm、搜索、系统外壳进程、旧式 UWP 宿主(ApplicationFrameHost)、本程序自身
- 提权进程读取路径失败时自动回退到设备路径 + 卷映射
- 单实例 (QLockFile)，防双开重复计时

## 数据

- 存储: `%LOCALAPPDATA%\UsageTracker\usage.db` (SQLite, WAL)
- 表 `usage(date, app_path, app_name, seconds)`，按 (日期, 应用) 增量累加

## 界面

- 今日: 总时长 + 各应用比例条列表（图标取自 exe）
- 近 7 天: 每日总时长 + 当日 top 3 应用
- 视觉: Minimal & Clean 浅色，Segoe UI Variable，单一深青 accent，Fluent 语言

## 测试

```bash
pip install -r requirements-dev.txt
python -m pytest
```

(pytest.ini 已固定 `qt_api = pyqt6`，本机同时装有 PySide6 时不会选错绑定)

## 目录

```
main.py            入口 (单实例 + 驻留托盘)
app.py             TrayApp: 托盘生命周期 + 每秒跟踪 tick
foreground.py      Win32 前台探测 + 排除规则 (ctypes)
session.py         Tracker 累计逻辑 (纯逻辑)
store.py           SQLite 存储 + 聚合查询
theme.py           设计令牌 (色板/字体/QSS)
resources/icon.ico 应用/托盘图标 (缺失时回退运行时绘制)
widgets/           统计视图 (今日/近7天/应用行/格式化)
tests/             pytest + qtbot 测试
```

## 已知限制

- 个别旧式 UWP 应用（ApplicationFrameHost 宿主）无法归因到真实应用，计入排除
- 跨午夜的使用时段按新日期入账（1 秒粒度内的跨天误差可忽略）
- 亚秒级的前台切换不统计（对时长统计无意义）
- 暂停统计状态不跨重启保存
