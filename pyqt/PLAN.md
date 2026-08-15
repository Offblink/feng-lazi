# Implementation Plan: 前台应用使用时长统计工具

## Design Reference
`DESIGN.md` (本目录) — Option A: 轮询 + ctypes + SQLite；视觉预设 Minimal & Clean 浅色

## Component Map
```
NEW FILES:
- usage_tracker/
  - main.py           入口 (依赖检查 + QApplication + 单实例 QLockFile)
  - app.py            TrayApp (托盘/窗口生命周期, 参照 Get It)
  - theme.py          设计令牌 (色板/字体/间距/QSS)
  - foreground.py     Win32 前台探测 + 排除规则 (ctypes)
  - session.py        Tracker 累计逻辑 (纯逻辑, 可单测)
  - store.py          SQLite 存储 + 聚合查询
  - widgets/__init__.py
  - widgets/stats_view.py   今日视图
  - widgets/history_view.py 近7天视图
  - widgets/app_row.py      应用行 (图标+名称+时长+比例条)
  - widgets/format.py       时长格式化
  - requirements.txt
  - tests/test_session.py
  - tests/test_store.py
  - README.md
```

## Tasks

### Phase 0: Scaffold
**Task 1: 项目骨架 + 托盘生命周期**
- 文件: `requirements.txt`, `main.py`, `theme.py`(初始), `app.py`(托盘部分)
- 内容: `QSystemTrayIcon` 按 Get It 模式 (运行时绘制图标/右键菜单/双击恢复/closeEvent→隐藏/退出清理)；`QLockFile` 单实例；`setQuitOnLastWindowClosed(False)`；默认启动驻留托盘
- 验收: `python main.py` 无主窗口、托盘图标可见；双击/菜单显示窗口；关闭按钮最小化到托盘；菜单退出干净；二次启动提示已运行

### Phase 1: 跟踪核心 (可单测)
**Task 2: foreground.py — 前台探测**
- `get_foreground() -> ForegroundInfo | None` (hwnd/pid/exe_path/name)
- exe 路径: `QueryFullProcessImageNameW` → 失败回退 `GetProcessImageFileNameW` + 卷映射
- `is_trackable(info) -> bool`: 排除桌面/托盘/锁屏/系统进程窗口类
- 验收: 探针脚本打印当前前台应用；桌面/托盘场景返回不可统计

**Task 3: session.py — 累计逻辑**
- `Tracker.tick(now, fg)` 按 delta 累计; 切换/暂停清段; `flush(now)` 结算并返回 `list[Record]`; `pause/resume`
- delta 上限 60s 防挂起跳变; 空段/零 delta 不计
- 验收: `python -m unittest tests.test_session` 全绿

**Task 4: store.py — SQLite 存储**
- `usage(date, app_path, app_name, seconds)` PK(date, app_path), WAL, 增量 upsert
- `add_records / today_total / daily_breakdown / last_n_days`
- 验收: `python -m unittest tests.test_store` 全绿

### Phase 2: 集成
**Task 5: 接入实时跟踪**
- QTimer 1s tick → `get_foreground` + `is_trackable` + `pid != os.getpid()` 自身排除 → `tracker.tick`
- 每 10s / 应用切换 / 退出 flush 入库; 托盘 tooltip = 当前应用 + 今日总时长; 托盘菜单加"暂停统计" (checkable)
- 验收: 切应用 tooltip 实时更新; 暂停后不再累计; 重启后数据延续

### Phase 3: 统计 UI
**Task 6: 今日视图**
- header: 日期 + 今日总时长; 应用行: 图标(QFileIconProvider 从 exe 提取) + 名称 + 时长 + 相对比例条
- 窗口 show 时刷新
- 验收: 显示真实数据, 比例条与时长一致

**Task 7: 近7天视图**
- 每天: 日期 + 总时长 + top 3 应用; 空日占位
- 验收: 有数据天聚合正确, 空日占位

**Task 8: 视觉打磨**
- theme.py 完整化 (卡片/列表/比例条/滚动条/菜单); 空状态文案; 全量自查无 em-dash
- 验收: 与设计读一致, 对比度达标

### Phase 4: 验证与收尾
**Task 9: 端到端验收 + README**
- 全量单测; 冒烟: 启动→tick 数秒→退出→读库验证有记录; README (用法/数据位置/限制)
- 验收: 验收清单全过, `python -m unittest discover` 全绿

## Execution Strategy
- 顺序执行, 每 Task 完成即验证再进下一个; Task 5 后整体冒烟
- 非 git 仓库 (C:/tmp), 无 commit 步骤; 以 Task 为增量边界

## Global Constraints
- 运行时依赖仅 PyQt6 (ctypes/sqlite3 为标准库)
- UI 文案中文; 不引入 em-dash; 单一 accent 色贯穿
- 每任务改完即验证 (运行或单测), 不留半成品状态
- 测试: pytest + pytest-qt (requirements-dev.txt); 纯逻辑用普通测试, Qt 交互用 qtbot

## Interface Contracts
```
foreground.ForegroundInfo: dataclass(hwnd:int, pid:int, exe_path:str, name:str)  # name 小写
foreground.get_foreground() -> ForegroundInfo | None
foreground.is_trackable(info) -> bool

session.Tracker:
  tick(now: datetime, fg: ForegroundInfo | None)   # 每秒
  pause() / resume() / is_paused -> bool
  flush(now: datetime | None) -> list[Record]
  Record = dataclass(date:str, app_path:str, app_name:str, seconds:int)

store.Store(db_path: str):
  add_records(records) / today_total(date:str) -> int
  daily_breakdown(date:str) -> list[dict]          # 秒降序
  last_n_days(n:int, end_date: date) -> list[dict] # 含空日
```

## v3: 精确起止时段 (增量实现)

背景: v2 只按小时聚合, 无法回答"某款应用从几时几分开始到几时几分停止"。目标:
确定具体起止时刻后, 甘特图时段按起始点正确渲染。

### 变更
- `store.py`: `usage(date, hour, ...)` → `segments(date, start, end, app_path, app_name, seconds)`,
  PK (date, start, app_path); upsert 覆盖开放段; `app_hourly` → `app_segments`
  (每段 start_min/end_min/seconds + HH:MM:SS 原串)
- `session.py`: `Record(date, start, end, app_path, app_name, seconds)`; 段 = 连续前台;
  tick 切换/无前台/暂停结束段; 跨午夜 00:00 拆分; flush 返回 已结束段 + 开放段最新状态;
  pending 记账防与已入库开放段重复
- `widgets/time_gantt.py`: 分钟级段矩形按起始点渲染; tooltip `应用 · 10:05 - 10:23 · 18 分`
  (不足 1 分钟的段含秒)
- `widgets/stats_view.py`: 接入 `app_segments`
- 迁移: v2 库 (含 hour 列) 备份 `.v2.bak` 后重建; v1 库仍备份 `.v1.bak`

### 验收
- pytest 全绿 (53 项, 含 v3 段语义单测与迁移测试)
- 真实 v2 库副本迁移验证: 3 行 283 秒完整备份, 新库为 segments 空表
- 离屏渲染像素断言: 段内/间隙/段后颜色与起始分钟定位一致
