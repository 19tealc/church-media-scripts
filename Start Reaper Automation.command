#!/bin/bash
# Church Media - Reaper Automation Launcher
# Point your Stream Deck button to this file.
# Terminal only needs Accessibility permission once — it never resets.

cd "$(dirname "$0")"
python3 "./reaper_automation.py"
osascript -e 'tell application "Terminal" to close front window'
