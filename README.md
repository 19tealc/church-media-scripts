# Church Media Scripts

macOS automation for running a church service production desk — Reaper
multitrack recording, livestream monitoring, and caption-file delivery.

Built for First Baptist Church of Columbia, SC, but the pieces are generic
enough to adapt. Everything is plain Python 3 and AppleScript, no dependencies
beyond what ships with macOS.

## Scripts

### `reaper_automation.py`

Runs a service start to finish:

1. Waits for the scheduled open time
2. Verifies SoundGrid QRec is running before Reaper opens
3. Launches Reaper with the right project template
4. Saves the project with a dated filename (auto-increments to `Take 2` etc.)
5. Opens MarkerMatic and waits for it to connect to Reaper
6. Clicks MarkerMatic's record, then starts Reaper recording
7. Confirms recording is real by checking media files are actually growing
8. Opens stream-check windows alongside Reaper
9. Stops recording, saves recorded media, saves the project

Weekday services run on a fixed schedule. Saturdays and Sunday afternoons
prompt for a show name, a project template, and optional record times.

```bash
python3 reaper_automation.py              # normal run
python3 reaper_automation.py --test       # shorten every wait to 10s, prefix files with TEST
python3 reaper_automation.py --special    # force the special-show prompts on any day
```

### `email_cc_file.py`

Logs into EEG Cloud, downloads the service's SRT caption file, and prepares a
pre-addressed email in Mail.app with the file attached. Stops short of sending
so it can be reviewed first.

### `Live Stream Monitor.html`

A single page showing the YouTube and Facebook streams side by side, with
one-key audio switching between them. Served over `http://localhost` rather
than opened as a `file://` page — Safari refuses `localStorage` on `file://`
URLs, which would wipe the saved stream links every service.

### Other helpers

| File | Purpose |
| --- | --- |
| `Install Wake Schedule.command` | Schedule the Mac to wake before services |
| `Install Restart Schedule.command` | Schedule weekly restarts |
| `Restart ProPresenter.command` | Restart ProPresenter cleanly |
| `Speedtest.command` | Quick upload-speed check before going live |

The `.command` files are double-clickable and work well as Stream Deck targets.

## Setup

```bash
cp config.example.py config.py
```

Then edit `config.py` with your own email addresses. It's gitignored, so your
addresses stay out of the repo.

The EEG Cloud password is read from the macOS Keychain, never stored in a file:

```bash
security add-generic-password -a eegcloud -s eegcloud -w
```

Terminal needs Accessibility permission (System Settings → Privacy & Security →
Accessibility) since the scripts drive Reaper and Safari via AppleScript. You
only have to grant it once.

See `SETUP INSTRUCTIONS.txt` for the full walkthrough.

## Notes

App paths at the top of `reaper_automation.py` assume a standard install of
Reaper, SoundGrid QRec, and MarkerMatic. Adjust them if yours differ.
