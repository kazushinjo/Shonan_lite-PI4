#!/usr/bin/env bash
# shonan_rx.py(GNU Radio RXフローグラフ)をバックグラウンド起動し、復調後のTSを
# ffplayでPi4直結のLCDへ表示する。Pi4はデスクトップ環境なし(tty)のため、ffplayは
# SDL2のKMS/DRMバックエンドで /dev/dri 経由で直接描画する(X/Wayland不要、確認済み)。
#
# file_sink(Python側)はFIFOをwriteでopenする際、読み手が先にいないとブロックする
# ため、必ずshonan_rx.pyを先にバックグラウンド起動してからffplayを起動する順序を守る。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIFO="${SHONAN_RX_FIFO:-/tmp/shonan_rx.ts}"

rm -f "$FIFO"
mkfifo "$FIFO"

cleanup() {
  echo "[run_rx_display] 停止中..." >&2
  [ -n "${RX_PID:-}" ] && kill "$RX_PID" 2>/dev/null || true
  wait "${RX_PID:-}" 2>/dev/null || true
  rm -f "$FIFO"
}
trap cleanup EXIT INT TERM

python3 "$HERE/rx/shonan_rx.py" --output-fifo "$FIFO" "$@" &
RX_PID=$!

# file_sinkがFIFOをopenするまで少し待つ(readerが先に必要なため、ffplay起動を
# 少し遅らせて確実にwriter側のopen(2)が先に完了するようにする)。
sleep 1

ffplay -fflags nobuffer -f mpegts "$FIFO"
