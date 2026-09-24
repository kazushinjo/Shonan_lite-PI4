#!/bin/bash
# check_stall.sh — diagnose whether a running dvbs2-rx is genuinely stalled.
#
# Samples each GNU Radio block thread's CPU time (utime+stime from
# /proc/<pid>/task/*/stat) twice, 3 seconds apart, and reports which threads
# are active. If plsync_cc is consuming ~100% of a core while every
# downstream block (xfecframe_demapper, ldpc_decoder, bch_decoder, etc.)
# shows zero growth, that is the known "stuck re-searching for lock forever"
# failure mode (see docs/loopback_test_procedure.md section 9.9) rather than
# a crash or a hang — the process is alive and busy, just never re-locking.
#
# Usage: ./check_stall.sh [pid]
#   If pid is omitted, auto-detects the running dvbs2-rx process.

set -u

PID="${1:-}"
if [ -z "$PID" ]; then
    # Match the actual python3 process, not the "bash -c '...dvbs2-rx...'"
    # wrapper shell that run_udp_hd_test.sh launches it through (pgrep -f
    # matches the whole command line, so the wrapper's argv text matches too).
    PID=$(pgrep -f "python3 /usr/local/bin/dvbs2-rx --source plutosdr" | head -1)
fi
if [ -z "$PID" ] || [ ! -d "/proc/$PID" ]; then
    echo "No running dvbs2-rx process found (pass a PID explicitly, or check pgrep -af dvbs2-rx)." >&2
    exit 1
fi

echo "Sampling thread CPU for dvbs2-rx PID $PID over 3s..."

declare -A before
for tid_dir in /proc/$PID/task/*; do
    tid=$(basename "$tid_dir")
    comm=$(cat "$tid_dir/comm" 2>/dev/null)
    ticks=$(awk '{print $14+$15}' "$tid_dir/stat" 2>/dev/null)
    before["$tid"]="$comm $ticks"
done

sleep 3

echo
printf "%-8s %-20s %8s\n" "TID" "NAME" "CPU_TICKS/3s"
echo "--------------------------------------------------"
worst_name=""
worst_delta=0
for tid_dir in /proc/$PID/task/*; do
    tid=$(basename "$tid_dir")
    comm=$(cat "$tid_dir/comm" 2>/dev/null)
    after_ticks=$(awk '{print $14+$15}' "$tid_dir/stat" 2>/dev/null)
    before_entry="${before[$tid]:-"$comm 0"}"
    before_ticks=$(echo "$before_entry" | awk '{print $NF}')
    delta=$((after_ticks - before_ticks))
    printf "%-8s %-20s %8d\n" "$tid" "$comm" "$delta"
    if [ "$delta" -gt "$worst_delta" ]; then
        worst_delta=$delta
        worst_name=$comm
    fi
done

echo
# 100 ticks == 1 full core-second on a standard 100Hz clock tick config.
# Thread name suffix (e.g. plsync_cc10) varies run-to-run; match by prefix.
if [[ "$worst_name" == plsync_cc* ]] && [ "$worst_delta" -ge 250 ]; then
    echo "=> plsync_cc is consuming ~100% CPU with no downstream activity: LIKELY STUCK RE-SEARCHING (stall)."
    echo "   Consider restarting the pipeline (./stop_test.sh && ./run_udp_hd_test.sh ...) or rely on watchdog_rx.sh."
else
    echo "=> No single-block CPU-pegging pattern detected. Likely healthy or normally idle-waiting."
fi
