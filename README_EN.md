# Feng La Zi (feng-lazi)

A PyQt6 foreground app usage tracker in **two editions**: the classic hand-styled one (`pyqt/`) and the Fluent Design one (`fluent/`). Runs resident in the system tray and only tracks the app behind the **foreground window**; desktop, taskbar, tray popups, and the lock screen are never counted. Every continuous session is recorded with its **exact start and stop time** (hour:minute to hour:minute), so you can see at a glance when you used what. The name comes from the nickname of Wang Xifeng in *Dream of the Red Chamber*: Feng La Zi ("the peppery one") keeps a sharp eye on everything, just like this app keeps a sharp eye on your every second.

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

## Two editions

| Directory | Edition | UI technology |
|---|---|---|
| `pyqt/` | Classic | PyQt6 + hand-written QSS (Minimal & Clean light theme, Segoe UI Variable, deep-teal accent) |
| `fluent/` | Fluent | PyQt6-Fluent-Widgets (left navigation, follows system dark/light, Win11 Mica) |

Both editions share the same tracking/storage logic (`store`/`session`/`foreground` are the same source) and the same three pages: **Usage periods** gantt (one timeline row per app, segments rendered at exact start/stop times, hover shows start/stop + duration), **Apps** per-app total usage with proportional bars (icons extracted from the exe), **Last 7 days** daily total + top 3 apps per day.

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
```

Starts with no window, resident in the system tray (background). Dev/test dependencies live in each directory's `requirements-dev.txt`.

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
- Single instance (QSharedMemory + QLocalServer, following Get It): a second launch does not show a dialog, it **wakes the existing window** and exits itself

## Data

- Classic edition: `%LOCALAPPDATA%\UsageTracker\usage.db`
- Fluent edition: `%LOCALAPPDATA%\UsageTrackerV4\usage.db` (separate data dir; the two editions never interfere)
- Table `segments(date, start, end, app_path, app_name, seconds)`, key (date, start, app); the open segment is overwritten on refresh, separate sessions become separate rows
- v1/v2 databases (no exact-time dimension) are auto-backed-up to `usage.v1.bak` / `usage.v2.bak` and rebuilt on startup; nothing is lost

## Tests

```bash
cd pyqt && python -m pytest      # classic
cd fluent && python -m pytest    # fluent
```

(`pyqt/pytest.ini` pins `qt_api = pyqt6`, so the right binding is used even if PySide6 is also installed.)

## Layout

```
LICENSE
README.md / README_EN.md
pyqt/               Classic edition: hand-written QSS (app/foreground/session/store/theme/widgets/tests)
fluent/             Fluent edition: qfluentwidgets (same logic source, widgets split per page)
```

## Known limitations

- A few legacy UWP apps (ApplicationFrameHost hosts) cannot be attributed to the real app and are excluded
- A segment crossing midnight splits at 00:00, boundary seconds credited to the new date (sub-second error is negligible)
- v1 → v2 → v3 upgrades cannot restore a finer time dimension, so the old database is backed up to `usage.v1.bak` / `usage.v2.bak` and tracking restarts fresh
- Sub-second foreground switches are not tracked (meaningless for usage stats)
- The paused state is not persisted across restarts
