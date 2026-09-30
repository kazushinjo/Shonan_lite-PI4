---
title: ESP32+W5500 12 V Power/PTT Control Development Specification
---

# ESP32+W5500 12 V Power/PTT Control Development Specification

English translation of [`W5500_PA_PTT_Control_仕様書.md`](W5500_PA_PTT_Control_仕様書.md) (Japanese original).
If the two differ, the Japanese original takes precedence.

This document is the same-named document of Shonan_Lite-RasPI5 (same board, same firmware) with the integration parts replaced for Shonan_lite-PI4.

| Item | Details |
|---|---|
| Revision | Rev.2.6 |
| Created | 2026-08-07 (Rev.2.0 update: 2026-08-30, fully revised to match the actual circuit (KiCad) / Rev.2.1 update: 2026-08-30, power system corrected: J3 (external DC-DC buck converter) removed, and the +5 V from U2 (L7805) now feeds both MCU1 and U1 (TA48033S) as a single system / Rev.2.2 update: 2026-08-31, J1 corrected to the pinout of the actual Freenove 40-pin DevKitC socket and MCU1 unified with J1's pin numbers and signal names; indicator circuits added: a red LED (D1) on the Power (switched 12 V) line and a green LED (D2) on the +12 V (input side) line / Rev.2.3 update: 2026-09-30, R8 changed to 100 Ω (to match the KiCad schematic) and R9 added, IP address description unified to the fixed-IP method, the delay until the 12 V power turns ON corrected to the implemented value (5 seconds), and the "Use ESP32 W5500" setting and PTT output via Pi 4 GPIO21 on the Shonan_lite-PI4 side added / Rev.2.4 update: 2026-09-30, R8 changed to 1 kΩ (1/2 W recommended), R12 (10 kΩ) added to pull Q1's base down to GND, the KiCad symbol of Q5 corrected to the 2SJ334 pinout (1 = G, 2 = D, 3 = S), and heatsinks added to U1, U2 and Q5 / Rev.2.5 update: 2026-09-30, to leave 20 mm of wiring space (from the inner wall) behind the front and back round connectors, the heatsink column moved down (22 mm pitch) and the transistors, LEDs, J5 and J6 moved in front of that space / Rev.2.6 update: 2026-09-30, fixed GND symbols in the schematic whose value was empty (they formed a separate net), made the inner layers full GND and +12 V planes, laid the 12 V output as a 4 mm trace and autorouted the rest, and changed Q1 and Q3 to the TO-92 footprint with 2.54 mm lead pitch, made the Power indicator LED (D1) and the +12 V indicator LED (D2) external, connected through J7 and J8, changed J6, J7 and J8 to JST XH connectors (B2B-XH-A), changed the R8 footprint to one for a 1/2 W resistor, changed C2 to 33 µF as in the TA48033S datasheet and C1 and C3 to 0.33 µF, added a pull-down resistor R13 (10 kΩ) on Q3's base, connected J1's GND pins 21–24 and 40, and revised the Q5 heat estimate using the on-resistance at high temperature) |
| Target board | ESP32 (WROVER family, plain ESP32) + W5500 Ethernet module |
| Target sketch | `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino` |
| Connected apps | shonan-android (DATV transmit app), Shonan_lite-PI4 (pi4/gui; linked to TX start/stop on the transmit screen and to app start/exit) |
| Status | Written to and boot-confirmed on an actual ESP32 (ESP32-D0WD-V3) (2026-08-30). Field testing including the radio (integration test with the 12 V power/PTT drive circuits) not yet done |

---

## 1. Purpose and Scope

Control, via Ethernet, **PTT** in conjunction with the transmit button of shonan-android, and the **12 V power (for external equipment such as a PA)** in conjunction with starting/exiting the Shonan_lite-PI4 (pi4/gui) app.

Up to Rev.1.1, 3-channel LNA/PTT/PA sequence control was assumed (e.g. disconnecting the LNA before raising PTT/PA when transmitting), but the actual circuit (KiCad) has no LNA drive circuit and implements **only two functions: 12 V power ON/OFF (high-side switch with a 2SJ334) and PTT ON/OFF**. This document has been fully revised to match the actual circuit.

**In scope**
- 2-channel ON/OFF control of 12 V power / PTT with ESP32 + W5500
- PTT TX/RX switching by HTTP requests from shonan-android
- 12 V power ON/OFF linked to starting/exiting the Shonan_lite-PI4 (pi4/gui) app
- Browser UI for manual checking and debugging

**Out of scope**
- Implementing the transmit button and sending HTTP requests in the shonan-android app (must be handled separately on the app side)
- Circuit design of the PA, LNA, etc. that receive the 12 V power (depends on the user's radio configuration)

---

## 2. Hardware Configuration

### 2.1 Parts

| Part | Notes |
|---|---|
| ESP32 (WROVER module, etc.) | Plain ESP32. Not the same as native-USB chips such as the ESP32-C3 |
| W5500 Ethernet module | SPI connection. Has no built-in MAC address, so it is set arbitrarily in the sketch |
| Q5 (2SJ334) | P-channel power MOSFET. High-side switch for the 12 V power (replaces the former relay K3) |
| Q1 (2SC1815) | NPN transistor driving Q5's gate (switched by GPIO26) |
| R8 (1 kΩ, 1/2 W) | Pull-up resistor from Q5's gate to +12 V (keeps Q5 OFF while Q1 is OFF). About 12–14 mA flows while Q1 is ON, dissipating about 0.14–0.2 W, so a 1/2 W part is used (a 1/4 W part would run at about 80% of its rating, with no margin). The PCB footprint is for a 1/2 W resistor 3.2 mm in diameter and 9 mm long, mounted vertically (5.08 mm lead pitch) |
| R12 (10 kΩ) | Pull-down resistor from Q1's base to GND (keeps Q1 reliably OFF even while GPIO26 is undetermined, e.g. during ESP32 startup) |
| R13 (10 kΩ) | Pull-down resistor from Q3's base to GND (keeps Q3 OFF, so PTT does not turn ON by itself, even while GPIO27 is undetermined, e.g. during ESP32 startup or programming) |
| Q3 (2SC1815) | NPN transistor driving the PTT_ON signal (switched by GPIO27; pulls down to GND like an open collector) |
| R9 (10 kΩ) | Pull-up resistor from the W5500 (A1) RST (same net as GPIO21) to +3V3_A |
| J2 (DC_IN_13V8) | Input connector for the external power supply (13.8 V/12 V) |
| U2 (L7805) | +12 V → +5 V linear regulator (TO-220). The generated +5 V (`+5v0`) feeds both MCU1 (J1) and U1 |
| U1 (TA48033S) | +5 V (U2 output) → +3.3 V linear regulator (TO-220). Dedicated to the W5500 (A1) VCC (+3V3_A) |
| C3 (0.33 µF, 25 V or higher) | Input (+12 V) capacitor of U2 (L7805) |
| C1 (0.33 µF, 16 V or higher) | Capacitor on U2's output / U1's input (+5 V) (CIN = 0.33 µF recommended in the TA48033S datasheet) |
| C2 (33 µF, electrolytic, 10 V or higher) | Output (+3.3 V) capacitor of U1 (TA48033S). The TA48033S may oscillate with a small output capacitor, so 33 µF is used as in the datasheet's standard circuit (0.1 µF is not enough). The + side goes to +3.3 V |
| J1 (ESP32_DevKitC_Socket_40P) | Female socket into which a Freenove ESP32-WROOM-32E DevKitC (40 pins, 25.4 mm wide) plugs directly |
| J7 (LED_PWR) + R10 (10 kΩ) | Power indicator for the Power line (Q5 output, switched 12 V). The indicator LED (red) is not mounted on the board; it is external and connected through J7, a JST XH connector. J7 pin 1 = LED anode (current-limited by R10, 10 kΩ), pin 2 = cathode (GND) |
| J8 (LED_12V) + R11 (10 kΩ) | Power indicator for the +12 V line (J2 input, unswitched). The indicator LED (green) is not mounted on the board; it is external and connected through J8, a JST XH connector. J8 pin 1 = LED anode (current-limited by R11, 10 kΩ), pin 2 = cathode (GND) |

### 2.2 SPI Wiring (ESP32 ⇔ W5500)

| W5500 | ESP32 GPIO |
|---|---|
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| CS (SS) | GPIO 5 |
| RST | GPIO 21 (active-LOW. The ESP32 sends a pulse at startup for a hard reset) |
| VCC | 3.3 V |
| GND | GND |

### 2.3 Output Pin Assignment

| Channel | ESP32 GPIO | Logic | State at startup | Drive circuit | Output |
|---|---|---|---|---|---|
| POWER (12 V power) | GPIO 26 | active-HIGH | OFF | R6 → Q1 (2SC1815, base pulled down to GND by R12) → Q5 (2SJ334, PMOS high-side switch, gate pulled up to +12 V by R8) | J5 (Power) |
| PTT | GPIO 27 | active-HIGH | OFF | R7 → Q3 (2SC1815) | J6 (PTT_ON; pulls the radio's PTT terminal to GND) |

> GPIO25 was reserved for LNA control in the old specification (Rev.1.1), but the actual circuit has no drive circuit for it and it is unconnected. It is not handled by the current sketch or this document.
>
> Both POWER (GPIO26) and PTT are latched ON/OFF outputs; no automatic TX/RX switching sequence (such as a 100 ms wait) is performed. POWER and PTT are treated as completely independent channels.

### 2.4 Power System

Starting from the externally supplied +12 V (13.8 V), it is a single-system configuration in which **the +5 V (`+5v0`) generated by U2 (L7805) is branched to both MCU1 (DevKitC board) and U1 (TA48033S)**.

```
J2 (+12 V, 13.8 V)
   │
   U2 (L7805, 12 V → 5 V)
   │
   +5 V (`+5v0` net) ──┬── J1(1) → MCU1 (DevKitC board) *converted to 3.3 V by the on-board LDO for the ESP32 module
                        │
                        └── U1 (TA48033S, 5 V → 3.3 V) → A1 (VCC, W5500)
```

| Supplied to | Path | Notes |
|---|---|---|
| MCU1 (DevKitC) | +12 V → U2 (L7805, 12 V → 5 V) → J1(1) | The on-board LDO of the DevKitC converts this 5 V to 3.3 V for the ESP32 module |
| W5500 | +12 V → U2 (L7805, 12 V → 5 V) → U1 (TA48033S, 5 V → 3.3 V) → A1 (VCC) | U1 further steps the `+5v0` output of U2 down to 3.3 V for the W5500 (A1) VCC |

Both the MCU1 and W5500 supplies start from the +5 V output of U2 (L7805); no external DC-DC buck converter module is used (J3, which existed in the old Rev.2.0, has been removed). For detailed connections, see "Power System Connection Details" in [`MCU1_J1_W5500_connections_en.md`](MCU1_J1_W5500_connections_en.md).

### 2.5 Heatsinks

A heatsink is attached to each of U2 (L7805), U1 (TA48033S) and Q5 (2SJ334).

| Item | Details |
|---|---|
| Heatsink | Akizuki Denshi [105054] heatsink 20×20×25 mm (part number 20PB020-01025) |
| Dimensions | 20×20 mm, 25 mm high. With pins for PCB mounting. The M3 tapped hole for the part is 18 mm from the bottom and 10 mm from the side (center of the width), and the part's tab is fixed with an M3 screw. The tab hole of a TO-220 is about 13 mm above the bottom of the body (varies by part; check against the actual part), so each part is mounted with the bottom of its body about 5 mm above the board. On the PCB, the part-side face of each heatsink is aligned with the back of the tab, and the center of the heatsink (the hole position) is aligned with the part's middle lead |
| Thermal resistance | 15.8 °C/W |
| Placement on the PCB | The board outline is 72 mm wide × 115 mm tall (the previous hand-wired 95×72 mm board extended by 20 mm vertically). The W5500 module is at the top left (RJ45 toward the top edge), the ESP32 DevKitC (J1, USB toward the bottom edge) below it, and the three TO-220 parts (U1, U2, Q5) are stacked vertically on the right at 22 mm pitch with their tabs facing the right edge and the heatsinks (20×20 mm) on the right-edge side. The resistors are on the left edge and the transistors and LEDs at the bottom right. High-current external wiring uses solder-wire pads: J2 (+12 V input, for 1 mm² wire) is at the top right (front round connector side), and J5 (12 V output, for 1 mm² wire) is at the bottom right (back round connector side). The low-current J6 (PTT output), J7 (external Power indicator LED) and J8 (external +12 V indicator LED) are JST XH connectors (B2B-XH-A, 2-pin, 2.5 mm pitch, rated 3 A); J7 (left) and J6 (right) are placed side by side in the space between the W5500 module and the ESP32 socket, and J8 is on the left edge (below R11) (each area is drawn on the Dwgs.User layer of the KiCad PCB data; the dimensions of the W5500 module, etc. will be updated with data from the actual parts). The board is 4-layer: inner layer 1 is a full GND plane and inner layer 2 is a full +12 V (input side) plane, so GND and +12 V are connected through the inner layers without traces. The switched 12 V output (/Power, 5 A or more) runs from Q5's drain to J5 as a wide trace on both outer layers (4 mm, narrowing to 2 mm between Q5's leads). The J2, J5 and Q5 pads connect to the planes solidly (no thermal relief). All other signals are routed on the two outer layers with Freerouting (autorouter): 0.3 mm for signals and 0.8 mm for +5 V, +3.3 V and the /Power branch to the LED. Q1 and Q3 use the TO-92 footprint with 2.54 mm lead pitch (Inline_Wide). The heatsink mounting pin holes are not designed yet |
| Case and mounting holes | The case (OpenSCAD "LAN_PTT.scad") has inner dimensions of 80×120×35 mm. M3 inserts are embedded in the bosses on the bottom (8 mm OD, 5 mm high), and the board is fixed with M3 screws. The mounting holes on the board are φ3.2 mm for M3 at the same 66×109 mm pitch as the bosses (3 mm inside each board edge). No component leads within a 4 mm radius around the holes where the bosses touch. The front (board top edge side) has a rectangular opening for RJ45 and a φ16 round hole, and the back (board bottom edge side) has a rounded opening for USB and a φ16 round hole; the board is laid out so that the W5500's RJ45 and the DevKitC's USB line up with their openings. The front round connector (WTN-11-1253 8P) carries +12 V and GND, and the back round connector carries the 12 V output, GND and PTT. Because each round connector extends about 10 mm behind the panel, an area 20 mm deep from the inner wall (17.5 mm from the board's top and bottom edges) and 20 mm wide (board x = 46–66 mm from the left edge) is kept free of tall parts to leave room for wiring. The only item in that area is J2 (solder-wire pads) on the front side |

Rough heat estimate (at 14 V input):

- U2 (L7805): with a maximum output current of about 0.25 A (rough total of the ESP32 DevKitC and the W5500), the loss is
  (14 V − 5 V) × 0.25 A ≈ 2.3 W. With the heatsink's 15.8 °C/W plus junction-to-case (about 5 °C/W), the temperature rise is about 50 °C.
- U1 (TA48033S): (5 V − 3.3 V) × about 0.13 A (W5500) ≈ 0.2 W, which is small.
- Q5 (2SJ334): the loss is on-resistance (max 38 mΩ at VGS = −10 V) × current². Taking about 19 °C/W (heatsink 15.8 °C/W plus junction-to-case 2.78 °C/W),
  about 1 W at 5 A. The on-resistance rises to about 1.5 times at high temperature, so taking about 1.4 W, the rise is about 27 °C. Assuming the air inside the closed case is about 45 °C (30 °C room plus about 15 °C from the heat of L7805, etc.), the junction is about 70 °C (limit 150 °C) and the heatsink surface about 65–70 °C, which leaves margin.
  At 10 A the loss at high temperature is about 5.7 W with a rise of about 110 °C, which this heatsink cannot handle, so the guideline with this heatsink is up to about 7 A. Apply thermal grease between the tab and the heatsink. Check against the actual load current of the PA, etc.

---

## 3. Operation

Sequence control such as "LNA off → wait 100 ms → PTT/PA on" used up to Rev.1.1 has been abolished; POWER and PTT each follow independent ON/OFF events.

### 3.1 PTT (linked to the shonan-android transmit button)

- Transmit button ON: `GET /tx?state=on` → PTT (GPIO27) ON after the configured delay (`ptt_delay_ms`, default 50 ms)
- Transmit button OFF: `GET /tx?state=off` → PTT (GPIO27) OFF immediately (a pending ON delay is cancelled)
- The 12 V power is never touched.

### 3.2 12 V Power (linked to Shonan_lite-PI4 app start/exit)

- 5 seconds after app start: `GET /ch?idx=0&state=on` → POWER (GPIO26) ON after the configured delay (`power_delay_sec`, default 3 seconds)
- At app exit: first `GET /ch?idx=0&state=off` → POWER (GPIO26) OFF immediately (a pending ON delay is cancelled), then the app exits after waiting 3 seconds

### 3.3 Design Intent

- Since the actual hardware has no LNA drive circuit, the protective sequence accompanying TX/RX switching (such as disconnecting the LNA) was judged unnecessary and abolished.
- The 12 V power corresponds to the main power for external equipment such as a PA, so it is switched ON/OFF at coarse-grained timing (app start/exit) rather than on every TX/RX change.
- Linking only PTT to the transmit button makes TX switching respond without delay.
- Only ON requests are preceded by the configured delay; OFF requests always take effect immediately for safety (a pending ON delay is also cancelled by an OFF request).

---

## 4. Network and HTTP API Specification

### 4.1 Network Settings

- Fixed IP address (default `192.168.0.100`/24, gateway `192.168.0.1`). DHCP is not used
- The IP/gateway/subnet are stored in NVS (Preferences) and retained after power loss. They can be changed with `/config/network` (see 4.2 below); after saving, the ESP32 restarts automatically to apply the new settings
- The MAC address is fixed in the sketch (it must not be duplicated on the same LAN)

### 4.2 API List

| Endpoint | Method | Description | Response |
|---|---|---|---|
| `/` | GET | HTML status page (with manual ON/OFF buttons) | HTML |
| `/tx?state=on` | GET | **PTT ON** (called from shonan-android) | `TX` (plain text) |
| `/tx?state=off` | GET | **PTT OFF** (called from shonan-android) | `RX` (plain text) |
| `/toggle?ch=0..1` | GET | Manual toggle of an individual channel (debug feature for checking wiring; 0 = POWER, 1 = PTT) | Redirect to `/` |
| `/ch?idx=0..1&state=on\|off` | GET | Explicit ON/OFF of an individual channel (0 = POWER, 1 = PTT; used for GPIO26 control at Shonan_lite-PI4 GUI start/exit) | `ON`/`OFF` (plain text) |
| `/api/status` | GET | Get the current state as JSON | `{"power":bool,"ptt":bool,"tx_active":bool}` |
| `/config` | GET | Delay time and IP settings page (HTML) | HTML |
| `/config/delay?power_delay_sec=..&ptt_delay_ms=..` | GET | Save the ON delay times for POWER/PTT | Redirect to the settings page, etc. |
| `/config/network?ip=..&gateway=..&subnet=..` | GET | Save the fixed IP address and restart automatically | Redirect to the settings page, etc. |

### 4.3 Call Examples

```
At TX start: GET http://<ESP32 IP address>/tx?state=on
At TX end:   GET http://<ESP32 IP address>/tx?state=off
```

Since the ESP32 uses a fixed IP address (default `192.168.0.100`, see 4.1), the user enters and keeps the same IP address on the settings screen of both shonan-android and Shonan_lite-PI4 (pi4/gui). If the ESP32's IP is changed with `/config/network`, change the app settings accordingly (★automatic discovery via DDNS/mDNS, etc. is not implemented in this revision).

### 4.4 Integration on the Shonan_lite-PI4 (pi4/gui) Side

- In the "PA_Power/PTT Controller (ESP32)" field of the settings screen (`pi4/gui/screens/settings.py`), turn ON "Use ESP32 W5500" and set the ESP32's IP address. When it is OFF or the address is empty, no integration is performed (the IP address is kept even when OFF; TX/RX operation is not affected even without a controller connected).
- `TxController.start()` in `pi4/gui/backend.py` sends GET `/tx?state=on` at its beginning and `stop()` sends `/tx?state=off` at its beginning (only PTT is switched ON/OFF). The timeout is short (1.5 seconds), and even if the ESP32 is not connected or does not respond, the exception is swallowed so that TX itself is not disturbed (it is only logged).
- There is no direct communication path between the ESP32 (MCU1) and the Pluto+. The Pi 4 (pi4/gui) writes `/www/settings.txt` on the Pluto+ via SSH (`_push_pluto_settings()`) and sends `/tx?state=` (`_send_ptt_request()`) to the ESP32 via HTTP, independently of each other; the ESP32 only handles the TX start/stop notifications from the Pi 4.
- Separately from the PTT switching above, GPIO26 (POWER channel, idx=0) is explicitly controlled in conjunction with starting/exiting the Pi 4 app (`pi4/gui/main.py`) itself (`_send_ptt_channel_state()`, using `/ch?idx=0&state=on|off`).
  - GPIO26 is turned ON 5 seconds after app start (also when switching to Langstone V2Modify and when Langstone is selected in the boot menu)
  - At app exit, GPIO26 is turned OFF first, and the app actually exits after waiting 3 seconds
  - The Pi 4's own (Raspberry Pi 4) GPIO is not used for controlling the 12 V power. Only GPIO26 on the MCU1 side is controlled over the network.
- ★The ESP32 W5500 (this controller) is not required. GPIO21 of the Pi 4 (pin 40; GND on pin 39) is HIGH (3.3 V) while transmitting and LOW while receiving, so by buffering it with a transistor/relay driver, etc., the PA and LNA can be switched between TX and RX without the ESP32 (the same pin as Langstone V2Modify's Tx Output; on the Shonan_Lite side it is driven with `pinctrl` by `_set_pi_tx_gpio()` in `pi4/gui/backend.py`). When the ESP32 is also used, this controller's PTT (J6) switches at the same time. This controller is required for switching the 12 V power ON/OFF.

---

## 5. Open Items and Future Work

- ★ Integration testing with the actual 12 V power/PTT drive circuits (checking Q1/Q3/Q5 on real hardware) has not been done.
- ★ Automatic discovery via mDNS (such as `http://shonan-ptt.local/`) is not implemented (the IP address uses the fixed-IP method and is entered manually in the app). To be considered if needed in operation.
- ★ Sending HTTP requests from the shonan-android app is outside the scope of this sketch. It must be added to the app's transmit button handler.
- Writing to the actual ESP32 is complete (2026-08-30, MAC: `70:4b:ca:7b:eb:94`). However, the integration test with the W5500 and the 12 V power/PTT drive circuits actually connected, and the communication check with the Pi 4 (pi4/gui) side, have not been done.
- GPIO25 (former LNA) remains physically unconnected. If LNA control becomes necessary in the future, a drive circuit must be added and the sketch and this document revised again.

---

## 6. Related Files

- Sketch: `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
- Schematic: `hardware/W5500_PA_PTT_Control/kicad/w5500-esp32.kicad_sch` (KiCad original) / `hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_回路図.svg` (SVG exported from KiCad. The hand-drawn outline schematic of the old Rev.1.0 diverged from the actual hardware, so it was abolished on 2026-08-30 and replaced with an export from the KiCad original)
- Detailed MCU1/J1/W5500 pin mapping table: [`MCU1_J1_W5500_connections_en.md`](MCU1_J1_W5500_connections_en.md) (Japanese original: `hardware/W5500_PA_PTT_Control/docs/MCU1_J1_W5500_接続一覧.md`)
