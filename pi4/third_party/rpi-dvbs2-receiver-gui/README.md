# Raspberry Pi DVB-S2 Receiver GUI

A simple DVB-S2 receiver application for Raspberry Pi 4.

This project provides a GTK4 graphical user interface for starting and
stopping a GNU Radio DVB-S2 software receiver.

The system has been tested with Raspberry Pi 4 and PlutoSDR / Pluto+.

## Current status

This is a preliminary release for community testing.

The receiver works on the author's system, but testing on different
hardware and software environments is required.

Feedback, test reports and bug reports are welcome.

## Main features

- Simple GTK4 receiver GUI
- Raspberry Pi 4 support
- GNU Radio based DVB-S2 reception
- PlutoSDR / Pluto+ support
- Symbol rates:
  - 333 kSym/s
  - 1 MSym/s
  - 1.5 MSym/s
  - 2 MSym/s
- MODCOD support:
  - QPSK 1/4
  - QPSK 1/2
  - QPSK 3/4
  - 8PSK 3/5
- Roll-off:
  - 0.20
  - 0.25
  - 0.35

## Required hardware

- Raspberry Pi 4
- PlutoSDR or compatible Pluto+
- Display, mouse and keyboard
- Suitable DVB-S2 test signal

## Required software

- Raspberry Pi OS 64-bit
- GNU Radio
- gr-dvbs2rx
- GTK4
- FFmpeg / ffplay
- Python 3

## Files

- `main4.c`  
  GTK4 receiver GUI source code

- `RF_UDP_dvbs2_rx.py`  
  GNU Radio DVB-S2 receiver

- `start_app.sh`  
  Starts the GUI application

- `start_rx.sh`  
  Starts the receiver

- `stop_rx.sh`  
  Stops the receiver

- `makefile`  
  Builds the GTK4 GUI

## Credits

- 方式考案・原システム設計・統合：山崎慎慈氏
- 受信安定化調査・再捕捉修正・運用スクリプト実装：真城和一

## Build

```bash
make
