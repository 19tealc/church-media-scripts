#!/bin/zsh
speedtest
echo ""
read -k 1 -s "?Press any key to close..."
osascript -e 'tell application "Terminal" to close (every window whose name contains "Speedtest")' &
exit
