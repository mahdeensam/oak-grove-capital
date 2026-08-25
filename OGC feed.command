#!/bin/bash
# Double-click this to keep the Cockpit tab fed. Close the window to stop.
cd "$(dirname "$0")" || exit 1
echo "Oak Grove cockpit feed - refreshing every 5 minutes, and answering the dashboard's Refresh button."
echo "Close this window to stop."
echo
exec python3 ogc-refresh.py --serve 8765 --loop 300
