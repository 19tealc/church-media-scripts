#!/usr/bin/env python3
"""
Church Media - Stop & Save Recording

Stops Reaper's recording, keeps every recorded file, saves the project, then
saves the project one more time for good measure.

It fires the same stop_recording_safe.lua the DiGiCo board uses, over OSC to
Reaper's "Console Record" control surface (port 9000). That means:
  - no "save / delete recorded media?" prompt to click through
  - Reaper doesn't need to be the front window
  - pressing it when Reaper isn't recording is harmless (it just saves)
"""

import os
import socket
import struct
import subprocess
import sys
import time

REAPER_OSC_HOST = "127.0.0.1"
REAPER_OSC_PORT = 9000

# Command ID of "Custom: stop_recording_safe.lua" in Reaper's Action List.
# If the script is ever re-added to Reaper, this ID changes: right-click it in
# Actions → Show Action List → "Copy selected action command ID" and paste here.
STOP_SCRIPT_ID = "_RS6aadf264525e4f617bcbd1fe80effb7cff741340"
SAVE_PROJECT   = 40026   # File: Save project

SAVE_FOLDER = os.path.expanduser("~/Documents/REAPER Media")


def osc_pad(b: bytes) -> bytes:
    b += b"\x00"
    return b + b"\x00" * (-len(b) % 4)


def osc_message(address: str, value) -> bytes:
    if isinstance(value, int):
        return osc_pad(address.encode()) + osc_pad(b",i") + struct.pack(">i", value)
    return osc_pad(address.encode()) + osc_pad(b",s") + osc_pad(str(value).encode())


def send(address: str, value):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(osc_message(address, value), (REAPER_OSC_HOST, REAPER_OSC_PORT))


def reaper_running() -> bool:
    return subprocess.run(["pgrep", "-x", "REAPER"], capture_output=True).returncode == 0


def newest_project():
    newest, newest_t = None, 0
    for root, _dirs, files in os.walk(SAVE_FOLDER):
        for f in files:
            if f.upper().endswith(".RPP"):
                p = os.path.join(root, f)
                t = os.path.getmtime(p)
                if t > newest_t:
                    newest, newest_t = p, t
    return newest, newest_t


def main():
    print("=" * 50)
    print("  STOP & SAVE RECORDING")
    print("=" * 50)

    if not reaper_running():
        print("  Reaper isn't open — nothing to stop.")
        return 1

    started = time.time()

    print("  Stopping recording and saving all recorded media...")
    send("/action/str", STOP_SCRIPT_ID)
    time.sleep(4)   # give Reaper time to finalise the files and save

    print("  Saving the project one more time...")
    send("/action", SAVE_PROJECT)
    time.sleep(2)

    path, saved_at = newest_project()
    if path and saved_at >= started:
        rel = os.path.relpath(path, SAVE_FOLDER)
        print(f"  ✓ Saved: {rel}  ({time.strftime('%I:%M:%S %p', time.localtime(saved_at))})")
        return 0

    print("  ⚠ Couldn't confirm the project saved.")
    print("    Check Reaper — if it's still recording, press Stop and choose Save All,")
    print("    then Cmd+S. (Is the 'Console Record' OSC device still set up?)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
