# 实现计划: 凤辣子 Flet 重写

## 目标
把 `../pyqt` (PyQt6 托盘应用) 的功能用 Flet 0.86 重写为桌面应用, 行为等价:
- 常驻后台 + 系统托盘 (菜单: 显示统计 / 暂停统计 / 退出, 双击恢复, 关窗最小化到托盘)
- 每秒轮询前台窗口 → 精确起止使用段 → SQLite 入库
- 三页签统计: 使用时段 (24h 甘特图) / 各应用 / 近 7 天
- 单实例 + 第二实例唤醒现有窗口; 启动托盘通知 (王熙凤口吻)
- 视觉沿用 DESIGN.md: Minimal & Clean 浅色, 锌灰中性 + 单一深青 accent (#0F766E), 无 em-dash

## 环境事实 (已验证)
- Python 3.13.7; flet 0.86.4 已装; 桌面客户端 (~/.flet/client/flet-desktop-full-0.86.4) 可运行 (无需 .NET 10, 实测启动无错误)
- pystray + Pillow 10.4.0 已装; pytest 9.1.0
- Flet 0.86 API: `ft.run(main)` (async 支持), `page.window.visible` 启始隐藏/显示,
  `page.window.prevent_close` + `window.on_event` 拦截关闭, `page.window.destroy()` 真退出,
  `page.window.to_front()`, `page.run_task()` 后台协程, `page.window.icon` (.ico)
- pystray: `Icon.run_detached()` 独立线程, `notify(msg, title)` 气泡, `MenuItem(checked=fn)` 勾选

## 关键架构决策
1. **复用纯逻辑三层 (逐字移植, 零改动)**: `foreground.py` (ctypes Win32),
   `session.py` (Tracker 段累计), `store.py` (SQLite segments 表) — 无 Qt 依赖, 测试原样移植
2. **托盘**: Flet 无原生托盘 → `pystray` 独立线程; 菜单回调**不直接碰 page**,
   推入 `queue.Queue` 命令队列, 由 Flet 事件循环内的 tick 协程每轮消费 (≤1s 延迟, 线程安全)
3. **窗口生命周期**: 启动隐藏 (`window.visible=False`), 托盘"显示统计" → visible=True + to_front;
   关窗 → prevent_close + CLOSE 事件 → visible=False; "退出" → flush + destroy
4. **单实例**: ctypes `CreateMutexW` (替代 QSharedMemory); 第二实例经
   `FindWindowW("凤辣子")` + ShowWindow/SetForegroundWindow 唤醒后退出 (替代 QLocalServer)
5. **tick 编排抽成纯类 `tracking.TrackerLoop`** (替代 PyQt 版 `_on_tick` 内联逻辑),
   假时钟/假前台可单测, 对应原 test_integration.py 语义
6. **数据目录独立** `%LOCALAPPDATA%/UsageTrackerV5/usage.db` — 与 pyqt (V3) / fluent (V4) 隔离,
   沿用 "每版独立数据目录" 惯例 (见 fluent app.py), 互不污染
7. **应用图标**: ctypes `ExtractIconExW` + `GetDIBits` → PIL → base64 PNG 供 ft.Image;
   失败回退首字母圆形头像 (accent 底)

## 组件映射
```
flet/
  PLAN.md / README.md
  requirements.txt         flet>=0.86, pystray, Pillow
  requirements-dev.txt     pytest
  pytest.ini
  main.py                  入口: 依赖检查 + 单实例 + ft.run
  app.py                   FletApp: 页面/主题/三页签/tick 循环/tray 桥接
  tray.py                  pystray 控制器 (线程 + 命令队列)
  singleton.py             CreateMutexW 单实例 + FindWindowW 唤醒
  tracking.py              TrackerLoop 节拍编排 (纯逻辑, 可单测)
  theme.py                 Flet 主题令牌 (色板/圆角/字体)
  foreground.py / session.py / store.py   (逐字移植自 ../pyqt)
  widgets/
    format.py              时长格式化 (移植)
    icons.py               exe → base64 PNG; 字母头像回退
    app_row.py             应用行 (图标+名称+时长+比例条)
    time_gantt.py          甘特图 (seg_style 纯函数 + Stack 百分比定位)
    stats_view.py          使用时段页签
    apps_view.py           各应用页签
    history_view.py        近 7 天页签
  tests/                   test_session/test_store (移植) +
                           test_tracking/test_singleton/test_tray_queue/
                           test_icons/test_gantt/test_format
```

## 任务与验收

### Phase 0: 计划与脚手架
- PLAN.md; requirements; pytest.ini (pythonpath=.)
- 验收: 目录就绪

### Phase 1: 核心逻辑移植 (先证明基线绿, 再做 UI)
- `foreground.py` / `session.py` / `store.py` 逐字复制; tests/test_session.py, test_store.py 原样复制
- 验收: `python -m pytest tests/test_session.py tests/test_store.py` 全绿 (23 项)

### Phase 2: 可单测支撑件
- `theme.py`: Flet Theme (primary #0F766E, bg #FAFAF9, surface #FFFFFF, border #E4E4E7,
  text #18181B, muted #71717A; 卡片圆角 8; Segoe UI Variable 优先)
- `tracking.py`: TrackerLoop.step(now, fg) → 切换即 flush / 每 10 tick flush / 暂停 / pending 合计;
  测试: 累计与自动入库、切换 flush、暂停恢复、自身排除、today_seconds 口径 (对应原集成测试语义)
- `singleton.py`: 互斥持有/识别 + 唤醒函数; 测试: 双 CreateMutex 判定, FindWindowW 无窗口时静默
- `tray.py`: 命令队列 + 假 icon 可测; 测试: 菜单回调入队, 暂停勾选状态, notify 转发
- `widgets/icons.py`: 提取 python.exe 图标成功返回 base64; 不存在路径回退 None
- 验收: 新测试全绿

### Phase 3: UI 三页签
- `widgets/app_row.py` + `time_gantt.py` (seg_style 纯函数: left/width 百分比 + 2px 保底) + 测试
- `stats_view.py` (header: 日期+总时长; 甘特卡片; 空态"今日还没有使用记录")
- `apps_view.py` (header + 应用列表 + 比例条 + 空态)
- `history_view.py` (近 7 天卡片, 每日 top 3, 空日占位)
- 验收: 各 view 构建函数以假 store 数据生成控件树; seg_style/显示名/格式化测试绿

### Phase 4: 主应用集成
- `app.py`: 主题应用 → 三页签 → TrackerLoop + run_task tick 循环 → tray 桥接 (命令消费) →
  窗口事件 (关闭→隐藏) → 启动通知
- 验收: `python main.py` 启动后无窗口、托盘可见; 双击/菜单显示窗口; 关窗回托盘; 菜单退出干净

### Phase 5: 入口与验证
- `main.py`: 依赖检查 (flet/pystray/Pillow), 单实例, 唤醒, ft.run
- E2E 冒烟: 启动 → tick 数秒 → 退出 → 读库验证有 segments 记录
- README: 用法/数据位置/与 pyqt 版共存说明/限制
- 验收: `python -m pytest` 全绿; 冒烟通过; 自查无 em-dash

## 全局约束
- 不参考 ../fluent; 不引入 PyQt6
- 运行时依赖: flet, pystray, Pillow (ctypes/sqlite3 标准库)
- UI 文案中文, 无 em-dash, 单一 accent 贯穿
- 每阶段完成即验证, 不留半成品; 核心纯逻辑先行保证可测

## 风险 (实测更新)
- 托盘菜单→窗口操作 ≤1s 延迟: 可接受 (队列轮询)
- Flet 窗口 FindWindowW 唤醒依赖窗口标题 "凤辣子": 已实测第二实例 0.6s 退出并唤醒
- pystray 气泡通知在 Windows 可能被系统静默: 与 PyQt 版 showMessage 同级行为
- **Flet 客户端不支持百分比定位**: Dart 侧 `parseDouble("25%")` 返回 null →
  甘特图/比例条改用像素坐标 (track_w 由窗口宽度计算, 同 PyQt 版 _seg_rect 语义) 与
  Row expand 权重, 均经单测
- **渲染已实测正常**: 早期"本机 Flutter 不绘制"为测量假象 (强杀进程的幽灵窗口),
  活窗口 (唯一标题 + 属主进程存活校验) 像素与识图均确认 UI 正常渲染
