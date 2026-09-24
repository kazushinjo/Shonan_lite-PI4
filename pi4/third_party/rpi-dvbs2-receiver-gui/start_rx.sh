#!/bin/bash
set -u
echo "[RX] Cleaning previous processes..."
pkill -f RF_UDP_dvbs2_rx.py 2>/dev/null
pkill -f ffplay 2>/dev/null
pkill -f ffmpeg 2>/dev/null

sleep 1

RX_HZ="$1"
MODE="$2"
SR="$3"

# シンボルレートに応じて SPS を自動選択
# 333k / 1M   : SPS=4
# 1.5M / 2M   : SPS=2

if [ "$SR" -ge 1500000 ]; then
    SPS=2
else
    SPS=4
fi

echo "[RX] Start: freq=$RX_HZ mode=$MODE sr=$SR sps=$SPS"
rm -f /tmp/rx_stdout.log
rm -f /tmp/ffmpeg_rx.log
rm -f /tmp/ffplay_rx.log

# 窓1
mkdir -p /tmp/jpg
rm -f /tmp/in.ts
mkfifo /tmp/in.ts
ffmpeg -y -f lavfi -i color=size=800x480:rate=1:color=black \
    -frames:v 1 -update 1 /tmp/jpg/latest.jpg
ffplay -loglevel info udp://127.0.0.1:2000 \
    > /tmp/ffplay_rx.log 2>&1 &

FFPLAY_PID=$!
echo "$FFPLAY_PID" > /tmp/ffplay_rx.pid

# 窓3
(
    cd ~/dvb-s || exit 1
    ./RF_UDP_dvbs2_rx.py \
        -g "$RX_HZ" \
        -m "$MODE" \
        -s "$SR" \
        -o "$SPS"
) > /tmp/rx_stdout.log 2>&1 &

RX_PID=$!
echo "$RX_PID" > /tmp/rx_pid

new="0"
old="0"
count="0"

while true
do
    sleep 2
    new=$(wc -c < /tmp/rx_stdout.log 2>/dev/null || echo 0)
    if [ "$new" -gt "$old" ]; then
        echo "[RX] log growing"
        count=$((count + 1))
    else
        count=0
    fi

if [ "$count" -ge 2 ]; then
    echo "[RX] active RX detected"
    sleep 20

    # 待機中にSTOPされた場合は、ここで終了
    if ! kill -0 "$RX_PID" 2>/dev/null; then
        echo "[RX] RX was stopped during startup wait"
        exit 0
    fi

    echo "[RX] start ffmpeg"
    (
        cd ~/dvb-s || exit 1
        # 必要なffmpegコマンドをここに置く
        # ffmpeg ...
    ) > /tmp/ffmpeg_rx.log 2>&1 &

    FFMPEG_PID=$!
    echo "$FFMPEG_PID" > /tmp/ffmpeg_rx.pid
    break
fi
    old=$new
done

echo "[RX] Started."
echo "[RX] ffplay PID : $FFPLAY_PID"
echo "[RX] rx PID     : $RX_PID"
echo "[RX] ffmpeg PID : $FFMPEG_PID"
echo "[RX] Frequency  : $RX_HZ"
echo "[RX] Symbol rate: $SR"
echo "[RX] Mode       : $MODE"
echo "[RX] SPS        : $SPS"
