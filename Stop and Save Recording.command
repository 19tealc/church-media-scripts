#!/bin/bash
# Church Media - Stop & Save Recording
# Point a Stream Deck "Open" action at this file.
# Stops Reaper recording, saves all recorded media, saves the project twice.

cd "$(dirname "$0")"
if python3 "./stop_and_save.py"; then
    sleep 3
    osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 &
else
    echo
    echo "── Press Return to close. ──"
    read -r
fi
