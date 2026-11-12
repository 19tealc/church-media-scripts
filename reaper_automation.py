#!/usr/bin/env python3
"""
Church Media - Reaper Automation
- Weekday services run on a fixed automated schedule
- Saturday and Sunday afternoon (12pm+) prompt for a show name and optional record times
"""

import subprocess
import json
import time
import datetime
import os
import sys

TEST_MODE = "--test" in sys.argv

# ─── PATHS ────────────────────────────────────────────────────────────────────

REAPER_PATH       = "/Applications/REAPER.app/Contents/MacOS/REAPER"
# SoundGrid QRec must already be up before Reaper opens.
QREC_PATH         = "/Applications/Waves/SoundGrid QRec/SoundGrid QRec.app"

# MarkerMatic pulls snapshot markers off the DiGiCo board into the Reaper recording.
# Its record button isn't exposed to accessibility, so it's clicked by position —
# offset is measured from the top-left of the MarkerMatic window.
MARKERMATIC_PATH        = "/Applications/MarkerMatic.app"
MARKERMATIC_REC_OFFSET  = (40, 101)   # leftmost (red) button in the mode row
MARKERMATIC_TIMEOUT     = 30          # seconds to wait for it to connect to Reaper

SAVE_FOLDER       = os.path.expanduser("~/Documents/REAPER Media")
DATE_FORMAT       = "%b. %d %Y"   # e.g., "May. 07 2026"
REAPER_LOAD_DELAY = 8             # seconds to wait after Reaper launches

TEMPLATE_FOLDER   = os.path.expanduser(
    "~/Library/Application Support/REAPER/ProjectTemplates"
)

# Template used for scheduled services (Sunday morning, Wednesday night)
DEFAULT_TEMPLATE  = os.path.join(TEMPLATE_FOLDER, "Sunday Service 2026.RPP")

# ─── STREAM CHECK WINDOWS ─────────────────────────────────────────────────────
# Safari windows opened during the service to spot-check the stream.
# Bounds are {left, top, right, bottom}. Edit a URL here if a link ever breaks.

STREAM_TAB_DELAY = 3   # seconds between opening each window (avoids Safari crash)

# "Live Stream Monitor.html" shows the YouTube and Facebook streams side by side
# in one window, so this script opens two windows instead of three.
#
# It is served over http://localhost rather than opened as a file:// page on
# purpose: Safari refuses localStorage on file:// URLs, which would wipe the
# saved stream links every service, and Facebook's embed is unreliable there too.
MONITOR_FILE = "Live Stream Monitor.html"
MONITOR_PORT = 8765
MONITOR_URL  = f"http://localhost:{MONITOR_PORT}/{MONITOR_FILE.replace(' ', '%20')}"

# Windows are stacked evenly down the left column; heights are worked out at
# run time from the usable screen area, so they never land under the Dock.
STREAM_COLUMN_WIDTH = 960

STREAM_CHECKS = [
    ("Resi",           "https://studio.resi.io"),
    ("Stream Monitor", MONITOR_URL),
]

# ─── SERVICE SCHEDULES ────────────────────────────────────────────────────────

SERVICES = {
    "Sunday": {
        "name":         "Sunday Service",
        "template":     DEFAULT_TEMPLATE,
        "open_time":    datetime.time( 8, 45,  0),   # 8:45 AM
        "record_start": datetime.time(10, 19, 58),   # 10:19:58 AM
        # The DiGiCo board stops the recording: a macro on the last snapshot
        # of the service fires stop_recording_safe.lua over OSC. So there is
        # no record_stop time — the script waits for the board instead.
        "record_stop":  None,
        "board_stop":   True,
        "layout_time":  datetime.time(10, 21, 33),   # record start + 95s, so the
                                                     # 90s-delayed stream is visible
    },
    "Wednesday": {
        "name":         "Wednesday Night",
        "template":     DEFAULT_TEMPLATE,
        "open_time":    datetime.time(18,  0,  0),   # 6:00 PM
        "record_start": datetime.time(18, 45,  0),   # 6:45 PM
        "record_stop":  datetime.time(20,  0,  0),   # ← update to your real time
    },
    # Add more scheduled services here as needed
}

# Sunday morning runs until this hour — after this, prompt for a special show name
SUNDAY_MORNING_CUTOFF = datetime.time(12, 0, 0)   # 12:00 PM

# ──────────────────────────────────────────────────────────────────────────────


def log(msg):
    ts = datetime.datetime.now().strftime("%I:%M:%S %p")
    print(f"[{ts}] {msg}", flush=True)


def wait_until(target: datetime.time, label: str = ""):
    if TEST_MODE:
        log(f"  [TEST] Pausing 10s instead of waiting until {target.strftime('%I:%M:%S %p')}")
        time.sleep(10)
        return
    now = datetime.datetime.now()
    target_dt = now.replace(
        hour=target.hour, minute=target.minute,
        second=target.second, microsecond=0
    )
    if target_dt <= now:
        return

    # Live countdown, updated in place on one line
    desc = label or target.strftime("%I:%M:%S %p")
    while True:
        remaining = (target_dt - datetime.datetime.now()).total_seconds()
        if remaining <= 0:
            break
        h, rem = divmod(int(remaining), 3600)
        m, s   = divmod(rem, 60)
        clock  = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        print(f"\r  ⏳ {desc} in {clock}   ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 60 + "\r", end="", flush=True)


def applescript(script: str):
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        log(f"  Warning: {result.stderr.strip()}")
    return result


def parse_time_input(prompt_text: str):
    """Ask for a time like '2:30 PM' or '14:30'. Returns a datetime.time or None."""
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            return None
        for fmt in ("%I:%M %p", "%I:%M:%S %p", "%H:%M", "%H:%M:%S"):
            try:
                return datetime.datetime.strptime(raw.upper(), fmt.upper()).time()
            except ValueError:
                continue
        print("  Couldn't read that time. Try formats like  2:30 PM  or  14:30  (or just press Enter to skip)")


def prompt_template() -> str:
    """List available Reaper templates and let the user pick one by number."""
    templates = sorted(
        f for f in os.listdir(TEMPLATE_FOLDER)
        if f.lower().endswith(".rpp")
    )
    if not templates:
        log(f"  No templates found in {TEMPLATE_FOLDER} — using default.")
        return DEFAULT_TEMPLATE

    print()
    print("  Available templates:")
    for i, name in enumerate(templates, 1):
        print(f"    {i}. {name[:-4]}")

    while True:
        raw = input(f"  Pick a template (1-{len(templates)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(templates):
            choice = templates[int(raw) - 1]
            print(f"  Using: {choice[:-4]}")
            return os.path.join(TEMPLATE_FOLDER, choice)
        print("  Please enter one of the listed numbers.")


def prompt_special_show() -> dict:
    """Interactive setup for Saturday or Sunday-afternoon special shows."""
    print()
    print("  ┌─────────────────────────────────────┐")
    print("  │        SPECIAL SHOW SETUP           │")
    print("  └─────────────────────────────────────┘")

    name = input("  Show name: ").strip()
    if not name:
        name = "Special Show"

    template = prompt_template()

    print()
    print("  Enter record start/stop times, or press Enter to control recording manually.")
    record_start = parse_time_input("  Record START time (e.g. 2:30 PM) or Enter to skip: ")
    record_stop  = parse_time_input("  Record STOP  time (e.g. 3:45 PM) or Enter to skip: ") if record_start else None

    print()
    return {
        "name":         name,
        "template":     template,
        "open_time":    None,          # open immediately for specials
        "record_start": record_start,
        "record_stop":  record_stop,
    }


def build_filename(prefix: str) -> str:
    if TEST_MODE:
        prefix = f"TEST {prefix}"
    date_str = datetime.datetime.now().strftime(DATE_FORMAT)
    base = f"{prefix} {date_str}"

    def taken(name):
        # Each project lives in its own folder; also check the old loose layout
        return (os.path.exists(os.path.join(SAVE_FOLDER, name))
                or os.path.exists(os.path.join(SAVE_FOLDER, name + ".RPP")))

    if not taken(base):
        return base

    for take in range(2, 20):
        candidate = f"{base} Take {take}"
        if not taken(candidate):
            log(f"  File already exists — using: {candidate}")
            return candidate

    return base + " (extra)"


def qrec_running() -> bool:
    """True if the SoundGrid QRec app is running."""
    result = subprocess.run(
        ["pgrep", "-f", f"{QREC_PATH}/Contents/MacOS/SoundGrid QRec"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def verify_qrec():
    """Confirm SoundGrid QRec is up before Reaper opens."""
    log("Checking SoundGrid QRec...")

    if qrec_running():
        log("  ✓ SoundGrid QRec is running.")
        return True

    print()
    print("  ┌───────────────────────────────────────────────────┐")
    print("  │  🚨 SOUNDGRID QREC IS NOT RUNNING!                │")
    print("  │     Open QRec and make sure it is ready           │")
    print("  │     BEFORE Reaper opens.                          │")
    print("  └───────────────────────────────────────────────────┘")
    print()

    while not qrec_running():
        input("  Press Enter once SoundGrid QRec is open... ")
        if not qrec_running():
            log("  Still not detecting QRec — check that it is actually open.")

    log("  ✓ SoundGrid QRec detected.")
    return True


def markermatic_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", f"{MARKERMATIC_PATH}/Contents/MacOS/MarkerMatic"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def markermatic_status() -> str:
    """The status lines shown in the MarkerMatic window, joined with '|'."""
    result = applescript('''
tell application "System Events" to tell process "MarkerMatic"
    set out to ""
    repeat with t in (static texts of window 1)
        set out to out & ((name of t) as text) & "|"
    end repeat
    return out
end tell
''')
    return result.stdout.strip()


def markermatic_reaper_connected() -> bool:
    status = markermatic_status()
    return "Reaper is connected" in status


def ensure_markermatic():
    """Open MarkerMatic and wait for it to connect to Reaper."""
    log("Checking MarkerMatic...")

    if not markermatic_running():
        log("  MarkerMatic not running — launching it...")
        subprocess.run(["open", "-a", MARKERMATIC_PATH], capture_output=True, text=True)
        time.sleep(4)
    else:
        log("  ✓ MarkerMatic is already running.")

    # Wait for it to find Reaper (Reaper must already be open)
    for _ in range(MARKERMATIC_TIMEOUT):
        if markermatic_reaper_connected():
            log("  ✓ MarkerMatic connected to Reaper.")
            status = markermatic_status()
            for line in status.split("|"):
                if "connected" in line and "Reaper" not in line:
                    log(f"    {line}")
            return True
        time.sleep(1)

    print()
    print("  ┌───────────────────────────────────────────────────┐")
    print("  │  ⚠  MARKERMATIC NOT CONNECTED TO REAPER!          │")
    print("  │     Snapshot markers may not be recorded.         │")
    print("  │     Check MarkerMatic before the service starts.   │")
    print("  └───────────────────────────────────────────────────┘")
    log(f"  Status: {markermatic_status()}")
    print()
    return False


def markermatic_record():
    """Click MarkerMatic's record button (not exposed to accessibility)."""
    log("Starting MarkerMatic...")
    x, y = MARKERMATIC_REC_OFFSET
    applescript(f'''
tell application "MarkerMatic" to activate
delay 0.6
tell application "System Events" to tell process "MarkerMatic"
    set {{wx, wy}} to position of window 1
    click at {{wx + {x}, wy + {y}}}
end tell
''')
    log("  MarkerMatic record clicked.")


def launch_reaper(template: str):
    log("Launching Reaper...")
    # start_new_session detaches Reaper from the Terminal, so closing the
    # Terminal window won't quit Reaper
    subprocess.Popen(
        [REAPER_PATH, "-template", template],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log(f"  Waiting {REAPER_LOAD_DELAY}s for Reaper to load...")
    time.sleep(REAPER_LOAD_DELAY)
    log("  Reaper ready.")


def save_project(prefix: str):
    filename = build_filename(prefix)
    # Save into a dated folder of its own. The templates leave the record path
    # blank, so Reaper records into the project's folder — this keeps each
    # service's mic recordings together instead of loose in REAPER Media.
    # (Leave Reaper's "Create subdirectory for project" box UNticked, or the
    # project ends up one folder deeper.)
    project_dir = os.path.join(SAVE_FOLDER, filename)
    os.makedirs(project_dir, exist_ok=True)
    folder   = project_dir.rstrip("/") + "/"
    log(f"Saving project as: {filename}/{filename}.RPP")

    script = f'''
tell application "REAPER" to activate
delay 0.5
tell application "System Events"
    tell process "REAPER"
        keystroke "s" using {{command down, option down}}
        delay 0.9
        keystroke "g" using {{command down, shift down}}
        delay 0.5
        keystroke "{folder}"
        delay 0.2
        key code 36
        delay 0.6
        keystroke "{filename}"
        delay 0.2
        key code 36
    end tell
end tell
'''
    applescript(script)
    log(f"  Saved: {filename}/{filename}.RPP")


def usable_screen():
    """Top and bottom edge of the screen once the menu bar and Dock are excluded.

    A window placed past these edges gets silently shoved back by the window
    server — that is what made a full-height 0-1080 layout overlap itself.
    """
    js = ('ObjC.import("AppKit");'
          'var f = $.NSScreen.mainScreen.visibleFrame,'
          '    g = $.NSScreen.mainScreen.frame;'
          'JSON.stringify([f.origin.y, f.size.height, g.size.height])')
    try:
        out = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", js],
            capture_output=True, text=True, timeout=10,
        ).stdout
        dock, visible_height, full_height = json.loads(out)
        menu_bar = full_height - dock - visible_height
        return int(menu_bar), int(full_height - dock)
    except Exception:
        return 30, 990   # sane default for a 1920x1080 display


def stream_window_bounds():
    """Even vertical split of the left column, one slot per stream window."""
    top, bottom = usable_screen()
    count = len(STREAM_CHECKS)
    slot = (bottom - top) // count
    rows = []
    for i in range(count):
        row_top = top + (i * slot)
        row_bottom = bottom if i == count - 1 else row_top + slot
        rows.append((0, row_top, STREAM_COLUMN_WIDTH, row_bottom))
    return rows


def ensure_monitor_server():
    """Serve this folder on localhost so the stream monitor page can load.

    Bound to 127.0.0.1 only — this folder holds our scripts and must not be
    reachable from the rest of the network. Reuses an existing server if one
    is already listening, so repeat runs don't stack up processes.
    """
    import socket

    with socket.socket() as probe:
        probe.settimeout(0.4)
        if probe.connect_ex(("127.0.0.1", MONITOR_PORT)) == 0:
            log(f"  Stream monitor server already running on port {MONITOR_PORT}.")
            return True

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(script_dir, MONITOR_FILE)):
        log(f"  ⚠  {MONITOR_FILE} not found — skipping stream monitor window.")
        return False

    subprocess.Popen(
        ["python3", "-m", "http.server", str(MONITOR_PORT),
         "--bind", "127.0.0.1", "--directory", script_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,   # outlives this script, so the page keeps working
    )

    # give it a moment to bind before Safari asks for the page
    for _ in range(20):
        time.sleep(0.25)
        with socket.socket() as probe:
            probe.settimeout(0.4)
            if probe.connect_ex(("127.0.0.1", MONITOR_PORT)) == 0:
                log(f"  Stream monitor server started on port {MONITOR_PORT}.")
                return True

    log("  ⚠  Stream monitor server did not start — opening it anyway.")
    return False


def close_stream_windows():
    """Close only the Safari windows this script opened, and stop the server.

    Matched by URL so the operator's own Safari windows are left alone.
    Collected first, then closed — closing while iterating skips windows.
    """
    log("Closing stream check windows...")

    script = f'''
tell application "Safari"
    set doomed to {{}}
    repeat with w in windows
        try
            set u to URL of current tab of w
            if u contains "studio.resi.io" or u contains "localhost:{MONITOR_PORT}" then
                set end of doomed to w
            end if
        end try
    end repeat
    set n to count of doomed
    repeat with w in doomed
        try
            close w
        end try
    end repeat
    return n
end tell
'''
    result = applescript(script)
    closed = result.stdout.strip() or "0"
    log(f"  Closed {closed} stream window(s).")

    # Stop the local server this script started for the monitor page.
    subprocess.run(
        ["pkill", "-f", f"http.server {MONITOR_PORT}"],
        capture_output=True,
    )
    log(f"  Stream monitor server on port {MONITOR_PORT} stopped.")


def setup_screen_layout():
    log("Setting up screen layout...")

    ensure_monitor_server()

    parts = []
    layout = stream_window_bounds()
    for i, ((label, url), bounds) in enumerate(zip(STREAM_CHECKS, layout)):
        if i:
            parts.append(f"delay {STREAM_TAB_DELAY}")
        activate = "\n    activate" if i == 0 else ""
        parts.append(f'''tell application "Safari"{activate}
    make new document with properties {{URL:"{url}"}}
    tell window 1
        set bounds to {{{bounds[0]}, {bounds[1]}, {bounds[2]}, {bounds[3]}}}
    end tell
end tell''')
        log(f"  Opening {label}...")

    parts.append('''tell application "System Events"
    tell process "REAPER"
        set bounds of window 1 to {960, 0, 1920, 1080}
    end tell
end tell
tell application "REAPER" to activate''')

    applescript("\n".join(parts))
    log("  Screen layout ready.")


def recent_media_bytes(max_age_secs=90):
    """Total size of audio files under SAVE_FOLDER modified in the last max_age_secs."""
    total = 0
    cutoff = time.time() - max_age_secs
    for root, _dirs, files in os.walk(SAVE_FOLDER):
        for f in files:
            if f.lower().endswith((".wav", ".flac", ".mp3", ".ogg")):
                path = os.path.join(root, f)
                try:
                    st = os.stat(path)
                    if st.st_mtime >= cutoff:
                        total += st.st_size
                except OSError:
                    pass
    return total


def verify_recording() -> bool:
    """Confirm Reaper is really recording by watching media files grow."""
    log("  Verifying recording...")
    size1 = recent_media_bytes()
    time.sleep(5)
    size2 = recent_media_bytes()
    if size2 > size1:
        log("  ✓ Recording confirmed — media files are growing.")
        return True
    return False


def send_record_keystroke():
    applescript('''
tell application "REAPER" to activate
delay 1
tell application "System Events"
    tell process "REAPER"
        keystroke "r" using {command down}
    end tell
end tell
''')


def start_recording():
    log("Starting recording...")
    send_record_keystroke()

    if verify_recording():
        return

    log("  ⚠ Recording NOT detected — retrying Cmd+R...")
    send_record_keystroke()
    if verify_recording():
        return

    print()
    print("  ┌───────────────────────────────────────────────────┐")
    print("  │  🚨 RECORDING COULD NOT BE CONFIRMED!             │")
    print("  │     CHECK REAPER NOW and start recording          │")
    print("  │     manually if needed (Cmd+R).                   │")
    print("  └───────────────────────────────────────────────────┘")
    print()


def stop_recording():
    log("Stopping recording...")
    script = '''
tell application "REAPER" to activate
delay 0.3
tell application "System Events"
    tell process "REAPER"
        key code 49
        delay 1.5
        try
            click button "Save All" of window 1
        end try
        delay 1
        keystroke "s" using {command down}
    end tell
end tell
'''
    applescript(script)
    log("  Recording stopped — media files and project saved.")
    log("  Reaper is ready to close manually.")


def wait_for_board_record_stop(quiet_seconds=30) -> bool:
    """Block until recording stops (media files stop growing for a while)."""
    if TEST_MODE:
        quiet_seconds = 15
        log("  [TEST] Watching for the recording to stop (15s of quiet).")

    log("Recording — waiting for the board to stop it...")
    log("  (last snapshot of the service)")

    needed = max(1, quiet_seconds // 5)
    last = recent_media_bytes()
    unchanged = 0

    while True:
        time.sleep(5)
        current = recent_media_bytes()
        if current > last:
            unchanged = 0
        else:
            unchanged += 1
            if unchanged >= needed:
                log("  ✓ Recording stopped.")
                return True
        last = current


def save_and_quit_reaper():
    """Save the project and close Reaper cleanly."""
    log("Saving project and closing Reaper...")

    # The stop script already saved recorded media and the project, but a
    # second Cmd+S is harmless and covers a manual stop.
    applescript('''
tell application "REAPER" to activate
delay 0.5
tell application "System Events"
    tell process "REAPER"
        keystroke "s" using {command down}
    end tell
end tell
''')
    time.sleep(2)

    applescript('tell application "REAPER" to quit')
    time.sleep(2)

    # If Reaper asks about unsaved changes, accept it.
    #
    # System Events sends keystrokes to whatever app is FRONTMOST — a
    # "tell process" block does not redirect them. So only act if Reaper is
    # still running, bring it to the front first, and prefer clicking the
    # button by name over a blind Return that could land in Safari.
    applescript('''
tell application "System Events"
    if exists (process "REAPER") then
        tell process "REAPER"
            set frontmost to true
            delay 0.4
            if (count of windows) > 0 then
                try
                    click button "Save" of window 1
                on error
                    try
                        click button "Save All" of window 1
                    on error
                        try
                            keystroke return
                        end try
                    end try
                end try
            end if
        end tell
    end if
end tell
''')

    for _ in range(15):
        time.sleep(1)
        if subprocess.run(["pgrep", "-x", "REAPER"],
                          capture_output=True).returncode != 0:
            log("  ✓ Reaper closed.")
            return True

    log("  ⚠ Reaper is still open — close it manually.")
    return False


def warn_keep_terminal_open():
    print()
    print("  ┌───────────────────────────────────────────────────┐")
    print("  │  ⚠  KEEP THIS TERMINAL WINDOW OPEN!               │")
    print("  │     Reaper will keep running if it closes, but    │")
    print("  │     the automation (timed record start/stop and   │")
    print("  │     screen layout) will STOP working.             │")
    print("  └───────────────────────────────────────────────────┘")
    print()


def run_service(service: dict):
    log(f"Service : {service['name']}")
    if service["open_time"]:
        log(f"Open    : {service['open_time'].strftime('%I:%M:%S %p')}")
    if service["record_start"] and service.get("board_stop"):
        log(f"Record  : {service['record_start'].strftime('%I:%M:%S %p')} → stopped by the board")
    elif service["record_start"]:
        log(f"Record  : {service['record_start'].strftime('%I:%M:%S %p')} → {service['record_stop'].strftime('%I:%M:%S %p')}")
    else:
        log("Record  : manual control")
    log("=" * 50)

    # Open Reaper (wait if a scheduled open time is set)
    if service["open_time"] and datetime.datetime.now().time() < service["open_time"]:
        wait_until(service["open_time"], "Reaper opens")

    # QRec has to be up before Reaper opens
    verify_qrec()

    launch_reaper(service["template"])

    # Save
    save_project(service["name"])

    # MarkerMatic connects to Reaper, so it has to come up after Reaper is open
    ensure_markermatic()

    warn_keep_terminal_open()

    # Timed recording, if times were provided
    if service["record_start"]:
        wait_until(service["record_start"], "Recording starts")
        time.sleep(2)
        markermatic_record()   # arm snapshot markers before Reaper rolls
        start_recording()
        warn_keep_terminal_open()

        if service.get("layout_time"):
            wait_until(service["layout_time"], "Screen layout")
            setup_screen_layout()

        if service.get("board_stop"):
            # The board fires stop_recording_safe.lua on the last snapshot,
            # which stops, saves the media and saves the project. This script
            # just watches for it, then closes out.
            wait_for_board_record_stop()
            close_stream_windows()
            save_and_quit_reaper()
        else:
            wait_until(service["record_stop"], "Recording stops")
            stop_recording()
            close_stream_windows()

    else:
        log("Reaper is ready — control recording manually.")
        log("  Remember to click Record in MarkerMatic too.")

    log("=" * 50)
    log(f"{service['name']} complete. Great work!")
    log("=" * 50)


def resize_terminal():
    applescript('''
tell application "Terminal"
    tell front window
        set number of rows to 14
        set number of columns to 65
    end tell
    set position of front window to {1370, 740}
end tell
''')


def main():
    now   = datetime.datetime.now()
    today = now.strftime("%A")

    resize_terminal()
    log("=" * 50)
    log("Church Media - Reaper Automation")
    if TEST_MODE:
        log("*** TEST MODE — waits skipped ***")
    log(f"Today is {today}, {now.strftime('%I:%M %p')}")

    # --day <Name> forces a scheduled service on any date (handy for testing),
    # e.g.  --day Sunday  to rehearse the Sunday run on a weekday.
    if "--day" in sys.argv:
        try:
            wanted = sys.argv[sys.argv.index("--day") + 1].capitalize()
        except IndexError:
            raise SystemExit("--day needs a day name, e.g. --day Sunday")
        service = SERVICES.get(wanted)
        if not service:
            raise SystemExit(
                f"No service defined for {wanted}. "
                f"Known: {', '.join(SERVICES)}"
            )
        log(f"Forcing the {wanted} schedule.")
        run_service(service)
        return

    # --special forces the special-show setup on any day (handy for testing)
    if "--special" in sys.argv:
        service = prompt_special_show()
        run_service(service)
        return

    # Saturday → always a special show
    if today == "Saturday":
        service = prompt_special_show()
        run_service(service)
        return

    # Sunday → morning service before noon, special show after noon
    if today == "Sunday":
        if now.time() < SUNDAY_MORNING_CUTOFF:
            service = SERVICES["Sunday"]
        else:
            log("Sunday afternoon detected — launching special show setup.")
            service = prompt_special_show()
        run_service(service)
        return

    # All other days — check the schedule
    service = SERVICES.get(today)
    if service:
        run_service(service)
    else:
        log(f"No service scheduled for {today}.")
        log("=" * 50)
    

if __name__ == "__main__":
    main()
