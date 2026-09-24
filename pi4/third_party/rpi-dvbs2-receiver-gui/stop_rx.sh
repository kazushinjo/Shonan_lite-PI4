#!/bin/bash

pkill -f RF_UDP_dvbs2_rx.py 2>/dev/null
pkill -f ffmpeg 2>/dev/null
pkill -f ffplay 2>/dev/null

rm -f /tmp/ffplay_rx.pid
rm -f /tmp/rx_pid
rm -f /tmp/ffmpeg_rx.pid
