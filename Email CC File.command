#!/bin/bash
# Church Media - CC File Email Launcher
# Point your Stream Deck button to this file.

cd "$(dirname "$0")"
python3 "./email_cc_file.py"
osascript -e 'tell application "Terminal" to close front window'
