# Feng La Zi (feng-lazi)

A foreground app usage tracker in **three editions**: the classic hand-styled one (`pyqt/`), the Fluent Design one (`fluent/`, both built on PyQt6), and the Flet edition (`flet/`). Runs resident in the system tray and only tracks the app behind the **foreground window**; desktop, taskbar, tray popups, and the lock screen are never counted. Every continuous session is recorded with its **exact start and stop time** (hour:minute to hour:minute), so you can see at a glance when you used what. The name comes from the nickname of Wang Xifeng in *Dream of the Red Chamber*: Feng La Zi ("the peppery one") keeps a sharp eye on everything, just like this app keeps a sharp eye on your every second.

> 中文: [README.md](README.md)

## Origin

My little brother keeps sneaking in gaming sessions. To prevent any more "incidents" from happening, I built this app. As it happens, we have been watching the 1987 TV adaptation of *Dream of the Red Chamber* together lately — hence the name.

## Dream of the Red Chamber Is Really Good!

>
Lots of people (especially some of my male friends) have held a bias against this novel since they were kids, so they just can't get into it.
>
But honestly, if you're willing to give it a shot, go check out the '87 TV adaptation — it's so good!
>
The character styling is incredibly faithful, and the atmosphere is perfectly crafted.
>
It truly deserves the title of the greatest TV series on earth! ⬅️ At least in my humble opinion 😕
>

## Three editions

| Directory | Edition | UI technology |
|---|---|---|
| `pyqt/` | Classic | PyQt6 + hand-written QSS (Minimal & Clean light theme, Segoe UI Variable, deep-teal accent) |
| `fluent/` | Fluent | PyQt6-Fluent-Widgets (left navigation, follows system dark/light, Win11 Mica) |
| `flet/` | Flet | Flet 0.86 (Flutter-engine rendering), pystray tray |

The first two editions share the same tracking/storage logic (`store`/`session`/`foreground` are the same source); the Flet edition is a same-source port (adds a `tracking` orchestration layer). All three show the same three pages: **Usage periods** gantt (one **fixed-height** timeline row per app, segments rendered at exact start/stop times, hover shows start/stop + duration; a scrollbar appears when the rows exceed the window height), **Apps** per-app total usage with proportional bars (icons extracted from the exe), **Last 7 days** daily total + top 3 apps per day. Edition differences and the Flet pitfalls are covered in [Flet edition development notes](#flet-edition-development-notes).

## Run

```bash
# Classic edition
cd pyqt
pip install -r requirements.txt
python main.pyw

# Fluent edition
cd fluent
pip install -r requirements.txt
python main.pyw

# Flet edition
cd flet
pip install -r requirements.txt
python main.py
```

Starts with no window, resident in the system tray (background). `pyqt/` and `fluent/` can also be launched by double-clicking `main.pyw` (no console window). Dev/test dependencies live in each directory's `requirements-dev.txt`. The Flet edition downloads the Flutter desktop client on first run (`~/.flet`, needs network).

## Tray usage

| Action | Effect |
|---|---|
| Right-click tray icon | Menu: Show stats / Pause tracking / Quit |
| Double-click tray icon | Open stats window |
| Close stats window (X) | Minimize to tray, keep tracking |
| Pause tracking (checked) | Nothing is counted meanwhile; tooltip shows "paused" |

The tray tooltip shows in real time: current app + today's total.

## Tracking rules

- Polls the foreground window every second, accumulated at 1-second granularity; written to the database on app switch / every 10 seconds / on quit
- Every continuous session is a **segment** with exact start/stop times (HH:MM:SS); segments crossing midnight split at 00:00, with boundary seconds credited to the new date; hour boundaries do not split
- The open segment is refreshed in the database every 10 seconds (a crash loses at most 10 s); the final start/stop times are settled when the session ends
- **Duplicate names**: identity is the exe **full path** — same-named programs in different directories are tracked separately; multiple windows of one app (e.g. browser tabs) merge into one entry; window titles are never used as identity (they change with content and would fragment the stats)
- Excluded: desktop (Progman/WorkerW), taskbar tray (Shell_TrayWnd), lock screen (LogonUI), dwm, search, system shell processes, legacy UWP host (ApplicationFrameHost), and the app itself
- Falls back to device path + volume mapping when an elevated process denies path reads
- Single instance (QSharedMemory + QLocalServer on the Qt editions; a named mutex + window-title wake on the Flet edition): a second launch does not show a dialog, it **wakes the existing window** and exits itself

## Data

- Classic edition: `%LOCALAPPDATA%\UsageTracker\usage.db`
- Fluent edition: `%LOCALAPPDATA%\UsageTrackerV4\usage.db`
- Flet edition: `%LOCALAPPDATA%\UsageTrackerV5\usage.db`
- The three editions keep separate data directories and never interfere (V5 starts from scratch)
- Table `segments(date, start, end, app_path, app_name, seconds)`, key (date, start, app); the open segment is overwritten on refresh, separate sessions become separate rows
- v1/v2 databases (no exact-time dimension) are auto-backed-up to `usage.v1.bak` / `usage.v2.bak` and rebuilt on startup; nothing is lost

## Tests

```bash
cd pyqt && python -m pytest      # classic
cd fluent && python -m pytest    # fluent
cd flet && python -m pytest      # flet
```

(`pyqt/pytest.ini` pins `qt_api = pyqt6`, so the right binding is used even if PySide6 is also installed.)

## Layout

```
LICENSE
README.md / README_EN.md
pyqt/               Classic edition: hand-written QSS (app/foreground/session/store/theme/widgets/tests)
fluent/             Fluent edition: qfluentwidgets (same logic source, widgets split per page)
flet/               Flet edition: flet 0.86 (same logic source + tracking/tray/singleton layer)
```

## Known limitations

- A few legacy UWP apps (ApplicationFrameHost hosts) cannot be attributed to the real app and are excluded
- A segment crossing midnight splits at 00:00, boundary seconds credited to the new date (sub-second error is negligible)
- v1 → v2 → v3 upgrades cannot restore a finer time dimension, so the old database is backed up to `usage.v1.bak` / `usage.v2.bak` and tracking restarts fresh
- Sub-second foreground switches are not tracked (meaningless for usage stats)
- The paused state is not persisted across restarts

## Flet edition development notes

The Flet edition is the only one that does not use Qt: the UI is described from Python (Flet 0.86) and rendered by the Flutter engine, and neither the tray nor single-instance comes out of the box, so both were built by hand. The pitfalls below are the ones actually hit, roughly in impact order.

### Flet vs. Fluent

| Dimension | fluent (qfluentwidgets) | flet |
|---|---|---|
| UI tech | PyQt6 + qfluentwidgets, native widgets + QPainter | Flet 0.86, whole window rendered by Flutter |
| Tray | Native `QSystemTrayIcon`, signals wired directly, zero latency | pystray in its own thread + command-queue bridge (≤1 s latency) |
| Single instance | Native `QSharedMemory` + `QLocalServer` | ctypes `CreateMutexW` + `FindWindowW` wake by window title |
| Close-to-tray | One-line `closeEvent` override | `prevent_close` + `WindowEventType.CLOSE` (event `data` is `None`; read the `.type` enum) |
| Quit | Synchronous `QApplication.quit()` | `window.destroy()` is a **coroutine** that must be `await`ed; the session teardown race throws `RuntimeError` and needs a guard |
| App icons | One line with `QFileIconProvider` | ctypes `ExtractIconExW` + `GetDIBits` + Pillow, ≈60 lines |
| Layout | Free QPainter drawing (QRect math) | Dart client **does not support percentage positioning** (`parseDouble("25%")` returns null); gantt uses pixel coordinates + Row expand weights instead |
| Dark/light theme | `setTheme(Theme.AUTO)` in one line, Mica material | Hand-mapped Material 3 ColorScheme, no Mica |
| Testing | Full qtbot suite (widget level) | Same-source pure logic + control-tree assertions (Flet has no GUI test framework) |
| Runtime | Plain pip dependencies | Downloads the Flutter client on first run (`~/.flet`, needs network); ~240 MB memory |

### Pitfalls encountered

1. **Churny API**: Flet 0.86 is mid-migration. `ft.app` → `ft.run`; `Tab(text=)` → `Tab(label=)` and `Tabs` was rebuilt around `TabBar` + `TabBarView`; `ColorScheme` dropped `background`/`surface_variant` (Material 3 removal); `ft.border.all` does not exist, use the `Border.all` classmethod; `Tooltip` changed from a wrapping control to a `tooltip=` property on the target; the `padding` helpers are gone, only the `Padding` constructor remains. Every one of these surfaced as a runtime error, with no static checks to catch them.
2. **Startup flash**: the client shows the window when Flutter's first frame completes, so Python-side `window.visible=False` is too late and the window flashes once. Fix: launch with `view=FLET_APP_HIDDEN`; only then does the flet launcher set `FLET_HIDE_WINDOW_ON_START` on the client (first frame stays hidden).
3. **Tray quit did nothing**: `window.destroy()` is a coroutine; without `await` the app can never exit and only a process kill works. On top of that, the session teardown after destroy races and intermittently raises `RuntimeError: Session closed`, which needs a try/except.
4. **Ghost-window illusion**: while debugging rendering, probe processes were killed with `taskkill /F`, which leaves the dead process's window objects behind ("ghost windows"); screenshots kept capturing blank dead windows, and the renderer was wrongly diagnosed as broken. Fix: unique window titles + verify the owning process is alive + PrintWindow only live windows. Lesson: when you kill a process, clear its windows too; check the window is alive before screenshotting.
5. **64-bit ctypes pointer truncation**: ctypes defaults arguments to `c_int`; handle/pointer APIs (`FindWindowW`, `ExtractIconExW`, `GetDIBits`) must declare explicit `argtypes`/`restype` or return values get truncated to 32 bits, showing up as random crashes or access violations.
6. **First-run client download**: the Flet desktop client is cached per version in `~/.flet/client`; a failed or blocked download means the window never comes up, and version upgrades re-download. The Qt editions have none of this.

### Takeaway

- The tracking/storage/probing layers (`foreground`/`session`/`store`) are the same source across all three editions; porting is cheap and all the difference lives in the UI shell and process lifecycle.
- On Windows, fluent is the low-friction option: tray, single instance, icons, and dark/light theming are all built in, and the debugging/test toolchain is mature (qtbot).
- Flet's upside is describing UI in pure Python with consistent cross-platform rendering and a programmable control tree, but the code and debugging cost of filling the Windows desktop gaps (tray, single instance, window lifecycle) is clearly higher.
- Choosing: for a Windows-only personal tool, go Qt (`pyqt`/`fluent`); for a serious cross-platform desktop app, Tauri 2 (native tray/single-instance/small binaries) plus a WebUI (HTML/CSS styling power and ecosystem beat any code-driven UI framework) is the better fit, at the cost of two languages and a process boundary. Flet's "write UI in Python" is only meaningful for pure-Python workflows that want to avoid a second language, and its UI ecosystem (styling, components, devtools) is clearly weaker than the Web. Note also that this app's data layer is Windows-bound (`foreground.py` is Win32 ctypes), so real cross-platform means rewriting the probing layer and adapting per-platform permissions; a cross-platform UI shell alone buys little. In practice this project is Windows-first.
