#!/usr/bin/env python3
"""Simple VRML models (boxes/cylinders) for parts that have no KiCad 3D model.

Coordinates are given in mm in the footprint frame (x right, y down as in KiCad, z up from the
board top surface) and converted to VRML units (1 unit = 2.54 mm, VRML y = -KiCad y).
Run: python3 make_models.py  (writes the .wrl files next to this script)
"""
import os

U = 2.54
WHITE = (0.85, 0.85, 0.85)
ALU = (0.80, 0.80, 0.82)
BLACK = (0.08, 0.08, 0.08)
BLUE = (0.05, 0.25, 0.75)
GREEN = (0.10, 0.45, 0.20)
METAL = (0.75, 0.75, 0.70)


def box(x0, y0, z0, x1, y1, z1, c):
    cx, cy, cz = (x0 + x1) / 2 / U, -(y0 + y1) / 2 / U, (z0 + z1) / 2 / U
    sx, sy, sz = abs(x1 - x0) / U, abs(y1 - y0) / U, abs(z1 - z0) / U
    return (f"Transform {{ translation {cx:.4f} {cy:.4f} {cz:.4f} children Shape {{ "
            f"appearance Appearance {{ material Material {{ diffuseColor {c[0]} {c[1]} {c[2]} }} }} "
            f"geometry Box {{ size {sx:.4f} {sy:.4f} {sz:.4f} }} }} }}\n")


def cyl(x, y, z0, z1, d, c):
    # VRML cylinders run along y; rotate to z
    return (f"Transform {{ translation {x / U:.4f} {-y / U:.4f} {(z0 + z1) / 2 / U:.4f} rotation 1 0 0 1.5708 "
            f"children Shape {{ appearance Appearance {{ material Material {{ diffuseColor {c[0]} {c[1]} {c[2]} }} }} "
            f"geometry Cylinder {{ radius {d / 2 / U:.4f} height {abs(z1 - z0) / U:.4f} }} }} }}\n")


def write(name, shapes):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), "w") as f:
        f.write("#VRML V2.0 utf8\n" + "".join(shapes))


# GEC 20PB020 (Akizuki 105054), 20x20 profile, 25 high. Origin = midpoint of the two pins,
# device mounting face at x=-3.5, fins toward +x. Pins dia 1.4, 12.5 pitch, 4.5 below the board.
hs = [box(-3.5, -10, 0, -1.0, 10, 25, ALU)]                      # base plate (device side)
for y0, y1 in ((-10, -8.8), (-3.7, -2.5), (2.5, 3.7), (8.8, 10)):  # fins
    hs.append(box(-1.0, y0, 0, 16.5, y1, 25, ALU))
for y in (-6.25, 6.25):
    hs.append(box(-1.0, y - 1.2, 0, 1.4, y + 1.2, 25, ALU))       # pin boss
    hs.append(cyl(0, y, -6.1, 0, 1.4, ALU))                       # pin (through 1.6 mm board)
write("Heatsink_GEC_20PB020.wrl", hs)

# W5500 Lite (USR-ES1). Origin = pin 1. PCB 23x25 (x -1.34..21.66, y -6.4..18.5) on 2.5 mm headers,
# RJ45 HR961160C (x 2.11..18.21, y -8.9..12.7), W5500 chip behind the RJ45.
w = [box(-1.34, -6.4, 2.5, 21.66, 18.5, 4.1, BLUE),
     box(2.11, -8.9, 4.1, 18.21, 12.7, 17.6, WHITE),
     box(6.66, -8.95, 6.0, 13.66, -8.9, 14.0, BLACK),              # RJ45 opening
     box(7.66, 13.8, 4.1, 12.66, 17.8, 5.0, BLACK)]
for i in range(6):
    for x in (0, 20.32):
        w.append(box(x - 1.27, i * 2.54 - 1.27, 0, x + 1.27, i * 2.54 + 1.27, 2.5, BLACK))
write("W5500_Lite_USR-ES1.wrl", w)

# Freenove ESP32 WROOM (FNK0090) in a 2x20 socket. Origin = pin 20 (left row, antenna end).
# Board about 27x58.5 (x -0.9..26.3, y -8.99..49.61), USB-C at the bottom (+y) end.
e = []
for x in (0, 25.4):
    e.append(box(x - 1.27, -1.27, 0, x + 1.27, 48.26 + 1.27, 8.5, BLACK))   # female sockets
e += [box(-0.9, -8.99, 8.5, 26.3, 49.61, 10.1, BLACK),
      box(3.7, -8.99, 10.1, 21.7, 16.5, 10.9, GREEN),                       # WROOM module PCB
      box(4.7, -1.5, 10.9, 20.7, 15.5, 13.2, WHITE),                        # shield can
      box(8.2, 42.3, 10.1, 17.2, 49.9, 13.3, WHITE),                        # USB-C
      box(1.2, 44.5, 10.1, 4.7, 48.0, 11.6, WHITE),                         # BOOT/EN buttons
      box(20.7, 44.5, 10.1, 24.2, 48.0, 11.6, WHITE)]
write("Freenove_ESP32_WROOM.wrl", e)
