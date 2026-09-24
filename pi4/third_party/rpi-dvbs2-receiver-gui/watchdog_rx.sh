#!/bin/bash
# watchdog_rx.sh — auto-restarting dvbs2-rx receiver with UDP relay.
#
# Monitors output throughput via udp_relay.py's byte counter. If no new
# bytes are sent for STALL_TIMEOUT seconds (plsync_cc stuck re-acquiring
# lock after a live-source glitch, never recovering), kills and restarts
# the whole dvbs2-rx | udp_relay.py pipeline.
#
# Usage: ./watchdog_rx.sh <freq> <modcod> <symrate> <sps> [rolloff]

set -u

FREQ="${1:?freq required}"
MODCOD="${2:?modcod required}"
SYMRATE="${3:?symrate required}"
SPS="${4:?sps required}"
ROLLOFF="${5:-0.2}"

STALL_TIMEOUT=8
CHECK_INTERVAL=2

RELAY_LOG=/tmp/watchdog_relay.log
STDERR_LOG=/tmp/watchdog_dvbs2rx_stderr.log

cd "$(dirname "$0")" || exit 1

cleanup() {
    echo "[watchdog] $(date '+%T') Stopping..."
    pkill -9 -f "dvbs2-rx --source plutosdr" 2>/dev/null
    pkill -9 -f "python3 udp_relay.py" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

while true; do
    PLUTO_ADDR=$(iio_info -s 2>/dev/null | grep -oE 'usb:[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [ -z "$PLUTO_ADDR" ]; then
        echo "[watchdog] $(date '+%T') PlutoSDR not found, retrying in 3s..."
        sleep 3
        continue
    fi

    echo "[watchdog] $(date '+%T') Starting dvbs2-rx ($PLUTO_ADDR, $MODCOD, ${SYMRATE}sym/s, sps=$SPS)..."
    rm -f "$RELAY_LOG"

    dvbs2-rx --source plutosdr --plutosdr-addr "$PLUTO_ADDR" --plutosdr-gain-mode slow_attack \
        -f "$FREQ" -m "$MODCOD" -s "$SYMRATE" -o "$SPS" -r "$ROLLOFF" \
        --sink fd --out-fd 1 2>"$STDERR_LOG" | \
        python3 udp_relay.py 2>"$RELAY_LOG" &
    PIPE_PID=$!

    LAST_TOTAL=0
    STALL_ELAPSED=0

    while kill -0 "$PIPE_PID" 2>/dev/null; do
        sleep "$CHECK_INTERVAL"
        CUR_TOTAL=$(grep -o 'total=[0-9]*' "$RELAY_LOG" 2>/dev/null | tail -1 | cut -d= -f2)
        CUR_TOTAL=${CUR_TOTAL:-0}

        if [ "$CUR_TOTAL" -gt "$LAST_TOTAL" ]; then
            LAST_TOTAL=$CUR_TOTAL
            STALL_ELAPSED=0
        else
            STALL_ELAPSED=$((STALL_ELAPSED + CHECK_INTERVAL))
            if [ "$STALL_ELAPSED" -ge "$STALL_TIMEOUT" ]; then
                echo "[watchdog] $(date '+%T') Stalled ${STALL_ELAPSED}s at total=$CUR_TOTAL bytes, restarting..."
                break
            fi
        fi
    done

    pkill -9 -f "dvbs2-rx --source plutosdr" 2>/dev/null
    pkill -9 -f "python3 udp_relay.py" 2>/dev/null
    sleep 1
done
