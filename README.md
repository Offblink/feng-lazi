# 凤辣子 (feng-lazi)

PyQt6 前台应用使用时长统计工具，**两个版本**：经典自绘版（`pyqt/`）与 Fluent Design 版（`fluent/`）。常驻系统托盘后台运行，只统计**前台窗口**对应的应用；桌面、任务栏、系统托盘、锁屏等状态不计时。每次连续使用都记录**精确起止时刻**（几时几分到几时几分），一眼看出什么时候在用什么。名字取自《红楼梦》王熙凤的绰号，凤辣子盯得紧，你的每一秒它都记着。

> English: [README_EN.md](README_EN.md)

## 起因

我的弟弟总是偷玩游戏。为了防止意外继续发生，特地制作了这款应用。恰好最近我和他在一起看《红楼梦》87 版电视剧，因命此名。

## 《红楼梦》真的很好看！

>
许多人（尤其是一些我的男生朋友们），他们从小就对这部小说带有成见，看不进去。
>
但其实如果你愿意的话，可以看一下87版的电视剧，可好看了！
>
人物的打扮很传神，环境的营造也都恰到好处，真不愧是**地表最强电视剧**！⬅️至少我是这么觉得的😕
>

## 两个版本

| 目录 | 版本 | UI 技术 |
|---|---|---|
| `pyqt/` | 经典版 | PyQt6 + 自定义 QSS（Minimal & Clean 浅色，Segoe UI Variable，深青 accent） |
| `fluent/` | Fluent 版 | PyQt6-Fluent-Widgets（左侧导航，跟随系统深浅色，Win11 Mica 材质） |

两版共享同一套跟踪/存储逻辑（`store`/`session`/`foreground` 同源），界面内容一致三页：**使用时段**甘特图（每款应用一行时间轴，按精确起止时刻渲染，悬停看 起止时刻 + 时长）、**各应用**使用总时长比例条列表（图标取自 exe）、**近 7 天**每日总时长 + 当日 top 3 应用。

## 运行

```bash
# 经典版
cd pyqt
pip install -r requirements.txt
python main.pyw

# Fluent 版
cd fluent
pip install -r requirements.txt
python main.pyw
```

启动后无窗口，直接驻留系统托盘（后台）。双击 `main.pyw` 亦可（无控制台窗口）。开发/测试依赖见各目录 `requirements-dev.txt`。

## 托盘操作

| 操作 | 效果 |
|---|---|
| 右键托盘图标 | 菜单: 显示统计 / 暂停统计 / 退出 |
| 双击托盘图标 | 打开统计窗口 |
| 关闭统计窗口 (X) | 最小化到托盘，继续统计 |
| 暂停统计 (勾选) | 期间不计时，tooltip 显示"已暂停" |

托盘 tooltip 实时显示: 当前应用 + 今日总时长。

## 统计规则

- 每秒探测前台窗口，按 1 秒粒度累计；应用切换 / 每 10 秒 / 退出时写入数据库
- 每次连续使用记为一个**段**，带精确起止时刻（HH:MM:SS）；段跨午夜在 00:00 拆分，跨边界秒数计入新日期；跨小时不拆分
- 段在应用中每 10 秒刷新一次（崩溃最多丢 10 秒），结束时落定最终起止时刻
- **重名窗口处理**：以 exe **完整路径**为身份主键 —— 同名但不同目录的程序各自统计互不混淆；同一应用开多个窗口（如多个浏览器标签）合并为一条；不用窗口标题做身份（标题随内容变化会碎片化统计）
- 排除: 桌面(Progman/WorkerW)、任务栏托盘(Shell_TrayWnd)、锁屏(LogonUI)、dwm、搜索、系统外壳进程、旧式 UWP 宿主(ApplicationFrameHost)、本程序自身
- 提权进程读取路径失败时自动回退到设备路径 + 卷映射
- 单实例 (QSharedMemory + QLocalServer, 参照 Get It): 重复启动不再弹提示，直接**唤醒已有实例的统计窗口**后自身退出

## 数据

- 经典版: `%LOCALAPPDATA%\UsageTracker\usage.db`
- Fluent 版: `%LOCALAPPDATA%\UsageTrackerV4\usage.db`（独立数据目录，两版互不干扰）
- 表 `segments(date, start, end, app_path, app_name, seconds)`，主键 (日期, 段开始时刻, 应用)；同一段刷新时覆盖，不同段各自成行
- v1/v2 旧库（无精确时刻维度）启动时自动备份为 `usage.v1.bak` / `usage.v2.bak` 并重建，不会丢失

## 测试

```bash
cd pyqt && python -m pytest      # 经典版
cd fluent && python -m pytest    # Fluent 版
```

(`pyqt/pytest.ini` 已固定 `qt_api = pyqt6`，本机同时装有 PySide6 时不会选错绑定)

## 目录

```
LICENSE
README.md / README_EN.md
pyqt/               经典版: 自定义 QSS (app/foreground/session/store/theme/widgets/tests)
fluent/             Fluent 版: qfluentwidgets (同源逻辑, widgets 按页拆分)
```

## 已知限制

- 个别旧式 UWP 应用（ApplicationFrameHost 宿主）无法归因到真实应用，计入排除
- 跨午夜的使用段在 00:00 拆分，跨边界秒数计入新日期（1 秒粒度内的跨段误差可忽略）
- v1 → v2 → v3 升级时旧库无法还原更细的时刻维度，故整体备份为 `usage.v1.bak` / `usage.v2.bak` 后重新统计
- 亚秒级的前台切换不统计（对时长统计无意义）
- 暂停统计状态不跨重启保存
