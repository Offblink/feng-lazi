# Feng La Zi (feng-lazi)

A PyQt6 foreground app usage tracker. Runs resident in the system tray and only tracks the app behind the **foreground window**; desktop, taskbar, tray popups, and the lock screen are never counted. Besides duration, it also records **which hour** the usage happened, so you can see at a glance when you used what. The name comes from the nickname of Wang Xifeng in *Dream of the Red Chamber*: Feng La Zi ("the peppery one") keeps a sharp eye on everything, just like this app keeps a sharp eye on your every second.

> 中文: [README.md](README.md)

## Origin

My little brother keeps sneaking in gaming sessions. To prevent any more "incidents" from happening, I built this app. As it happens, we have been watching the 1987 TV adaptation of *Dream of the Red Chamber* together lately — hence the name.

## Dream of the Red Chamber Is Really Good!

> My brother and I have been watching the 1987 TV adaptation of *Dream of the Red Chamber* lately. It is beautifully made — strongly recommended, friends at home and abroad, don't miss it.
> Back to this app: it started because my little brother kept sneaking in gaming sessions, and there was no stopping him. So I made this time tracker. As long as your computer is on, it writes down who is in the foreground and for how long. No denying it.
> It sits quietly in the system tray and stays out of the way. Want to check the books? Double-click to open it: what you used today, how you spent the last seven days, all clear.
> The name came from the show — Feng La Zi keeps the sharpest eye on everyone, which fits perfectly. Now my brother thinks twice before opening a game. Mind your skin.

## Run

```bash
pip install -r requirements.txt
python main.py
```

Starts with no window, resident in the system tray (background). Dev/test dependencies live in `requirements-dev.txt`.

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
- Seconds are credited to the **date + hour** of use, powering the time-of-day distribution view
- **Duplicate names**: identity is the exe **full path** — same-named programs in different directories are tracked separately; multiple windows of one app (e.g. browser tabs) merge into one entry; window titles are never used as identity (they change with content and would fragment the stats)
- Excluded: desktop (Progman/WorkerW), taskbar tray (Shell_TrayWnd), lock screen (LogonUI), dwm, search, system shell processes, legacy UWP host (ApplicationFrameHost), and the app itself
- Falls back to device path + volume mapping when an elevated process denies path reads
- Single instance (QSharedMemory + QLocalServer, following Get It): a second launch does not show a dialog, it **wakes the existing window** and exits itself

## Data

- Location: `%LOCALAPPDATA%\UsageTracker\usage.db` (SQLite, WAL)
- Table `usage(date, hour, app_path, app_name, seconds)`, key (date, hour, app), incrementally accumulated
- v1 databases (no hour dimension) are auto-backed-up to `usage.v1.bak` and rebuilt on startup; nothing is lost

## UI

- Today: total time + **24-hour distribution bars** (with peak-hour label) + per-app proportional bars (icons extracted from the exe)
- Last 7 days: daily total + top 3 apps per day
- Visuals: Minimal & Clean light theme, Segoe UI Variable, single deep-teal accent, Fluent design language

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

(`pytest.ini` pins `qt_api = pyqt6`, so the right binding is used even if PySide6 is also installed.)

## Layout

```
main.pyw            Entry (single instance + resident tray, no console window)
app.py             TrayApp: tray lifecycle + 1-second tracking tick
foreground.py      Win32 foreground detection + exclusion rules (ctypes)
session.py         Tracker accumulation logic (pure logic)
store.py           SQLite storage + aggregate queries (v2: hour dimension)
theme.py           Design tokens (palette / fonts / QSS)
resources/icon.ico App & tray icon (falls back to a runtime-drawn icon)
widgets/           Stats views (today / last 7 days / hour bars / app rows / formatting)
tests/             pytest + qtbot tests
```

## Known limitations

- A few legacy UWP apps (ApplicationFrameHost hosts) cannot be attributed to the real app and are excluded
- A segment crossing midnight or an hour boundary is credited to the new time (sub-second error is negligible)
- v1 → v2 upgrade keeps only daily totals, so the old database is backed up to `usage.v1.bak` and tracking restarts fresh
- Sub-second foreground switches are not tracked (meaningless for usage stats)
- The paused state is not persisted across restarts
