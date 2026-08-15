# Design: 前台应用使用时长统计工具

## Problem
Windows 上统计"用户实际在用的应用"的时长。只统计**前台窗口**对应的应用；系统托盘、桌面、锁屏等非应用状态不计时。本工具自身常驻后台，以系统托盘形式存在。

## Context
- 平台: Windows 11 (x64), Python 3.13, PyQt6 6.10.2 已装
- 参考: `Get It` (PyQt6 提醒应用) 的托盘实现 —— `QSystemTrayIcon` + 右键菜单(打开主界面/退出) + 双击恢复 + `closeEvent` 最小化到托盘
- 约束: 常驻后台；数据本地存储；不引入重依赖
- 用户: 中文界面

## 设计读 (taste skill)
"Reading this as: Windows 11 桌面工具 for 自我追踪用户, calm Fluent 风格, 倾向 Segoe UI Variable + 锌灰中性色 + 单一深青 accent, Minimal & Clean preset"
- DESIGN_VARIANCE=4, MOTION_INTENSITY=2, VISUAL_DENSITY=4
- 反模板化纪律: 不用 AI 紫渐变、不用玻璃拟态、无装饰性圆点、无 em-dash

## Options Considered

### Option A: 轮询 + ctypes (推荐)
- 核心: 主线程 QTimer 每 1s 调 `GetForegroundWindow()` → `GetWindowThreadProcessId()` → `QueryFullProcessImageNameW()` 拿 exe 路径 → 累计进当前记录；切换应用时把上一段写入 SQLite
- 优点: 简单、稳、无额外依赖（ctypes 标准库）；1s 粒度对"使用时长"统计足够
- 缺点: 亚秒级切换会丢失（无实际意义）；每次 tick 一次 Win32 调用（开销可忽略）
- 风险: 低。获取 exe 路径对提权进程可能 Access Denied → 回退 `GetProcessImageFileNameW` + 卷映射

### Option B: 事件驱动 SetWinEventHook (EVENT_SYSTEM_FOREGROUND)
- 核心: 专用线程跑 hook + 自己的消息泵，前台切换瞬间触发回调
- 优点: 切换零延迟、零轮询开销、不错过任何切换
- 缺点: 复杂度高（回调编组、hook 生命周期、与 Qt 事件循环交互）；难调试难测试
- 风险: 中。hook 回调里做重活会卡系统；线程间信号传递多一个故障面

### Option C: 轮询 + psutil
- 同 A 但用 `psutil.Process(pid).name()/exe()` 取元数据
- 优点: 代码略短
- 缺点: psutil 对提权/系统进程同样 Access Denied，仍需 ctypes 兜底；为省几行引入运行时依赖

**推荐 A**。纯 stdlib + PyQt6，排除逻辑集中，核心逻辑可单测。

### 存储: SQLite (stdlib) vs JSON vs CSV
- **SQLite 推荐**: WAL 模式、按 (date, app) 主键增量 upsert、崩溃安全、聚合查询方便
- JSON: 每次 flush 全量重写，崩溃丢数据
- CSV: 追加简单但聚合要自己算

### UI 形态
- **A 推荐**: 单窗口两页签（今日 / 近7天），自定义绘制的比例条列表，无图表库
- B: 仅托盘 + 剪贴板/通知输出 —— 太薄，没法"看统计"
- C: matplotlib 图表 —— 重依赖，v1 过杀

## Recommended: Option A
- 前台探测: `foreground.py` (Win32 封装 + 排除规则)
- 累计逻辑: `session.py` (纯逻辑, 可单测: tick 事件 → 记录)
- 存储: `store.py` (SQLite, 增量 upsert + 聚合查询)
- 集成: QTimer 1s tick, 切换 flush + 每 10s 定期 flush + 退出 flush
- 托盘: 按 Get It 模式 (菜单: 显示统计/暂停统计/退出, 双击恢复, close→隐藏)
- 单实例: QLockFile 防双开重复计时
- 启动: 默认直接驻留托盘（后台），双击/菜单打开统计窗口
- 排除: 桌面(Progman/WorkerW)、任务栏/托盘(Shell_TrayWnd)、LogonUI、dwm、SearchHost、ShellExperienceHost、ApplicationFrameHost(旧式 UWP 宿主)、自身

## Open Questions
1. 视觉预设: Minimal & Clean 浅色 (推荐) / Dark tech 深色 / Balanced Professional —— 需用户选
2. UWP 新版应用 (如 Windows 设置/照片) 多数走自身进程，可正常统计；个别走 ApplicationFrameHost 的旧式 UWP 计入排除（已知限制，v1 接受）
3. 排除列表是否需要用户可编辑 (设置界面) —— v1 内置固定列表，设置界面列为后续

## v3: 精确起止时段 (2026-08)

v2 只按小时累计 (`usage(date, hour, ...)`), 甘特图只能显示"某小时内有使用", 无法回答
"从几时几分开始、几时几分停止"。v3 改为按连续使用段记录精确时刻:

- 段 = 同应用不间断前台; 记录 `date` + `start`/`end` (HH:MM:SS) + 秒数
- 表 `segments(date, start, end, app_path, app_name, seconds)`, PK (date, start, app_path)
- 开放段每 10s 以最新 (end, seconds) 覆盖刷新同一行 —— 崩溃最多丢 10s, 甘特图实时可见;
  段结束时落定最终起止
- 段跨午夜在 00:00 拆分, 跨边界秒数计入新日期 (与 v2 口径一致); 跨小时不拆分
- v2 库无法还原分钟 → 备份 `.v2.bak` 后重建 (沿用 v1→v2 先例, 不混入无法还原的时刻)
- 甘特图按段的起始分钟定位渲染 (起始点驱动), tooltip 显示 起止时刻 + 时长
