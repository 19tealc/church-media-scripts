#!/bin/bash
# Church Media - Restart ProPresenter
# Double-click or point a Stream Deck button to this file.
# Gracefully quits ProPresenter, waits for it to fully exit, then reopens it.

APP_NAME="ProPresenter"

if pgrep -xq "$APP_NAME"; then
    echo "Quitting $APP_NAME..."
    # Send quit without waiting, since ProPresenter may put up an
    # "Are you sure you want to close?" confirmation dialog
    osascript -e "ignoring application responses" \
              -e "tell application \"$APP_NAME\" to quit" \
              -e "end ignoring"

    # Wait up to 30 seconds for a clean exit, auto-clicking the
    # confirmation dialog if it appears (needs Accessibility access)
    for i in $(seq 1 30); do
        pgrep -xq "$APP_NAME" || break
        osascript 2>/dev/null <<EOF
tell application "System Events"
    if exists process "$APP_NAME" then
        tell process "$APP_NAME"
            repeat with btnName in {"OK", "Quit", "Close", "Yes"}
                if exists (button (btnName as text) of window 1) then
                    click button (btnName as text) of window 1
                    exit repeat
                end if
            end repeat
        end tell
    end if
end tell
EOF
        sleep 1
    done

    # If it's still stuck after 30s, force it closed
    if pgrep -xq "$APP_NAME"; then
        echo "$APP_NAME didn't quit cleanly — forcing it closed."
        pkill -x "$APP_NAME"
        sleep 3
    fi
else
    echo "$APP_NAME wasn't running."
fi

echo "Opening $APP_NAME..."
open -a "$APP_NAME"

# Only close the Terminal window when run by double-click / Stream Deck
# (skipped when run on a schedule, where no window exists)
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    osascript -e 'tell application "Terminal" to close (every window whose name contains "Restart ProPresenter")' &
fi
exit
