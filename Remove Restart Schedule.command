#!/bin/bash
# Church Media - Remove ProPresenter Restart Schedule
# Double-click to stop the automatic twice-a-week restarts.
# (The restart button itself keeps working — this only removes the schedule.)

LABEL="com.churchmedia.restart-propresenter"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$PLIST"

echo ""
echo "Schedule removed. ProPresenter will no longer restart automatically."
echo ""
read -n 1 -s -p "Press any key to close..."
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    osascript -e 'tell application "Terminal" to close (every window whose name contains "Remove Restart Schedule")' &
fi
exit
