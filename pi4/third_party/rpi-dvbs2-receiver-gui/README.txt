Preliminary DVB-S2 Receiver GUI for Raspberry Pi 4

Files:

main4.c
    GTK4 receiver-only GUI source.

makefile
    Builds the GUI application named "app".

start_app.sh
    Starts the GUI application.

start_rx.sh
    Starts ffplay and the GNU Radio DVB-S2 receiver.
    SPS is selected automatically:
      125 kSym/s to 1 MSym/s: SPS 4
      1.5 MSym/s and 2 MSym/s: SPS 2

stop_rx.sh
    Stops the receiver and ffplay processes.

RF_UDP_dvbs2_rx.py
    Modified GNU Radio DVB-S2 receiver flowgraph.
    The recovered transport stream is sent by UDP to:
      127.0.0.1 port 2000

Build:

    make

Run:

    ./start_app.sh

Tested hardware:

    Raspberry Pi 4
    Official Raspberry Pi 7-inch display
    PlutoSDR-compatible receiver
    Mouse
    Headphones

Tested symbol rates:

    333 kSym/s
    1 MSym/s
    1.5 MSym/s
    2 MSym/s

Available MODCODs:

    QPSK 1/4
    QPSK 1/2
    QPSK 3/4
    8PSK 3/5

This is a preliminary version.

Credits:

    方式考案・原システム設計・統合：山崎慎慈氏
    受信安定化調査・再捕捉修正・運用スクリプト実装：真城和一

2026-07-13
