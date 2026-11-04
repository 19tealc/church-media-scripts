#!/usr/bin/env python3
"""
Church Media - CC File Email Automation
Logs into EEG Cloud, downloads the SRT caption file, and prepares it in Mail.app
"""

import subprocess
import time
import datetime
import os
import glob
import random

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

EEG_LOGIN_URL = "https://www.eegcloud.tv/login#"

# Addresses live in config.py, which is gitignored.
# Copy config.example.py to config.py and fill in your own.
try:
    from config import EMAIL, RECIPIENTS
except ImportError:
    raise SystemExit(
        "Missing config.py — copy config.example.py to config.py "
        "and fill in your email addresses."
    )

MESSAGES = [
    "Hope you have a great week!",
    "Great service today, everyone!",
    "Attached is the CC file from today's service. Have a wonderful day!",
]

DOWNLOADS        = os.path.expanduser("~/Downloads")
DOWNLOAD_TIMEOUT = 5 * 60   # seconds before giving up on the download

# ──────────────────────────────────────────────────────────────────────────────


def get_password() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "eegcloud", "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("EEG Cloud password not found in Keychain. Run setup again.")
    return result.stdout.strip()


def log(msg):
    ts = datetime.datetime.now().strftime("%I:%M:%S %p")
    print(f"[{ts}] {msg}", flush=True)


def run_applescript(script: str):
    result = subprocess.run(
        ["osascript"],
        input=script, text=True, capture_output=True
    )
    if result.returncode != 0:
        log(f"  Warning: {result.stderr.strip()}")
    return result


def safari_js(js: str):
    """Run JavaScript in the frontmost Safari document."""
    safe = js.replace("\\", "\\\\").replace('"', '\\"')
    run_applescript(f'tell application "Safari" to do JavaScript "{safe}" in document 1')


def cleanup_old_srt():
    old = glob.glob(os.path.join(DOWNLOADS, "asr_live*.srt"))
    for f in old:
        os.remove(f)
        log(f"  Removed old SRT: {os.path.basename(f)}")


def wait_for_srt():
    log(f"Waiting for SRT download (up to {DOWNLOAD_TIMEOUT // 60} minutes)...")
    deadline = time.time() + DOWNLOAD_TIMEOUT
    while time.time() < deadline:
        matches = glob.glob(os.path.join(DOWNLOADS, "asr_live*.srt"))
        # Ignore partial downloads
        matches = [f for f in matches if not f.endswith(".crdownload")]
        if matches:
            latest = max(matches, key=os.path.getmtime)
            log(f"  Downloaded: {os.path.basename(latest)}")
            return latest
        time.sleep(2)
    return None


def open_eeg_cloud():
    log("Opening EEG Cloud in Safari...")
    run_applescript(f'''
tell application "Safari"
    activate
    open location "{EEG_LOGIN_URL}"
    set bounds of window 1 to {{0, 0, 1000, 800}}
end tell
''')
    time.sleep(6)


def login(email: str, password: str):
    log("Logging in...")
    # Email field + submit
    safari_js(f"document.getElementsByName('username')[0].value = '{email}';")
    safari_js("document.querySelector('button[type=\"submit\"]').click();")
    time.sleep(1)
    # Password field + submit
    safari_js(f"document.getElementsByName('password')[0].value = '{password}';")
    safari_js("document.querySelector('button[type=\"submit\"]').click();")
    time.sleep(1)
    log("  Logged in.")


def navigate_and_download():
    log("Navigating to LEXI Live...")
    safari_js("Array.from(document.querySelectorAll('h3')).find(el => el.textContent.trim() === 'LEXI Live').click();")
    time.sleep(3)

    log("  Opening job list...")
    safari_js('document.querySelector(\'a[href="/speech-recognition/live/monitor"]\').click();')
    time.sleep(3)

    log("  Opening top job...")
    safari_js('document.querySelector(\'a.btn-info[href*="/speech-recognition/live/monitor/"]\').click();')
    time.sleep(3)

    log("  Selecting SRT format...")
    safari_js("""
var d = document.getElementById('download-captions-select');
if (d) { d.value = 'srt'; d.dispatchEvent(new Event('change')); }
""")
    time.sleep(3)

    log("  Clicking download...")
    safari_js("document.querySelector('button[id^=\"download-captions-button-\"]').click();")


def logout_safari():
    log("Logging out of EEG Cloud...")
    run_applescript('tell application "Safari" to set URL of document 1 to "https://www.eegcloud.tv/logout"')
    time.sleep(2)
    run_applescript('tell application "Safari" to close front window')


def compose_email(srt_path: str):
    date_str = datetime.datetime.now().strftime("%m/%d/%Y")
    subject  = f"CC File {date_str}"
    body     = random.choice(MESSAGES)

    cc_block = "\n        ".join([
        f'make new cc recipient with properties {{address:"{addr}"}}'
        for addr in RECIPIENTS["cc"]
    ])

    log(f"Composing email: '{subject}' → {RECIPIENTS['to']}")

    run_applescript(f'''
tell application "Mail"
    activate
    set msg to make new outgoing message with properties {{subject:"{subject}", content:"{body}" & return & return, visible:true}}
    tell msg
        make new to recipient with properties {{address:"{RECIPIENTS['to']}"}}
        {cc_block}
        make new attachment with properties {{file name:POSIX file "{srt_path}"}} at after the last paragraph
        -- send  ← uncomment this line to auto-send without review
    end tell
end tell
''')
    log("  Email ready — review and hit Send in Mail.")


def main():
    log("=" * 50)
    log("Church Media - CC File Automation")
    log("=" * 50)

    password = get_password()

    # Step 1: Clean up any leftover SRT files from a previous run
    cleanup_old_srt()

    # Step 2: Log in and navigate to the download
    open_eeg_cloud()
    login(EMAIL, password)
    navigate_and_download()

    # Step 3: Wait for the file to finish downloading
    srt_path = wait_for_srt()
    if not srt_path:
        log("ERROR: SRT file did not appear within 5 minutes.")
        log("Check that 'Allow JavaScript from Apple Events' is enabled in Safari → Develop menu.")
        input("Press Enter to close...")
        return

    # Step 4: Log out of EEG Cloud
    logout_safari()

    # Step 5: Open Mail and attach the file
    compose_email(srt_path)

    # Step 6: Clean up the local download after Mail has it
    time.sleep(5)
    if os.path.exists(srt_path):
        os.remove(srt_path)
        log(f"  Cleaned up local file.")

    log("=" * 50)
    log("Done! Review the email and click Send.")
    log("=" * 50)


if __name__ == "__main__":
    main()
