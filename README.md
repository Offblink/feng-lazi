# 凤辣子 (feng-lazi)

前台应用使用时长统计工具，**三个版本**：经典自绘版（`pyqt/`）、Fluent Design 版（`fluent/`，均基于 PyQt6）与 Flet 版（`flet/`）。常驻系统托盘后台运行，只统计**前台窗口**对应的应用；桌面、任务栏、系统托盘、锁屏等状态不计时。每次连续使用都记录**精确起止时刻**（几时几分到几时几分），一眼看出什么时候在用什么。名字取自《红楼梦》王熙凤的绰号，凤辣子盯得紧，你的每一秒它都记着。

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

## 三个版本

| 目录 | 版本 | UI 技术 |
|---|---|---|
| `pyqt/` | 经典版 | PyQt6 + 自定义 QSS（Minimal & Clean 浅色，Segoe UI Variable，深青 accent） |
| `fluent/` | Fluent 版 | PyQt6-Fluent-Widgets（左侧导航，跟随系统深浅色，Win11 Mica 材质） |
| `flet/` | Flet 版 | Flet 0.86（Flutter 引擎渲染），托盘 pystray |

前两版共享同一套跟踪/存储逻辑（`store`/`session`/`foreground` 同源），Flet 版同源移植（新增 `tracking` 编排层），界面内容一致三页：**使用时段**甘特图（每款应用一行**固定高度**时间轴，按精确起止时刻渲染，悬停看 起止时刻 + 时长；应用多到超出窗口高度时出现滚动条）、**各应用**使用总时长比例条列表（图标取自 exe）、**近 7 天**每日总时长 + 当日 top 3 应用。版本差异与 Flet 版踩坑实录见文末 [Flet 版开发实录](#flet-版开发实录)。

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

# Flet 版
cd flet
pip install -r requirements.txt
python main.py
```

启动后无窗口，直接驻留系统托盘（后台）。`pyqt/`、`fluent/` 双击 `main.pyw` 亦可（无控制台窗口）。开发/测试依赖见各目录 `requirements-dev.txt`。Flet 版首次运行会下载 Flutter 桌面客户端（`~/.flet`，需联网）。

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
- Fluent 版: `%LOCALAPPDATA%\UsageTrackerV4\usage.db`
- Flet 版: `%LOCALAPPDATA%\UsageTrackerV5\usage.db`
- 三版数据目录独立，互不干扰；同跑不会互相污染（V5 数据从零开始）
- 表 `segments(date, start, end, app_path, app_name, seconds)`，主键 (日期, 段开始时刻, 应用)；同一段刷新时覆盖，不同段各自成行
- v1/v2 旧库（无精确时刻维度）启动时自动备份为 `usage.v1.bak` / `usage.v2.bak` 并重建，不会丢失

## 测试

```bash
cd pyqt && python -m pytest      # 经典版
cd fluent && python -m pytest    # Fluent 版
cd flet && python -m pytest      # Flet 版
```

(`pyqt/pytest.ini` 已固定 `qt_api = pyqt6`，本机同时装有 PySide6 时不会选错绑定)

## 目录

```
LICENSE
README.md / README_EN.md
pyqt/               经典版: 自定义 QSS (app/foreground/session/store/theme/widgets/tests)
fluent/             Fluent 版: qfluentwidgets (同源逻辑, widgets 按页拆分)
flet/               Flet 版: flet 0.86 (同源逻辑 + tracking/tray/singleton 层)
```

## 已知限制

- 个别旧式 UWP 应用（ApplicationFrameHost 宿主）无法归因到真实应用，计入排除
- 跨午夜的使用段在 00:00 拆分，跨边界秒数计入新日期（1 秒粒度内的跨段误差可忽略）
- v1 → v2 → v3 升级时旧库无法还原更细的时刻维度，故整体备份为 `usage.v1.bak` / `usage.v2.bak` 后重新统计
- 亚秒级的前台切换不统计（对时长统计无意义）
- 暂停统计状态不跨重启保存

## Flet 版开发实录

Flet 版是三个版本里唯一不走 Qt 的：UI 由 Flet 0.86（Python 侧描述控件树，Flutter 引擎渲染），
托盘和单实例没有现成方案，全部自造。以下是实测中遇到的坑，按影响排序。

### 与 Fluent 版对比

| 维度 | fluent (qfluentwidgets) | flet |
|---|---|---|
| UI 技术 | PyQt6 + qfluentwidgets，原生控件 + QPainter 自绘 | Flet 0.86，Flutter 引擎整窗渲染 |
| 托盘 | `QSystemTrayIcon` 原生，菜单信号直连，零延迟 | pystray 独立线程 + 命令队列桥接（≤1s 延迟） |
| 单实例 | `QSharedMemory` + `QLocalServer` 原生 | ctypes `CreateMutexW` + `FindWindowW` 按窗口标题唤醒 |
| 关窗→托盘 | `closeEvent` 拦截一行 | `prevent_close` + `WindowEventType.CLOSE`（事件 `data` 是 None，要读 `.type` 枚举） |
| 退出 | `QApplication.quit()` 同步 | `window.destroy()` 是**协程**必须 `await`；会话关闭竞态抛 `RuntimeError` 需捕获 |
| 应用图标 | `QFileIconProvider` 一行 | ctypes `ExtractIconExW` + `GetDIBits` + Pillow ≈60 行 |
| 布局 | QPainter 任意绘制（QRect 数学） | Dart 客户端**不支持百分比定位**（`parseDouble("25%")` 返回 null），甘特图改像素坐标 + Row expand 权重 |
| 深浅色主题 | `setTheme(Theme.AUTO)` 一行，Mica 材质 | 手写 Material 3 ColorScheme 映射，无 Mica |
| 测试 | qtbot 全套（控件级） | 纯逻辑同源 + 控件树断言（Flet 无 GUI 测试框架） |
| 运行时 | 纯 pip 依赖 | 首次运行下载 Flutter 客户端（`~/.flet`，需联网），内存占用约 240MB |

### 踩坑实录

1. **API 变动大**：Flet 0.86 迁移期，`ft.app` → `ft.run`；`Tab(text=)` → `Tab(label=)` 且 Tabs 重构为
   `TabBar` + `TabBarView`；`ColorScheme` 删了 `background`/`surface_variant`（Material 3 移除）；
   `ft.border.all` 不存在要用 `Border.all` 类方法；`Tooltip` 从包装控件变成目标控件的 `tooltip=` 属性；
   `padding` 助手全删只剩 `Padding` 构造。每一处都是运行时报错才发现，没有静态检查兜底。
2. **启动闪烁**：客户端在 Flutter 首帧完成时自动显示窗口，Python 侧 `window.visible=False` 晚一步生效，
   窗口会闪一下。修法：入口用 `view=FLET_APP_HIDDEN`，flet 启动器才会给客户端设
   `FLET_HIDE_WINDOW_ON_START`（首帧不显示）。
3. **托盘退出无效**：`window.destroy()` 是协程，没 `await` 时应用永远退不掉，只能杀进程。
   且 destroy 后会话关闭有竞态，间歇抛 `RuntimeError: Session closed`，需 try/except 收口。
4. **幽灵窗口假象**：排查渲染问题时用 `taskkill /F` 强杀探针进程，死进程的窗口对象残留（幽灵窗口），
   截图抓到的全是空白死窗口，一度误判"本机 Flutter 不渲染"。修法：唯一窗口标题 + 校验属主进程存活
   + PrintWindow 抓活窗口。教训：杀进程要连窗口一起清，截图前先验证窗口还活着。
5. **64 位 ctypes 指针截断**：ctypes 默认把参数当 `c_int`，句柄/指针类 API（`FindWindowW`、
   `ExtractIconExW`、`GetDIBits`）必须显式声明 `argtypes`/`restype`，否则返回值被截断成 32 位，
   表现为随机崩溃或 Access Violation。
6. **首次运行下载客户端**：flet 桌面客户端按版本缓存到 `~/.flet/client`，下载失败或网络受限时
   窗口起不来；版本升级会重新下载。Qt 系版本无此问题。

### 结论

- 跟踪/存储/探测三层（`foreground`/`session`/`store`）三版同源，迁移成本极低，
  差异全部集中在 UI 壳和进程生命周期。
- fluent 在 Windows 上更省心：托盘、单实例、图标、深浅色全是现成的，
  调试和测试工具链成熟（qtbot）。
- flet 的优势是纯 Python 描述 UI、跨平台渲染一致、控件树可编程化，
  但为补 Windows 桌面缺口（托盘/单实例/窗口生命周期）付出的代码和调试成本明显更高。
- 选型建议：纯 Windows 个人工具 → Qt 系（pyqt/fluent），省心；正经跨平台桌面 → Tauri 2
  （原生托盘/单实例/小体积）+ WebUI（HTML/CSS 样式能力与生态碾压代码式 UI），成本是两门语言
  和进程边界；Flet 的"纯 Python 写 UI"价值有限，只对不想碰第二门语言的纯 Python 工作流有意义，
  UI 生态（样式/组件/devtools）明显弱于 Web。另外本应用的数据层本身 Windows 绑定
  （`foreground.py` 是 Win32 ctypes），跨平台需重写探测层并适配各平台权限，
  UI 壳跨了平台收益也有限，实际是 Windows 优先。
