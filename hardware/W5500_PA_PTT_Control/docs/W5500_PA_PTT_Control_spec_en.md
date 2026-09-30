---
title: ESP32+W5500 PA/PTT/LNA Sequence Control Development Specification
---

# ESP32+W5500 PA/PTT/LNA Sequence Control Development Specification

English translation of [`W5500_PA_PTT_Control_仕様書.md`](W5500_PA_PTT_Control_仕様書.md) (Japanese original).
If the two differ, the Japanese original takes precedence.

| Item | Details |
|---|---|
| Revision | Rev.1.0 |
| Created | 2026-08-07 |
| Target board | ESP32 (WROVER family, plain ESP32) + W5500 Ethernet module |
| Target sketch | `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino` |
| Connected app | shonan-android (DATV transmit app) |
| Status | Software implemented and compile-checked. Writing to real hardware and field testing not yet done |

---

## 1. Purpose and Scope

In conjunction with the transmit button of shonan-android, automatically switch the **LNA (receive preamplifier), PTT and PA (power amplifier) power** on the radio side in a safe order via Ethernet.

**In scope**
- 3-channel ON/OFF control of LNA/PTT/PA with ESP32 + W5500
- TX/RX switching by HTTP requests from shonan-android
- Browser UI for manual checking and debugging

**Out of scope**
- Implementing the transmit button and sending HTTP requests in the shonan-android app (must be handled separately on the app side)
- Circuit design of the PA and LNA themselves (the power system implementation depends on the user's radio configuration)

---

## 2. Hardware Configuration

### 2.1 Parts

| Part | Notes |
|---|---|
| ESP32 (WROVER module, etc.) | Plain ESP32. Not the same as native-USB chips such as the ESP32-C3 |
| W5500 Ethernet module | SPI connection. Has no built-in MAC address, so it is set arbitrarily in the sketch |
| Output stage (3 ch) | Power switching for each of the LNA, PTT and PA lines (relay or SSR, depending on the user's system) |

### 2.2 SPI Wiring (ESP32 ⇔ W5500)

| W5500 | ESP32 GPIO |
|---|---|
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| CS (SS) | GPIO 5 |
| RST | Unused (may be connected to 3.3 V or EN, or left unconnected) |
| VCC | 3.3 V |
| GND | GND |

### 2.3 Output Pin Assignment

| Channel | ESP32 GPIO | Logic | State at startup |
|---|---|---|---|
| LNA | GPIO 25 | active-HIGH | **ON** (receive state) |
| PTT | GPIO 26 | active-HIGH | OFF |
| PA | GPIO 27 | active-HIGH | OFF |

> The GPIO outputs are 3.3 V logic, so if they cannot drive the relays/SSRs directly, add a drive stage such as transistors (this document specifies only the logic layer; the drive circuit is shown as an outline in the schematic).

---

## 3. Operation Sequence

### 3.1 TX Start (RX → TX)

When the transmit button of shonan-android is pressed, switching is done in the following order.

```
[Receive state]  LNA=ON, PTT=OFF, PA=OFF
     │
     │ ① LNA OFF
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ② wait 100 ms
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ③ PTT and PA ON at the same time
     ▼
[Transmit state]  LNA=OFF, PTT=ON, PA=ON
```

### 3.2 TX End (TX → RX)

```
[Transmit state]  LNA=OFF, PTT=ON, PA=ON
     │
     │ ① PTT and PA OFF at the same time
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ② wait 100 ms
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ③ LNA ON
     ▼
[Receive state]  LNA=ON, PTT=OFF, PA=OFF
```

### 3.3 Design Intent

- At TX start: disconnecting the LNA first and then raising PTT/PA prevents the LNA from being damaged by high transmit power.
- At TX end: dropping PA/PTT first and then restoring the LNA prevents residual transmit output from reaching the LNA.
- The 100 ms wait can be adjusted with `delay(100)` in `W5500_PA_PTT_Control.ino` according to the actual system switching.

---

## 4. Network and HTTP API Specification

### 4.1 Network Settings

- The IP address is obtained by DHCP (fixed IP is not used, due to the current configuration)
- The MAC address is fixed in the sketch (it must not be duplicated on the same LAN)

### 4.2 API List

| Endpoint | Method | Description | Response |
|---|---|---|---|
| `/` | GET | HTML status page (with manual ON/OFF buttons) | HTML |
| `/tx?state=on` | GET | **TX start** (called from shonan-android) | `TX` (plain text) |
| `/tx?state=off` | GET | **TX end** (called from shonan-android) | `RX` (plain text) |
| `/toggle?ch=0..2` | GET | Manual toggle of an individual channel (debug feature for checking wiring) | Redirect to `/` |
| `/api/status` | GET | Get the current state as JSON | `{"out1":bool,"out2":bool,"out3":bool,"tx_active":bool}` |

`out1` = LNA, `out2` = PTT, `out3` = PA.

### 4.3 Call Example on the shonan-android Side

```
When the transmit button is pressed:  GET http://<ESP32 IP address>/tx?state=on
When the transmit button is released: GET http://<ESP32 IP address>/tx?state=off
```

Since the ESP32's IP address is assigned by DHCP, it is assumed that the user enters and keeps the IP on the shonan-android settings screen, etc. (★automatic discovery via DDNS/mDNS, etc. is not implemented in this revision).

### 4.4 Integration on the Shonan_lite-PI4 (pi4/gui) Side

- Integration is performed only when "Use ESP32 W5500" is turned ON on the settings screen and the IP address is entered
  (no integration when it is OFF or the address is empty; the IP address is kept even when OFF).
- `TxController.start()` in `pi4/gui/backend.py` sends GET `/tx?state=on` and `stop()` sends `/tx?state=off` (only PTT is
  switched ON/OFF; same as the Pi 5 version). The timeout is short (1.5 seconds), and even if the ESP32 is not connected
  or does not respond, the exception is swallowed so that TX itself is not disturbed (it is only logged).
- This controller is also used for controlling the 12 V power in conjunction with app start/exit, and by the
  "Pluto Power" card on the Home screen. On the Langstone V2Modify side, `/tx?state=on|off` is sent in conjunction with
  the hardware PTT and the on-screen PTT.
- ★The ESP32 W5500 (this controller) is not required. GPIO21 of the Pi 4 (pin 40; GND on pin 39) is HIGH (3.3 V) while
  transmitting and LOW while receiving, so by buffering it with a transistor/relay driver, etc., the PA and LNA can be
  switched between TX and RX without the ESP32 (the same pin as Langstone V2Modify's tx output; on the Shonan_Lite side
  it is driven with `pinctrl` by `_set_pi_tx_gpio()` in `pi4/gui/backend.py`). This controller is required for switching
  the 12 V power ON/OFF.

---

## 5. Open Items and Future Work

- ★ The actual drive circuits for PA/PTT/LNA (relay/SSR type, current capacity) depend on the user's radio configuration, so the schematic is presented as an outline (see section 5). See the schematic .svg.
- ★ Fixed IP addressing or mDNS support (such as `http://shonan-ptt.local/`) is not implemented. To be considered if needed in operation.
- ★ Sending HTTP requests from the shonan-android app is outside the scope of this sketch. It must be added to the app's transmit button handler.
- Writing to real hardware and operation testing have not been done (as of 2026-08-07).

---

## 6. Related Files

- Sketch: `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
- Schematic: `hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_回路図.svg`
