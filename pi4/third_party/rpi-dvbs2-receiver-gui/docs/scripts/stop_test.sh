#!/bin/bash
# stop_test.sh — stop all DVB-S2 loopback/UDP test processes and clean up
# their temp logs/captures from /tmp (tmpfs; prior sessions have hit
# disk-exhaustion stalls from stale debug logs, see procedure.md 9.3).

set -u

echo "Stopping test processes..."
pkill -9 -f "dvbs2-rx --source plutosdr" 2>/dev/null
pkill -9 -f "dvbs2-tx --source fd" 2>/dev/null
pkill -9 -f "ffmpeg -f v4l2" 2>/dev/null
pkill -9 -f "python3 udp_relay.py" 2>/dev/null
pkill -9 -f "ffmpeg -y -i udp://127.0.0.1:2000" 2>/dev/null
pkill -9 -f "watchdog_rx.sh" 2>/dev/null
sleep 1

echo "Remaining matching processes (should be empty):"
pgrep -af "dvbs2-rx|dvbs2-tx|ffmpeg|udp_relay|watchdog_rx" 2>&1

echo "Cleaning up /tmp test artifacts..."
rm -f /tmp/tx_*.log /tmp/rx_stderr_*.log /tmp/udp_relay_*.log /tmp/udp_capture_*.log \
      /tmp/udp_received_*.ts /tmp/rx_*.ts /tmp/watchdog_*.log

df -h /tmp
