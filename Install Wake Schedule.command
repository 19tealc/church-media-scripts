#!/bin/bash
# Church Media - Install Wake Schedule
#
# Makes the Mac WAKE FROM SLEEP a few minutes before each scheduled
# ProPresenter restart, so the restarts happen even if the computer
# is asleep. (A Mac that is fully SHUT DOWN cannot wake itself.)
#
# There is nothing to edit here — it reads the days and times from
# "Install Restart Schedule.command" in this same folder. Set your
# days/times there first, then double-click this file.
#
# You will be asked for the computer's ADMIN PASSWORD — this is a
# system power setting, and macOS requires it. Type it and press
# Return (the cursor won't move while you type; that's normal).

WAKE_EARLY_MINUTES=3

DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="$DIR/Install Restart Schedule.command"

fail() { echo ""; echo "ERROR: $1"; echo ""; read -n 1 -s -p "Press any key to close..."; exit 1; }

[ -f "$CONF" ] || fail "Couldn't find 'Install Restart Schedule.command' in this folder:
  $DIR
Keep the files together and run this again."

get() { grep -m1 "^$1=" "$CONF" | cut -d'"' -f2; }
DAY1="$(get DAY1)"; TIME1="$(get TIME1)"
DAY2="$(get DAY2)"; TIME2="$(get TIME2)"

day_code() {
    case "$1" in
        Sunday) echo U ;; Monday) echo M ;; Tuesday) echo T ;;
        Wednesday) echo W ;; Thursday) echo R ;; Friday) echo F ;;
        Saturday) echo S ;; *) echo "" ;;
    esac
}
C1="$(day_code "$DAY1")"; C2="$(day_code "$DAY2")"
[ -n "$C1" ] && [ -n "$C2" ] || fail "Couldn't read the days from 'Install Restart Schedule.command'.
Check its DAY1/DAY2 lines use full day names (Sunday, Wednesday, ...)."

mins() { echo $(( 10#${1%%:*} * 60 + 10#${1##*:} )); }
M1="$(mins "$TIME1")"; M2="$(mins "$TIME2")"

# macOS supports one repeating wake time, so wake before the earlier
# of the two restart times on both days.
EARLIEST=$(( M1 < M2 ? M1 : M2 ))
WAKE=$(( EARLIEST - WAKE_EARLY_MINUTES ))
[ "$WAKE" -lt 0 ] && WAKE=0
WAKE_TIME="$(printf '%02d:%02d:00' $((WAKE / 60)) $((WAKE % 60)))"

echo ""
echo "Setting the Mac to wake at $WAKE_TIME on: $DAY1, $DAY2"
if [ "$M1" -ne "$M2" ]; then
    echo ""
    echo "NOTE: your two restart times are different ($TIME1 and $TIME2)."
    echo "macOS only supports ONE repeating wake time, so the Mac wakes"
    echo "at $WAKE_TIME on both days. On the day with the later restart,"
    echo "the Mac may fall back asleep first — that restart will then run"
    echo "the next time the computer wakes up."
fi
echo ""
echo "Enter the admin password when asked (typing is invisible):"
sudo pmset repeat wakeorpoweron "$C1$C2" "$WAKE_TIME" || fail "The wake schedule was not set (wrong password, or the account
is not an administrator)."

echo ""
echo "=============================================="
echo "  Wake schedule installed!"
echo "=============================================="
pmset -g sched
echo ""
echo "To remove it later: run 'Remove Wake Schedule.command'."
echo ""
read -n 1 -s -p "Press any key to close..."
if [[ "$TERM_PROGRAM" == "Apple_Terminal" ]]; then
    osascript -e 'tell application "Terminal" to close (every window whose name contains "Install Wake Schedule")' &
fi
exit
