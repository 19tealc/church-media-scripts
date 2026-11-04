#!/bin/bash
# Church Media - Remove Wake Schedule
# Double-click to stop the Mac from waking itself for the
# ProPresenter restarts. Asks for the admin password once.

echo ""
echo "Removing the automatic wake schedule."
echo "Enter the admin password when asked (typing is invisible):"
sudo pmset repeat cancel && echo "" && echo "Wake schedule removed."
echo ""
read -n 1 -s -p "Press any key to close..."
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    osascript -e 'tell application "Terminal" to close (every window whose name contains "Remove Wake Schedule")' &
fi
exit
