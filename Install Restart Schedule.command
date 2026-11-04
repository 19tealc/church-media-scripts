#!/bin/bash
# Church Media - Install ProPresenter Restart Schedule
#
# Edit the four lines below to pick your two days and times,
# then double-click this file. Running it again after changing
# the lines updates the schedule. Times are 24-hour (e.g. 06:00
# is 6 AM, 18:30 is 6:30 PM).
#
# IMPORTANT: keep this file in the same folder as
# "Restart ProPresenter.command" — it schedules that script.

DAY1="Sunday"
TIME1="06:00"
DAY2="Wednesday"
TIME2="06:00"

# ------------ no need to edit below this line ------------

LABEL="com.churchmedia.restart-propresenter"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$DIR/Restart ProPresenter.command"

day_num() {
    case "$1" in
        Sunday) echo 0 ;; Monday) echo 1 ;; Tuesday) echo 2 ;;
        Wednesday) echo 3 ;; Thursday) echo 4 ;; Friday) echo 5 ;;
        Saturday) echo 6 ;; *) echo "" ;;
    esac
}

fail() { echo ""; echo "ERROR: $1"; echo ""; read -n 1 -s -p "Press any key to close..."; exit 1; }

[ -f "$SCRIPT" ] || fail "Couldn't find 'Restart ProPresenter.command' in this folder:
  $DIR
Keep both files in the same folder and run this again."

WD1="$(day_num "$DAY1")"; WD2="$(day_num "$DAY2")"
[ -n "$WD1" ] || fail "DAY1 is '$DAY1' — use a full day name like Sunday or Wednesday."
[ -n "$WD2" ] || fail "DAY2 is '$DAY2' — use a full day name like Sunday or Wednesday."

parse_time() {  # sets H and M from HH:MM
    [[ "$1" == *:* ]] || fail "$2 is '$1' — use 24-hour HH:MM format, e.g. 06:00 or 18:30."
    H=$((10#${1%%:*})); M=$((10#${1##*:}))
    { [ "$H" -le 23 ] && [ "$M" -le 59 ]; } || fail "$2 is '$1' — hour must be 0-23 and minute 0-59."
}
parse_time "$TIME1" "TIME1"; H1=$H; M1=$M
parse_time "$TIME2" "TIME2"; H2=$H; M2=$M

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Weekday</key><integer>$WD1</integer>
            <key>Hour</key><integer>$H1</integer>
            <key>Minute</key><integer>$M1</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>$WD2</integer>
            <key>Hour</key><integer>$H2</integer>
            <key>Minute</key><integer>$M2</integer>
        </dict>
    </array>
</dict>
</plist>
EOF

# Remove any previous version of the schedule, then load the new one
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
launchctl bootstrap "gui/$(id -u)" "$PLIST" || launchctl load "$PLIST" 2>/dev/null

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    echo ""
    echo "=============================================="
    echo "  Schedule installed!"
    echo "  ProPresenter will restart every:"
    echo "    $DAY1 at $TIME1"
    echo "    $DAY2 at $TIME2"
    echo "=============================================="
    echo ""
    echo "To change days/times: edit the lines at the top"
    echo "of this file and double-click it again."
    echo "To stop the schedule: run 'Remove Restart Schedule.command'."
else
    fail "The schedule did not load. Try restarting the computer and running this again."
fi

echo ""
read -n 1 -s -p "Press any key to close..."
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    osascript -e 'tell application "Terminal" to close (every window whose name contains "Install Restart Schedule")' &
fi
exit
