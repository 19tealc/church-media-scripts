#!/bin/bash
# Church Media - Reaper Automation REHEARSAL launcher
# Runs the Saturday / Sunday-afternoon special-show prompts in test mode, on any day.
# Point a Stream Deck "Open" action at this file.
#
# Test mode: every wait is cut to ~10s and files are saved with a "TEST" prefix,
# so real service recordings are never touched. Reaper DOES really record.

cd "$(dirname "$0")"
python3 "./reaper_automation.py" --test --special

echo
echo "── Rehearsal finished. Review the log above, then press Return to close. ──"
read -r
osascript -e 'tell application "Terminal" to close front window'
