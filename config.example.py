"""
Local configuration template.

Copy this file to config.py and fill in your own values:

    cp config.example.py config.py

config.py is gitignored, so your addresses never reach the repo.
"""

# EEG Cloud account the CC file is downloaded from.
# The password lives in the macOS Keychain, not here. Add it once with:
#   security add-generic-password -a eegcloud -s eegcloud -w
EMAIL = "you@example.com"

# Who the finished caption file goes to each week.
RECIPIENTS = {
    "to": "producer@example.com",
    "cc": ["pastor@example.com", "tech@example.com"],
}
