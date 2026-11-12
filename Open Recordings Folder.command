#!/bin/bash
# Church Media - Open the Reaper recordings folder in Finder
# Point a Stream Deck "Open" action at this file.
# Each service is in its own dated folder inside REAPER Media.

open "$HOME/Documents/REAPER Media"
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 &
exit 0
