#!/usr/bin/env python3
"""Relay stdin MPEG-TS bytes to a UDP destination in TS-packet-aligned datagrams.

Unlike `nc -u`, this uses sendto() on an unconnected socket, so it is
immune to ICMP port-unreachable causing a silent early exit if the
destination briefly has no listener.

Continuously re-validates TS packet sync (0x47 every 188 bytes) rather
than trusting a one-time initial resync, since the live DVB-S2 decode
can introduce occasional byte-level discontinuities mid-stream (e.g.
around imperfectly decoded frames). Any single corrupted/missing byte
would otherwise permanently misalign every following datagram.
"""
import socket
import sys

DEST = ("127.0.0.1", 2000)
TS_PACKET = 188
PACKETS_PER_DATAGRAM = 7
CHUNK = TS_PACKET * PACKETS_PER_DATAGRAM  # 1316 bytes
SYNC = 0x47

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
stdin = sys.stdin.buffer

buf = bytearray()
total_sent = 0
resyncs = 0


def fill(min_len):
    """Read from stdin until buf has at least min_len bytes. Returns False on EOF."""
    while len(buf) < min_len:
        chunk = stdin.read(max(4096, min_len - len(buf)))
        if not chunk:
            return False
        buf.extend(chunk)
    return True


def resync():
    """Scan forward in buf (refilling as needed) until buf[0] starts a
    verified TS packet (sync bytes at 0, 188, 376)."""
    global resyncs
    resyncs += 1
    while True:
        if not fill(2 * TS_PACKET + 1):
            return False
        if buf[0] == SYNC and buf[TS_PACKET] == SYNC and buf[2 * TS_PACKET] == SYNC:
            return True
        # Slide forward by one byte and retry.
        del buf[0:1]


if not resync():
    print("EOF during initial resync", file=sys.stderr, flush=True)
    sys.exit(0)

print("resynced to TS packet boundary", file=sys.stderr, flush=True)

packets = []
while True:
    if not fill(TS_PACKET):
        print(f"EOF, total sent={total_sent}, resyncs={resyncs}", file=sys.stderr, flush=True)
        break

    if buf[0] != SYNC:
        if not resync():
            print(f"EOF during resync, total sent={total_sent}", file=sys.stderr, flush=True)
            break
        packets = []
        continue

    packet = bytes(buf[0:TS_PACKET])
    del buf[0:TS_PACKET]
    packets.append(packet)

    if len(packets) == PACKETS_PER_DATAGRAM:
        datagram = b"".join(packets)
        sock.sendto(datagram, DEST)
        total_sent += len(datagram)
        print(f"sent {len(datagram)} bytes, total={total_sent}, resyncs={resyncs}",
              file=sys.stderr, flush=True)
        packets = []
