#!/bin/bash
# run_udp_hd_test.sh — one-shot launcher for the HD-over-UDP live test.
#
# Starts: camera -> H.264 -> dvbs2-tx (loopback via attenuator) -> PlutoSDR RX
# -> dvbs2-rx -> udp_relay.py (127.0.0.1:2000) -> optional ffmpeg capture for
# verification. All background processes are fully detached (setsid + disown +
# stdin /dev/null) so they survive after this script's own SSH session ends.
#
# Lessons baked in from the 2026-07-14 investigation (see
# docs/loopback_test_procedure.md section 9):
#   - Do NOT pass --log/--log-period together with --sink fd/--out-fd 1: the
#     periodic stats text gets interleaved into the same stdout stream that
#     carries binary TS data, corrupting UDP relay alignment. Use --sink file
#     instead when SNR/FER stats are needed, or read stats separately.
#   - dvbs2-rx and dvbs2-tx are periodically reinstalled to
#     /usr/local/bin/{dvbs2-rx,dvbs2-tx} from ~/gr-dvbs2rx/apps/ whenever
#     `sudo make install` runs there. Edit the source under ~/gr-dvbs2rx/apps/,
#     not the installed copy, or changes silently vanish on the next rebuild.
#
# Usage:
#   ./run_udp_hd_test.sh [freq] [modcod] [symrate] [sps] [rolloff] [capture_secs]
# Example (defaults shown):
#   ./run_udp_hd_test.sh 438022000 QPSK3/4 1000000 2 0.2 90

set -u

FREQ="${1:-438022000}"
MODCOD="${2:-QPSK3/4}"
SYMRATE="${3:-1000000}"
SPS="${4:-2}"
ROLLOFF="${5:-0.2}"
CAPTURE_SECS="${6:-90}"

cd "$(dirname "$0")" || exit 1

echo "[run_udp_hd_test] Cleaning up any leftover test processes..."
pkill -9 -f "dvbs2-rx --source plutosdr" 2>/dev/null
pkill -9 -f "dvbs2-tx --source fd" 2>/dev/null
pkill -9 -f "ffmpeg -f v4l2" 2>/dev/null
pkill -9 -f "python3 udp_relay.py" 2>/dev/null
pkill -9 -f "ffmpeg -y -i udp://127.0.0.1:2000" 2>/dev/null
sleep 1

PLUTO_ADDR=$(iio_info -s 2>/dev/null | grep -oE 'usb:[0-9]+\.[0-9]+\.[0-9]+' | head -1)
if [ -z "$PLUTO_ADDR" ]; then
    echo "[run_udp_hd_test] ERROR: PlutoSDR not found via iio_info -s" >&2
    exit 1
fi
echo "[run_udp_hd_test] Using PlutoSDR RX address: $PLUTO_ADDR"

if [ ! -e /dev/video0 ]; then
    echo "[run_udp_hd_test] ERROR: /dev/video0 not found (USB camera not connected?)" >&2
    exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
TX_LOG="/tmp/tx_${TS}.log"
RX_STDERR_LOG="/tmp/rx_stderr_${TS}.log"
RELAY_LOG="/tmp/udp_relay_${TS}.log"
CAPTURE_LOG="/tmp/udp_capture_${TS}.log"
CAPTURE_TS="/tmp/udp_received_${TS}.ts"

echo "[run_udp_hd_test] Starting TX (camera -> H.264 -> dvbs2-tx)..."
setsid nohup bash -c "ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i /dev/video0 \
  -c:v libx264 -preset ultrafast -tune zerolatency -b:v 1400k -pix_fmt yuv420p \
  -f mpegts - | \
  dvbs2-tx --source fd --sink plutosdr --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
  -f $FREQ -m $MODCOD -s $SYMRATE -o $SPS -r $ROLLOFF" > "$TX_LOG" 2>&1 < /dev/null &
disown
sleep 3

echo "[run_udp_hd_test] Starting RX (dvbs2-rx --sink fd | udp_relay.py, no --log)..."
setsid nohup bash -c "dvbs2-rx --source plutosdr --plutosdr-addr $PLUTO_ADDR --plutosdr-gain-mode slow_attack \
  -f $FREQ -m $MODCOD -s $SYMRATE -o $SPS -r $ROLLOFF \
  --sink fd --out-fd 1 2>$RX_STDERR_LOG | \
  python3 udp_relay.py 2>$RELAY_LOG > /dev/null" < /dev/null &
disown
sleep 2

if [ "$CAPTURE_SECS" -gt 0 ]; then
    echo "[run_udp_hd_test] Starting ${CAPTURE_SECS}s UDP capture for verification -> $CAPTURE_TS"
    setsid nohup timeout $((CAPTURE_SECS + 5)) ffmpeg -y -i udp://127.0.0.1:2000 -c copy -t "$CAPTURE_SECS" \
        "$CAPTURE_TS" > "$CAPTURE_LOG" 2>&1 < /dev/null &
    disown
fi

sleep 2
echo "[run_udp_hd_test] Running processes:"
pgrep -af "dvbs2-rx|dvbs2-tx|ffmpeg|udp_relay" 2>&1

cat <<EOF

[run_udp_hd_test] Started. Logs:
  TX log:        $TX_LOG
  RX stderr:     $RX_STDERR_LOG
  UDP relay log: $RELAY_LOG
  Capture log:   $CAPTURE_LOG
  Capture file:  $CAPTURE_TS

Check stall status any time with:  ./check_stall.sh
Stop everything with:              ./stop_test.sh
EOF
