---
title: ESP32+W5500 12V電源/PTT制御 開発仕様書 / ESP32+W5500 12 V Power/PTT Control Development Specification
---

# ESP32+W5500 12V電源/PTT制御 開発仕様書 / ESP32+W5500 12 V Power/PTT Control Development Specification

本書は日本語と英語を併記している。各節で日本語の後に英語が続く。表は各欄に日本語と英語を並べて書く。

This document is written in both Japanese and English. In each section, the Japanese text is followed by the English text.
In the tables, each cell gives the Japanese and then the English.

本書はShonan_Lite-RasPI5の同名文書(同じ基板・同じファームウェア)を、Shonan_lite-PI4向けに連携部分を置き換えたものである。

This document is the same-named document of Shonan_Lite-RasPI5 (same board, same firmware) with the integration parts replaced for Shonan_lite-PI4.

| 項目<br>Item | 内容<br>Details |
|---|---|
| 版数<br>Revision | Rev.2.8 |
| 基板の版数(シルク表記)<br>Board revision (silkscreen) | Rev.1.2(仕様書の版数とは別の番号。対応は下の「版数の対応表」を参照)<br>Rev.1.2 (a number separate from this document's revision; see "Revision Correspondence" below) |
| 作成日<br>Created | 2026-08-07（Rev.2.0更新: 2026-08-30、実機回路(KiCad)に合わせて全面改訂／Rev.2.1更新: 2026-08-30、電源系統を訂正。J3(外付けDCDCバックコンバータ)は廃止し、U2(L7805)の+5VをMCU1とU1(TA48033S)の両方に供給する単一系統に修正／Rev.2.2更新: 2026-08-31、J1をFreenove実機の40pin DevKitCソケット配列に修正しMCU1もJ1と同じピン番号・信号名に統一。Power(スイッチ後12V)系統に赤色LED(D1)、+12V(入力側)系統に緑色LED(D2)の表示回路を追加／Rev.2.3更新: 2026-09-30、R8を100Ωに変更(KiCad回路図に合わせる)しR9を追記、IPアドレスの記述を固定IP方式に統一、12V電源ONまでの遅延を実装値(5秒)に訂正、Shonan_lite-PI4側の「ESP32 W5500を使用する」設定とPi4 GPIO21によるPTT出力を追記／Rev.2.4更新: 2026-09-30、R8を1kΩ(1/2W推奨)に変更、Q1のベースをGNDへプルダウンするR12(10kΩ)を追加、KiCadのQ5シンボルを2SJ334の足の並び(1=G、2=D、3=S)に合わせて修正、U1・U2・Q5に放熱器を追加／Rev.2.5更新: 2026-09-30、前面・背面の丸型コネクタの裏に配線用の空き(内壁から20mm)を確保するため、放熱器の列を下へ移し(間隔22mm)、トランジスタ・LED・J5・J6を空きの手前へ移動／Rev.2.6更新: 2026-09-30、回路図の一部のGND記号の値が空で別ネットになっていたのを修正、内層をGND・+12Vの全面ベタにし12V出力を幅4mmで引いたうえで残りを自動配線、Q1・Q3を足の間隔2.54mmのTO-92に変更、Power表示LED(D1)・+12V表示LED(D2)を外付けにしてそれぞれJ7・J8で接続、J6・J7・J8をJST XHコネクタ(B2B-XH-A)に変更、R8の基板の穴を1/2W抵抗用に変更、C2をTA48033Sのデータシートどおり33µF・C1とC3を0.33µFに変更、Q3のベースにプルダウン抵抗R13(10kΩ)を追加、J1のGNDピン21〜24・40を接続、Q5の発熱の目安を高温時のオン抵抗で見直し／2026-10-01追記: J1の35番ピン(W5500 RST)の配線が+5Vのビアに0.3mmまで近づいていたため、+5V(`/+5v0`)を信号線から0.5mm以上離し(線幅0.6mm)、J1のピンとピンの間に配線を通さないよう再配線(基板の版数表記はRev.1.0)／Rev.2.7更新: 2026-10-01、放熱器(20PB020)の取付ピン(φ1.4mm、間隔12.5mm)用のめっき無し穴(φ1.8mm、周囲1mmは全層で銅箔なし)を追加し、M3穴の高さを基板から19mmに訂正(基板の版数をRev.1.1に変更)／Rev.2.8更新: 2026-10-03、3.3VレギュレータU1をTA48033SからLM2940T-3.3(TO-220、1=IN・2=GND・3=OUT)に変更。足の並びが違うためU1の2番をGND・3番を+3V3_Aにつなぎ替えて裏面の配線を引き直し、C1をLM2940のデータシートどおり0.47µFに変更(基板の版数をRev.1.2に変更)）<br>2026-08-07 (Rev.2.0 update: 2026-08-30, fully revised to match the actual circuit (KiCad) / Rev.2.1 update: 2026-08-30, power system corrected: J3 (external DC-DC buck converter) removed, and the +5 V from U2 (L7805) now feeds both MCU1 and U1 (TA48033S) as a single system / Rev.2.2 update: 2026-08-31, J1 corrected to the pinout of the actual Freenove 40-pin DevKitC socket and MCU1 unified with J1's pin numbers and signal names; indicator circuits added: a red LED (D1) on the Power (switched 12 V) line and a green LED (D2) on the +12 V (input side) line / Rev.2.3 update: 2026-09-30, R8 changed to 100 Ω (to match the KiCad schematic) and R9 added, IP address description unified to the fixed-IP method, the delay until the 12 V power turns ON corrected to the implemented value (5 seconds), and the "Use ESP32 W5500" setting and PTT output via Pi 4 GPIO21 on the Shonan_lite-PI4 side added / Rev.2.4 update: 2026-09-30, R8 changed to 1 kΩ (1/2 W recommended), R12 (10 kΩ) added to pull Q1's base down to GND, the KiCad symbol of Q5 corrected to the 2SJ334 pinout (1 = G, 2 = D, 3 = S), and heatsinks added to U1, U2 and Q5 / Rev.2.5 update: 2026-09-30, to leave 20 mm of wiring space (from the inner wall) behind the front and back round connectors, the heatsink column moved down (22 mm pitch) and the transistors, LEDs, J5 and J6 moved in front of that space / Rev.2.6 update: 2026-09-30, fixed GND symbols in the schematic whose value was empty (they formed a separate net), made the inner layers full GND and +12 V planes, laid the 12 V output as a 4 mm trace and autorouted the rest, changed Q1 and Q3 to the TO-92 footprint with 2.54 mm lead pitch, made the Power indicator LED (D1) and the +12 V indicator LED (D2) external, connected through J7 and J8, changed J6, J7 and J8 to JST XH connectors (B2B-XH-A), changed the R8 footprint to one for a 1/2 W resistor, changed C2 to 33 µF as in the TA48033S datasheet and C1 and C3 to 0.33 µF, added a pull-down resistor R13 (10 kΩ) on Q3's base, connected J1's GND pins 21–24 and 40, and revised the Q5 heat estimate using the on-resistance at high temperature / added 2026-10-01: because the trace from J1 pin 35 (W5500 RST) came within 0.3 mm of a +5 V via, re-routed so that +5 V (`/+5v0`) is at least 0.5 mm from signal traces (0.6 mm wide) and no trace passes between the pins of J1 (the board is marked Rev.1.0) / Rev.2.7 update: 2026-10-01, added non-plated holes (1.8 mm, no copper on any layer within 1 mm) for the heatsink (20PB020) mounting pins (1.4 mm dia., 12.5 mm pitch), and corrected the M3 hole height to 19 mm above the board (board revision changed to Rev.1.1) / Rev.2.8 update: 2026-10-03, the 3.3 V regulator U1 changed from the TA48033S to the LM2940T-3.3 (TO-220, 1 = IN, 2 = GND, 3 = OUT); because the pinout differs, U1 pin 2 was reconnected to GND and pin 3 to +3V3_A and the bottom-layer trace re-routed, and C1 changed to 0.47 µF as in the LM2940 datasheet (board revision changed to Rev.1.2)) |
| 対象ボード<br>Target board | ESP32 (WROVER系、無印ESP32) + W5500 イーサネットモジュール<br>ESP32 (WROVER family, plain ESP32) + W5500 Ethernet module |
| 対象スケッチ<br>Target sketch | `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino` |
| 連携先<br>Connected apps | shonan-android（DATV送信アプリ）、Shonan_lite-PI4（pi4/gui、送信画面のTX開始/終了およびアプリ起動/終了に連動）<br>shonan-android (DATV transmit app), Shonan_lite-PI4 (pi4/gui; linked to TX start/stop on the transmit screen and to app start/exit) |
| ステータス<br>Status | 実機ESP32(ESP32-D0WD-V3)へ書き込み・起動確認済み（2026-08-30）。無線機を含めた実地テスト（12V電源/PTT駆動回路との結合試験）は未実施<br>Written to and boot-confirmed on an actual ESP32 (ESP32-D0WD-V3) (2026-08-30). Field testing including the radio (integration test with the 12 V power/PTT drive circuits) not yet done |

---

## 版数の対応表 / Revision Correspondence

仕様書の版数と基板の版数(シルク表記)は別の番号で管理する。基板を変更して製造し直すときは基板の版数を上げ、
この表に行を追加する。

The revision of this document and the revision of the board (silkscreen) are managed as separate numbers. When the
board is changed and manufactured again, raise the board revision and add a row to this table.

| 仕様書の版数<br>Document revision | 日付<br>Date | 基板の版数(シルク表記)<br>Board revision (silkscreen) | 備考<br>Notes |
|---|---|---|---|
| Rev.1.0〜1.1 | 2026-08-07〜 | —(プリント基板なし)<br>— (no PCB) | LNA/PTT/PAの3チャンネル構成の旧仕様。KiCadで回路図を作る前<br>Old specification with three channels (LNA/PTT/PA), before the schematic was drawn in KiCad |
| Rev.2.0〜2.5 | 2026-08-30〜2026-09-30 | —(未製造)<br>— (not manufactured) | KiCadで回路図・基板を設計中<br>Schematic and PCB being designed in KiCad |
| Rev.2.6 | 2026-09-30(2026-10-01追記を含む)<br>2026-09-30 (including the 2026-10-01 additions) | Rev.1.0 | 放熱器の取付ピン用の穴なし<br>No holes for the heatsink mounting pins |
| Rev.2.7 | 2026-10-01 | Rev.1.1 | 放熱器の取付ピン用のめっき無し穴を追加。U1はTA48033S(1=IN・2=OUT・3=GND)の足の並び<br>Non-plated holes for the heatsink mounting pins added. U1 uses the TA48033S pinout (1 = IN, 2 = OUT, 3 = GND) |
| Rev.2.8 | 2026-10-03 | **Rev.1.2** | U1をLM2940T-3.3(1=IN・2=GND・3=OUT)に変更し配線を引き直し、C1を0.47µFに変更。`fabrication/jlcpcb/`の発注データはこの版。Rev.1.1の基板にLM2940T-3.3を載せると出力とGNDが逆になるので使わない<br>U1 changed to the LM2940T-3.3 (1 = IN, 2 = GND, 3 = OUT) with re-routed traces, and C1 changed to 0.47 µF. The order data in `fabrication/jlcpcb/` is for this revision. Do not fit an LM2940T-3.3 on a Rev.1.1 board, as its output and GND would be swapped |

---

## 1. 目的・スコープ / Purpose and Scope

shonan-android の送信ボタン操作に連動して **PTT** を、Shonan_lite-PI4(pi4/gui)アプリの起動/終了操作に連動して **12V電源(PA等の外部機器用)** を、それぞれイーサネット経由でON/OFF制御する。

Rev.1.1まではLNA/PTT/PAの3ch・シーケンス制御（送信時にLNAを切り離してからPTT/PAを立ち上げる等）を想定していたが、実機回路(KiCad)ではLNA用の駆動回路が存在せず、**12V電源ON/OFF（2SJ334によるハイサイドスイッチ）とPTT ON/OFFの2機能のみ**が実装されている。本書はこの実機回路に合わせて全面改訂した。

Control, via Ethernet, **PTT** in conjunction with the transmit button of shonan-android, and the **12 V power (for external equipment such as a PA)** in conjunction with starting/exiting the Shonan_lite-PI4 (pi4/gui) app.

Up to Rev.1.1, 3-channel LNA/PTT/PA sequence control was assumed (e.g. disconnecting the LNA before raising PTT/PA when transmitting), but the actual circuit (KiCad) has no LNA drive circuit and implements **only two functions: 12 V power ON/OFF (high-side switch with a 2SJ334) and PTT ON/OFF**. This document has been fully revised to match the actual circuit.

**スコープに含むもの / In scope**
- ESP32 + W5500 による12V電源／PTT 2チャンネルのON/OFF制御 / 2-channel ON/OFF control of 12 V power / PTT with ESP32 + W5500
- shonan-androidからのHTTPリクエストによるPTTのTX/RX切替 / PTT TX/RX switching by HTTP requests from shonan-android
- Shonan_lite-PI4(pi4/gui)アプリの起動/終了に連動した12V電源のON/OFF / 12 V power ON/OFF linked to starting/exiting the Shonan_lite-PI4 (pi4/gui) app
- ブラウザによる手動確認・デバッグ用UI / Browser UI for manual checking and debugging

**スコープに含まないもの / Out of scope**
- shonan-androidアプリ側での送信ボタン実装・HTTPリクエスト送出処理（別途アプリ側での対応が必要） / Implementing the transmit button and sending HTTP requests in the shonan-android app (must be handled separately on the app side)
- 12V電源の供給先となるPA・LNA等自体の回路設計（利用者の無線機構成に依存） / Circuit design of the PA, LNA, etc. that receive the 12 V power (depends on the user's radio configuration)

---

## 2. ハードウェア構成 / Hardware Configuration

### 2.1 使用部品 / Parts

| 部品<br>Part | 備考<br>Notes |
|---|---|
| ESP32 (WROVERモジュール等)<br>ESP32 (WROVER module, etc.) | 無印ESP32。ESP32-C3等のネイティブUSBチップとは別物<br>Plain ESP32. Not the same as native-USB chips such as the ESP32-C3 |
| W5500 イーサネットモジュール<br>W5500 Ethernet module | SPI接続。MACアドレス内蔵なしのためスケッチ内で任意設定<br>SPI connection. Has no built-in MAC address, so it is set arbitrarily in the sketch |
| Q5 (2SJ334) | P-ch パワーMOSFET。12V電源のハイサイドスイッチ（旧リレーK3を置き換え）<br>P-channel power MOSFET. High-side switch for the 12 V power (replaces the former relay K3) |
| Q1 (2SC1815) | Q5のゲート駆動用NPNトランジスタ（GPIO26でON/OFF）<br>NPN transistor driving Q5's gate (switched by GPIO26) |
| R8 (1kΩ、1/2W)<br>R8 (1 kΩ, 1/2 W) | Q5のゲートを+12Vへプルアップする抵抗（Q1 OFF時にQ5をOFFに保つ）。Q1 ON中は約12〜14mAが流れ、約0.14〜0.2Wを消費するため1/2Wとする(1/4Wでは定格の約8割で余裕がない)。基板の穴は直径3.2mm・長さ9mmの1/2W抵抗の縦置き用(足の間隔5.08mm)<br>Pull-up resistor from Q5's gate to +12 V (keeps Q5 OFF while Q1 is OFF). About 12–14 mA flows while Q1 is ON, dissipating about 0.14–0.2 W, so a 1/2 W part is used (a 1/4 W part would run at about 80% of its rating, with no margin). The PCB footprint is for a 1/2 W resistor 3.2 mm in diameter and 9 mm long, mounted vertically (5.08 mm lead pitch) |
| R12 (10kΩ)<br>R12 (10 kΩ) | Q1のベースをGNDへプルダウンする抵抗(ESP32の起動中などGPIO26が確定しない間もQ1を確実にOFFにする)<br>Pull-down resistor from Q1's base to GND (keeps Q1 reliably OFF even while GPIO26 is undetermined, e.g. during ESP32 startup) |
| R13 (10kΩ)<br>R13 (10 kΩ) | Q3のベースをGNDへプルダウンする抵抗(ESP32の起動中や書き込み中などGPIO27が確定しない間もQ3をOFFにし、PTTが勝手にONにならないようにする)<br>Pull-down resistor from Q3's base to GND (keeps Q3 OFF, so PTT does not turn ON by itself, even while GPIO27 is undetermined, e.g. during ESP32 startup or programming) |
| Q3 (2SC1815) | PTT_ON信号駆動用NPNトランジスタ（GPIO27でON/OFF、オープンコレクタ的にGND側へ落とす）<br>NPN transistor driving the PTT_ON signal (switched by GPIO27; pulls down to GND like an open collector) |
| R9 (10kΩ)<br>R9 (10 kΩ) | W5500(A1)のRST(GPIO21と同一ネット)を+3V3_Aへプルアップする抵抗<br>Pull-up resistor from the W5500 (A1) RST (same net as GPIO21) to +3V3_A |
| J2 (DC_IN_13V8) | 外部電源(13.8V/12V系)の入力コネクタ<br>Input connector for the external power supply (13.8 V/12 V) |
| U2 (L7805) | +12V→+5Vのリニアレギュレータ(TO-220)。生成した+5V(`+5v0`)はMCU1(J1)とU1の両方に供給される<br>+12 V → +5 V linear regulator (TO-220). The generated +5 V (`+5v0`) feeds both MCU1 (J1) and U1 |
| U1 (LM2940T-3.3) | U2出力の+5V→+3.3Vのリニアレギュレータ(TO-220、1A、足は1=IN・2=GND・3=OUT)。W5500(A1)のVCC(+3V3_A)専用<br>+5 V (U2 output) → +3.3 V linear regulator (TO-220, 1 A, pins 1 = IN, 2 = GND, 3 = OUT). Dedicated to the W5500 (A1) VCC (+3V3_A) |
| C3 (0.33µF、25V以上)<br>C3 (0.33 µF, 25 V or higher) | U2(L7805)の入力(+12V)側コンデンサ<br>Input (+12 V) capacitor of U2 (L7805) |
| C1 (0.47µF、16V以上)<br>C1 (0.47 µF, 16 V or higher) | U2の出力・U1の入力(+5V)側コンデンサ(LM2940データシートのCIN=0.47µF。U1が電源のフィルタから離れているときは必要)<br>Capacitor on U2's output / U1's input (+5 V) (CIN = 0.47 µF in the LM2940 datasheet; required when U1 is far from the supply filter) |
| C2 (33µF、10V以上の電解コンデンサ)<br>C2 (33 µF, electrolytic, 10 V or higher) | U1(LM2940T-3.3)の出力(+3.3V)側コンデンサ。LM2940は出力コンデンサが22µF以上でESRが0.1〜1Ωでないと発振するおそれがあるため、33µFの電解コンデンサとする(0.1µFのセラミックでは不足)。+側が+3.3V<br>Output (+3.3 V) capacitor of U1 (LM2940T-3.3). The LM2940 may oscillate unless the output capacitor is at least 22 µF with an ESR of 0.1–1 Ω, so a 33 µF electrolytic capacitor is used (a 0.1 µF ceramic is not enough). The + side goes to +3.3 V |
| J1 (ESP32_DevKitC_Socket_40P) | Freenove ESP32-WROOM-32E DevKitC(40pin、25.4mm幅)を直接プラグインするメスソケット<br>Female socket into which a Freenove ESP32-WROOM-32E DevKitC (40 pins, 25.4 mm wide) plugs directly |
| J7 (LED_PWR) + R10 (10kΩ)<br>J7 (LED_PWR) + R10 (10 kΩ) | Power(Q5出力・スイッチ後12V)系統の通電表示。表示LED(赤)は基板に載せず外付けとし、JST XHコネクタ(J7)で接続する。J7の1番=LEDのアノード(R10(10kΩ)で電流制限)、2番=カソード(GND)<br>Power indicator for the Power line (Q5 output, switched 12 V). The indicator LED (red) is not mounted on the board; it is external and connected through J7, a JST XH connector. J7 pin 1 = LED anode (current-limited by R10, 10 kΩ), pin 2 = cathode (GND) |
| J8 (LED_12V) + R11 (10kΩ)<br>J8 (LED_12V) + R11 (10 kΩ) | +12V(J2入力・未スイッチ)系統の通電表示。表示LED(緑)は基板に載せず外付けとし、JST XHコネクタ(J8)で接続する。J8の1番=LEDのアノード(R11(10kΩ)で電流制限)、2番=カソード(GND)<br>Power indicator for the +12 V line (J2 input, unswitched). The indicator LED (green) is not mounted on the board; it is external and connected through J8, a JST XH connector. J8 pin 1 = LED anode (current-limited by R11, 10 kΩ), pin 2 = cathode (GND) |

### 2.2 SPI配線（ESP32 ⇔ W5500） / SPI Wiring (ESP32 ⇔ W5500)

| W5500 | ESP32 GPIO |
|---|---|
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| CS (SS) | GPIO 5 |
| RST | GPIO 21（active-LOW。起動時にESP32からパルスを出してハードリセット）<br>GPIO 21 (active-LOW. The ESP32 sends a pulse at startup for a hard reset) |
| VCC | 3.3V |
| GND | GND |

### 2.3 出力ピン割り当て / Output Pin Assignment

| チャンネル<br>Channel | ESP32 GPIO | 論理<br>Logic | 起動時状態<br>State at startup | 駆動回路<br>Drive circuit | 出力先<br>Output |
|---|---|---|---|---|---|
| POWER (12V電源)<br>POWER (12 V power) | GPIO 26 | active-HIGH | OFF | R6→Q1(2SC1815、ベースはR12でGNDへプルダウン)→Q5(2SJ334, PMOSハイサイドスイッチ、ゲートはR8で+12Vへプルアップ)<br>R6 → Q1 (2SC1815, base pulled down to GND by R12) → Q5 (2SJ334, PMOS high-side switch, gate pulled up to +12 V by R8) | J5 (Power) |
| PTT | GPIO 27 | active-HIGH | OFF | R7→Q3(2SC1815)<br>R7 → Q3 (2SC1815) | J6 (PTT_ON、無線機PTT端子をGND側へ落とす方式)<br>J6 (PTT_ON; pulls the radio's PTT terminal to GND) |

> GPIO25は旧仕様(Rev.1.1)でLNA制御用として予約されていたが、実機回路では駆動回路が実装されておらず未接続(回路図でもJ1の12番ピンを未接続(×)にしている)。現行スケッチ・本書では扱わない。
>
> POWER(GPIO26)・PTTともにラッチ式のON/OFF出力であり、送信/受信の自動切替シーケンス（100ms待機等）は行わない。POWERとPTTは完全に独立したチャンネルとして扱う。
>
> GPIO25 was reserved for LNA control in the old specification (Rev.1.1), but the actual circuit has no drive circuit for it and it is unconnected (pin 12 of J1 is marked as no-connect (×) in the schematic). It is not handled by the current sketch or this document.
>
> Both POWER (GPIO26) and PTT are latched ON/OFF outputs; no automatic TX/RX switching sequence (such as a 100 ms wait) is performed. POWER and PTT are treated as completely independent channels.

### 2.4 電源系統 / Power System

外部から供給される+12V(13.8V)を起点に、**U2(L7805)が生成する+5V(`+5v0`)を
MCU1(DevKitC基板)とU1(LM2940T-3.3)の両方に分岐供給**する、単一系統の構成である。

Starting from the externally supplied +12 V (13.8 V), it is a single-system configuration in which **the +5 V (`+5v0`)
generated by U2 (L7805) is branched to both MCU1 (DevKitC board) and U1 (LM2940T-3.3)**.

```
J2(+12V,13.8V)
   │
   U2(L7805、12V→5V)
   │
   +5V(`+5v0`ネット / net) ──┬── J1(1) → MCU1(DevKitC基板 / board) ※基板内蔵LDOで3.3Vに変換しESP32モジュールへ
                               │                                     (converted to 3.3 V by the on-board LDO for the ESP32 module)
                               └── U1(LM2940T-3.3、5V→3.3V) → A1(VCC、W5500)
```

| 供給先<br>Supplied to | 経路<br>Path | 備考<br>Notes |
|---|---|---|
| MCU1(DevKitC)用<br>MCU1 (DevKitC) | +12V → U2(L7805、12V→5V) → J1(1) | DevKitC基板上のオンボードLDOがこの5Vを3.3Vに変換しESP32モジュールへ供給する<br>The on-board LDO of the DevKitC converts this 5 V to 3.3 V for the ESP32 module |
| W5500用<br>W5500 | +12V → U2(L7805、12V→5V) → U1(LM2940T-3.3、5V→3.3V) → A1(VCC) | U2出力の`+5v0`をU1がさらに3.3Vへ降圧しW5500(A1)のVCCへ供給<br>U1 further steps the `+5v0` output of U2 down to 3.3 V for the W5500 (A1) VCC |

MCU1用・W5500用いずれも起点はU2(L7805)の+5V出力であり、外付けのDCDCバックコンバータ
モジュールは使用しない（旧Rev.2.0で存在したJ3は廃止）。詳細な接続関係は
[`MCU1_J1_W5500_接続一覧.md`](MCU1_J1_W5500_接続一覧.md)「電源系統の接続詳細」を参照。

Both the MCU1 and W5500 supplies start from the +5 V output of U2 (L7805); no external DC-DC buck converter module is
used (J3, which existed in the old Rev.2.0, has been removed). For detailed connections, see "Power System Connection
Details" in [`MCU1_J1_W5500_接続一覧.md`](MCU1_J1_W5500_接続一覧.md).

### 2.5 放熱器 / Heatsinks

U2(L7805)・U1(LM2940T-3.3)・Q5(2SJ334)には、それぞれ放熱器を付ける。

A heatsink is attached to each of U2 (L7805), U1 (LM2940T-3.3) and Q5 (2SJ334).

| 項目<br>Item | 内容<br>Details |
|---|---|
| 放熱器<br>Heatsink | 秋月電子 [105054] 放熱器(ヒートシンク)20×20×25mm(型番20PB020-01025)<br>Akizuki Denshi [105054] heatsink 20×20×25 mm (part number 20PB020-01025) |
| 寸法<br>Dimensions | 20×20mm、高さ25mm。部品取付用のM3タップ穴は、基板から19mm・横は端から10mm(幅の中央)の位置にあり、M3ねじで部品のタブを固定する。TO-220のタブの穴は本体下端から約13mm(品種により差があり、実物で要確認)なので、部品は本体下端が基板から約6mm浮いた高さで取り付ける。基板取付用の金属ピン(φ1.4mm、基板下へ約4.5mm)が2本あり、間隔は12.5mm(幅の中央から±6.25mm)、部品取付面から3.5mm奥の位置。基板にはφ1.8mmのめっき無し穴を開け、ピンが内層のGND・+12Vのベタや配線とショートしないよう、穴の縁から1mm以内は全層で銅箔を置かない(ピンははんだ付けしない。放熱器はM3ねじと部品の足で固定)。U1・U2はタブがGNDのため放熱器もGND電位、Q5(TO-220NIS)は絶縁。基板上では、放熱器の部品側の面をタブの裏面にそろえ、放熱器の中央(穴の位置)が各部品の中央の足に来るように置いた<br>20×20 mm, 25 mm high. With pins for PCB mounting. The M3 tapped hole for the part is 19 mm above the board and 10 mm from the side (center of the width), and the part's tab is fixed with an M3 screw. The tab hole of a TO-220 is about 13 mm above the bottom of the body (varies by part; check against the actual part), so each part is mounted with the bottom of its body about 6 mm above the board. The heatsink has two metal mounting pins (1.4 mm dia., about 4.5 mm below the board) at 12.5 mm pitch (±6.25 mm from the center of the width), 3.5 mm behind the part-mounting face. The board has 1.8 mm non-plated holes for them, and no copper is placed on any layer within 1 mm of the hole edge so the pins cannot short to the inner GND/+12 V planes or traces (the pins are not soldered; the heatsink is held by the M3 screw and the part's leads). The tabs of U1 and U2 are GND, so their heatsinks are at GND potential; Q5 (TO-220NIS) is isolated. On the PCB, the part-side face of each heatsink is aligned with the back of the tab, and the center of the heatsink (the hole position) is aligned with the part's middle lead |
| 熱抵抗<br>Thermal resistance | 15.8℃/W |
| 基板上の配置<br>Placement on the PCB | 基板外形は横72mm×縦115mm(従来の手配線基板95×72mmを縦に20mm延長)。左上にW5500モジュール(RJ45は上端側)、その下にESP32 DevKitC(J1、USBは下端側)、右側にTO-220の3部品(U1・U2・Q5)を22mm間隔で縦に並べて放熱タブを右端側に向け、放熱器(20×20mm)を右端側に置く。左端に抵抗、右下にトランジスタ・LEDを配置。大電流の外部配線は電線はんだ付け用パッドで、J2(+12V入力、1mm²線用)は右上(前面の丸型コネクタ側)、J5(12V出力、1mm²線用)は右下(背面の丸型コネクタ側)に置く。小電流のJ6(PTT出力)・J7(外付けPower表示LED)・J8(外付け+12V表示LED)はJST XHコネクタ(B2B-XH-A、2ピン、ピッチ2.5mm、定格3A)とし、J7(左)・J6(右)はW5500モジュールとESP32ソケットの間の空きに横に並べ、J8は左端(R11の下)に置く(KiCadの基板データのDwgs.Userレイヤーに各範囲を記入。W5500モジュール等の寸法は実物のデータで更新予定)。4層基板で、内層1をGNDの全面ベタ、内層2を+12V(入力側)の全面ベタとし、GNDと+12Vは配線せずに内層で接続する。スイッチ後の12V出力(/Power、5A以上)はQ5のドレインからJ5まで表裏両面に幅4mm(Q5の足の間は2mm)の太いパターンで引く。J2・J5・Q5のパッドはベタ面へ直結(サーマルなし)。それ以外の信号はFreerouting(自動配線)で表裏2層に配線した(信号0.3mm、+3.3V・LED用の/Power分岐は0.8mm、+5Vは0.6mm)。+5V(`/+5v0`)はネットクラスSupply5Vで信号線から0.5mm以上離す(C1自身の足の間だけは部品の寸法で0.4mmのため、`kicad/w5500-esp32.kicad_dru`の例外ルールで0.25mmとする)。J1(ESP32ソケット)のピンとピンの間には、はんだブリッジを避けるため表裏とも配線禁止領域を置き、配線を通さない(同じ+5Vの1番・2番の間だけは除く)。Q1・Q3は足の間隔2.54mmのTO-92(Inline_Wide)。放熱器の取付ピンはめっき無し穴(φ1.8mm、周囲1mm銅箔なし)<br>The board outline is 72 mm wide × 115 mm tall (the previous hand-wired 95×72 mm board extended by 20 mm vertically). The W5500 module is at the top left (RJ45 toward the top edge), the ESP32 DevKitC (J1, USB toward the bottom edge) below it, and the three TO-220 parts (U1, U2, Q5) are stacked vertically on the right at 22 mm pitch with their tabs facing the right edge and the heatsinks (20×20 mm) on the right-edge side. The resistors are on the left edge and the transistors and LEDs at the bottom right. High-current external wiring uses solder-wire pads: J2 (+12 V input, for 1 mm² wire) is at the top right (front round connector side), and J5 (12 V output, for 1 mm² wire) is at the bottom right (back round connector side). The low-current J6 (PTT output), J7 (external Power indicator LED) and J8 (external +12 V indicator LED) are JST XH connectors (B2B-XH-A, 2-pin, 2.5 mm pitch, rated 3 A); J7 (left) and J6 (right) are placed side by side in the space between the W5500 module and the ESP32 socket, and J8 is on the left edge (below R11) (each area is drawn on the Dwgs.User layer of the KiCad PCB data; the dimensions of the W5500 module, etc. will be updated with data from the actual parts). The board is 4-layer: inner layer 1 is a full GND plane and inner layer 2 is a full +12 V (input side) plane, so GND and +12 V are connected through the inner layers without traces. The switched 12 V output (/Power, 5 A or more) runs from Q5's drain to J5 as a wide trace on both outer layers (4 mm, narrowing to 2 mm between Q5's leads). The J2, J5 and Q5 pads connect to the planes solidly (no thermal relief). All other signals are routed on the two outer layers with Freerouting (autorouter): 0.3 mm for signals, 0.8 mm for +3.3 V and the /Power branch to the LED, and 0.6 mm for +5 V. +5 V (`/+5v0`) is kept at least 0.5 mm from signal traces by the Supply5V net class (only between C1's own pads, which are 0.4 mm apart by the part's dimensions, an exception rule in `kicad/w5500-esp32.kicad_dru` allows 0.25 mm). Between the pins of J1 (ESP32 socket), keepout areas on both layers prevent traces from passing, to avoid solder bridges (except between pins 1 and 2, which are both +5 V). Q1 and Q3 use the TO-92 footprint with 2.54 mm lead pitch (Inline_Wide). The heatsink mounting pins go into non-plated holes (1.8 mm, no copper within 1 mm) |
| ケースと取付穴<br>Case and mounting holes | ケース(OpenSCAD「LAN_PTT.scad」)は内寸80×120×35mm。底のボス(外径8mm、高さ5mm)にM3インサートを埋め込み、基板をM3ねじで固定する。基板の取付穴はM3用φ3.2mmで、ボスと同じ66×109mm間隔(基板の各辺から3mm内側)。ボスが当たる穴の周り半径4mmには部品の足を置かない。前面(基板上端側)にRJ45用の角穴とφ16の丸穴、背面(基板下端側)にUSB用の角丸穴とφ16の丸穴があり、W5500のRJ45とDevKitCのUSBがそれぞれの開口に来るよう配置した。前面の丸型コネクタ(WTN-11-1253 8P)には+12VとGND、背面の丸型コネクタには12V出力・GND・PTTをつなぐ。丸型コネクタはパネルの裏へ約10mm出るため、配線の余裕を含めて内壁から20mm(基板の上端・下端から17.5mm)、幅20mm(基板のx=46〜66mm、左端基準)の範囲には背の高い部品を置かない。この範囲にあるのは前面側のJ2(電線はんだ付け用パッド)だけ<br>The case (OpenSCAD "LAN_PTT.scad") has inner dimensions of 80×120×35 mm. M3 inserts are embedded in the bosses on the bottom (8 mm OD, 5 mm high), and the board is fixed with M3 screws. The mounting holes on the board are φ3.2 mm for M3 at the same 66×109 mm pitch as the bosses (3 mm inside each board edge). No component leads within a 4 mm radius around the holes where the bosses touch. The front (board top edge side) has a rectangular opening for RJ45 and a φ16 round hole, and the back (board bottom edge side) has a rounded opening for USB and a φ16 round hole; the board is laid out so that the W5500's RJ45 and the DevKitC's USB line up with their openings. The front round connector (WTN-11-1253 8P) carries +12 V and GND, and the back round connector carries the 12 V output, GND and PTT. Because each round connector extends about 10 mm behind the panel, an area 20 mm deep from the inner wall (17.5 mm from the board's top and bottom edges) and 20 mm wide (board x = 46–66 mm from the left edge) is kept free of tall parts to leave room for wiring. The only item in that area is J2 (solder-wire pads) on the front side |

発熱の目安(入力14V時):

- U2(L7805): 出力電流を最大約0.25A(ESP32 DevKitCとW5500の合計の目安)とすると、損失は(14V−5V)×0.25A≒2.3W。
  放熱器15.8℃/W+接合部〜ケース間(約5℃/W)で温度上昇は約50℃。
- U1(LM2940T-3.3): (5V−3.3V)×約0.13A(W5500)≒0.2Wと小さい。
- Q5(2SJ334): 損失はオン抵抗(最大38mΩ@VGS=−10V)×電流²。放熱器15.8℃/W+接合部〜ケース間2.78℃/Wで約19℃/Wとして、5Aで約1W。高温時はオン抵抗が約1.5倍になるので約1.4Wとみると、温度上昇は約27℃。閉じたケース内の気温を約45℃(室温30℃+L7805等の発熱による上昇約15℃)として、接合部は約70℃(上限150℃)、放熱器表面は約65〜70℃で余裕がある。
  10Aでは高温時に約5.7W・温度上昇約110℃となりこの放熱器では不足するため、この放熱器での目安は約7Aまで。タブと放熱器の間には放熱グリスを塗る。PA等の実際の負荷電流に合わせて確認すること。

Rough heat estimate (at 14 V input):

- U2 (L7805): with a maximum output current of about 0.25 A (rough total of the ESP32 DevKitC and the W5500), the loss is
  (14 V − 5 V) × 0.25 A ≈ 2.3 W. With the heatsink's 15.8 °C/W plus junction-to-case (about 5 °C/W), the temperature rise is about 50 °C.
- U1 (LM2940T-3.3): (5 V − 3.3 V) × about 0.13 A (W5500) ≈ 0.2 W, which is small.
- Q5 (2SJ334): the loss is on-resistance (max 38 mΩ at VGS = −10 V) × current². Taking about 19 °C/W (heatsink 15.8 °C/W plus junction-to-case 2.78 °C/W),
  about 1 W at 5 A. The on-resistance rises to about 1.5 times at high temperature, so taking about 1.4 W, the rise is about 27 °C. Assuming the air inside the closed case is about 45 °C (30 °C room plus about 15 °C from the heat of L7805, etc.), the junction is about 70 °C (limit 150 °C) and the heatsink surface about 65–70 °C, which leaves margin.
  At 10 A the loss at high temperature is about 5.7 W with a rise of about 110 °C, which this heatsink cannot handle, so the guideline with this heatsink is up to about 7 A. Apply thermal grease between the tab and the heatsink. Check against the actual load current of the PA, etc.

---

## 3. 動作仕様 / Operation

Rev.1.1までの「LNA off→100ms待機→PTT/PA on」のようなシーケンス制御は廃止し、POWERとPTTはそれぞれ独立したON/OFFイベントに連動する。

Sequence control such as "LNA off → wait 100 ms → PTT/PA on" used up to Rev.1.1 has been abolished; POWER and PTT each follow independent ON/OFF events.

### 3.1 PTT（shonan-android 送信ボタン連動） / PTT (linked to the shonan-android transmit button)

- 送信ボタンON: `GET /tx?state=on` → 設定した遅延時間(`ptt_delay_ms`、デフォルト50ms)後にPTT(GPIO27) ON
- 送信ボタンOFF: `GET /tx?state=off` → PTT(GPIO27) 即時OFF（保留中のON遅延はキャンセルされる）
- 12V電源には一切触れない。

- Transmit button ON: `GET /tx?state=on` → PTT (GPIO27) ON after the configured delay (`ptt_delay_ms`, default 50 ms)
- Transmit button OFF: `GET /tx?state=off` → PTT (GPIO27) OFF immediately (a pending ON delay is cancelled)
- The 12 V power is never touched.

### 3.2 12V電源（Shonan_lite-PI4アプリ起動/終了連動） / 12 V Power (linked to Shonan_lite-PI4 app start/exit)

- アプリ起動から5秒後: `GET /ch?idx=0&state=on` → 設定した遅延時間(`power_delay_sec`、デフォルト3秒)後にPOWER(GPIO26) ON
- アプリ終了時: 先に `GET /ch?idx=0&state=off` → POWER(GPIO26) 即時OFF（保留中のON遅延はキャンセルされる）、その後3秒待ってからアプリを終了

- 5 seconds after app start: `GET /ch?idx=0&state=on` → POWER (GPIO26) ON after the configured delay (`power_delay_sec`, default 3 seconds)
- At app exit: first `GET /ch?idx=0&state=off` → POWER (GPIO26) OFF immediately (a pending ON delay is cancelled), then the app exits after waiting 3 seconds

### 3.3 設計意図 / Design Intent

- LNA駆動回路が実機に存在しないため、送受信切替に伴う保護シーケンス（LNA切り離し等）は不要と判断し廃止した。
- 12V電源はPA等の外部機器向けの主電源に相当するため、TX/RXの都度切り替えるのではなく、アプリの起動/終了という粒度の大きいタイミングでON/OFFする運用とする。
- PTTのみを送信ボタンに連動させることで、TX切替の応答を遅延なく行う。
- ON要求のみ設定した遅延時間を挟み、OFF要求は安全のため常に即時反映する（保留中のON遅延もOFF要求でキャンセルされる）。

- Since the actual hardware has no LNA drive circuit, the protective sequence accompanying TX/RX switching (such as disconnecting the LNA) was judged unnecessary and abolished.
- The 12 V power corresponds to the main power for external equipment such as a PA, so it is switched ON/OFF at coarse-grained timing (app start/exit) rather than on every TX/RX change.
- Linking only PTT to the transmit button makes TX switching respond without delay.
- Only ON requests are preceded by the configured delay; OFF requests always take effect immediately for safety (a pending ON delay is also cancelled by an OFF request).

---

## 4. ネットワーク・HTTP API仕様 / Network and HTTP API Specification

### 4.1 ネットワーク設定 / Network Settings

- 固定IPアドレス方式（初期値 `192.168.0.100`/24、ゲートウェイ `192.168.0.1`）。DHCPは使用しない
- IP/ゲートウェイ/サブネットはNVS(Preferences)に保存され、電源断後も保持される。`/config/network`（下記4.2）で変更可能で、保存後は自動再起動して新設定を反映する
- MACアドレスはスケッチ内で固定値を指定（同一LAN内で重複しないこと）

- Fixed IP address (default `192.168.0.100`/24, gateway `192.168.0.1`). DHCP is not used
- The IP/gateway/subnet are stored in NVS (Preferences) and retained after power loss. They can be changed with `/config/network` (see 4.2 below); after saving, the ESP32 restarts automatically to apply the new settings
- The MAC address is fixed in the sketch (it must not be duplicated on the same LAN)

### 4.2 API一覧 / API List

| エンドポイント<br>Endpoint | メソッド<br>Method | 説明<br>Description | レスポンス<br>Response |
|---|---|---|---|
| `/` | GET | ステータス確認用HTML（手動ON/OFFボタン付き）<br>HTML status page (with manual ON/OFF buttons) | HTML |
| `/tx?state=on` | GET | **PTT ON**（shonan-androidから呼び出し）<br>**PTT ON** (called from shonan-android) | `TX`（プレーンテキスト）<br>`TX` (plain text) |
| `/tx?state=off` | GET | **PTT OFF**（shonan-androidから呼び出し）<br>**PTT OFF** (called from shonan-android) | `RX`（プレーンテキスト）<br>`RX` (plain text) |
| `/toggle?ch=0..1` | GET | 個別チャンネル手動トグル（配線確認用デバッグ機能。0=POWER,1=PTT）<br>Manual toggle of an individual channel (debug feature for checking wiring; 0 = POWER, 1 = PTT) | `/` へリダイレクト<br>Redirect to `/` |
| `/ch?idx=0..1&state=on\|off` | GET | 個別チャンネル明示ON/OFF（0=POWER,1=PTT。Shonan_lite-PI4 GUI起動/終了時のGPIO26制御用）<br>Explicit ON/OFF of an individual channel (0 = POWER, 1 = PTT; used for GPIO26 control at Shonan_lite-PI4 GUI start/exit) | `ON`/`OFF`（プレーンテキスト）<br>`ON`/`OFF` (plain text) |
| `/api/status` | GET | 現在状態をJSONで取得<br>Get the current state as JSON | `{"power":bool,"ptt":bool,"tx_active":bool}` |
| `/config` | GET | 遅延時間・IP設定画面（HTML）<br>Delay time and IP settings page (HTML) | HTML |
| `/config/delay?power_delay_sec=..&ptt_delay_ms=..` | GET | POWER/PTTのON遅延時間を保存<br>Save the ON delay times for POWER/PTT | 設定画面へリダイレクト等<br>Redirect to the settings page, etc. |
| `/config/network?ip=..&gateway=..&subnet=..` | GET | 固定IPアドレスを保存し自動再起動<br>Save the fixed IP address and restart automatically | 設定画面へリダイレクト等<br>Redirect to the settings page, etc. |

### 4.3 呼び出し例 / Call Examples

```
送信開始時 / At TX start: GET http://<ESP32のIPアドレス / ESP32 IP address>/tx?state=on
送信終了時 / At TX end:   GET http://<ESP32のIPアドレス / ESP32 IP address>/tx?state=off
```

ESP32のIPアドレスは固定IP(初期値`192.168.0.100`、4.1参照)のため、shonan-android・Shonan_lite-PI4(pi4/gui)
いずれも設定画面で利用者が同じIPアドレスを入力・保持する運用とする。ESP32側のIPを`/config/network`で
変更した場合は、アプリ側の設定も合わせて変更すること（★DDNS/mDNS等による自動検出は本版では未実装）。

Since the ESP32 uses a fixed IP address (default `192.168.0.100`, see 4.1), the user enters and keeps the same IP address
on the settings screen of both shonan-android and Shonan_lite-PI4 (pi4/gui). If the ESP32's IP is changed with
`/config/network`, change the app settings accordingly (★automatic discovery via DDNS/mDNS, etc. is not implemented in
this revision).

### 4.4 Shonan_lite-PI4(pi4/gui)側の連携 / Integration on the Shonan_lite-PI4 (pi4/gui) Side

- 設定画面(`pi4/gui/screens/settings.py`)の「PA_Power/PTTコントローラ (ESP32)」欄で「ESP32 W5500を使用する」を
  ONにし、ESP32のIPアドレスを設定する。OFFまたは空欄の場合は連携自体を行わない（OFFにしてもIPアドレスは
  保持される。未接続環境でもTX/RXの動作に影響しない）。
- `pi4/gui/backend.py` の `TxController.start()` 冒頭で `/tx?state=on`、`stop()` 冒頭で
  `/tx?state=off` をGETする（PTTのみをON/OFFする）。タイムアウトは短く(1.5秒)設定し、
  ESP32が未接続/未応答でも例外を握りつぶしてTX本体の動作を妨げない（ログにのみ記録）。
- ESP32(MCU1)とPluto+の間に直接の通信経路はない。Pi4(pi4/gui)がPluto+へはSSHで`/www/settings.txt`を
  書き込み(`_push_pluto_settings()`)、ESP32へはHTTPで`/tx?state=`(`_send_ptt_request()`)を送る、
  それぞれ独立した構成であり、ESP32はPi4からのTX開始/終了通知のみを扱う。
- 上記PTT切替とは別に、Pi4アプリ(`pi4/gui/main.py`)自体の起動/終了に連動して
  GPIO26(POWERチャンネル、idx=0)を明示的に制御する（`_send_ptt_channel_state()`、
  `/ch?idx=0&state=on|off`を使用）。
  - アプリ起動から5秒後にGPIO26をON(Langstone V2Modifyへの切替時・起動メニューでLangstoneを選んだ時もON)
  - アプリ終了時、先にGPIO26をOFFにしてから3秒待って実際に終了
  - 12V電源の制御にPi4本体(Raspberry Pi4)のGPIOは使用しない。あくまでMCU1側のGPIO26を
    ネットワーク経由で制御する。
- ★ESP32 W5500(本コントローラ)は必須ではない。Pi4本体のGPIO21(40番ピン、GNDは39番ピン)が
  送信中HIGH(3.3V)・受信中LOWになるため、これをトランジスタ/リレードライバ等でバッファすれば
  ESP32なしでもPA・LNAの送受信切替ができる(Langstone V2ModifyのTx Outputと同じピン。Shonan_Lite側は
  `pi4/gui/backend.py`の`_set_pi_tx_gpio()`で`pinctrl`により出力)。ESP32を併用する場合は
  本コントローラのPTT(J6)も同時に切り替わる。12V電源のON/OFFは本コントローラが必要。

- In the "PA_Power/PTT Controller (ESP32)" field of the settings screen (`pi4/gui/screens/settings.py`), turn ON
  "Use ESP32 W5500" and set the ESP32's IP address. When it is OFF or the address is empty, no integration is performed
  (the IP address is kept even when OFF; TX/RX operation is not affected even without a controller connected).
- `TxController.start()` in `pi4/gui/backend.py` sends GET `/tx?state=on` at its beginning and `stop()` sends
  `/tx?state=off` at its beginning (only PTT is switched ON/OFF). The timeout is short (1.5 seconds), and even if the
  ESP32 is not connected or does not respond, the exception is swallowed so that TX itself is not disturbed (it is only logged).
- There is no direct communication path between the ESP32 (MCU1) and the Pluto+. The Pi 4 (pi4/gui) writes `/www/settings.txt`
  on the Pluto+ via SSH (`_push_pluto_settings()`) and sends `/tx?state=` (`_send_ptt_request()`) to the ESP32 via HTTP,
  independently of each other; the ESP32 only handles the TX start/stop notifications from the Pi 4.
- Separately from the PTT switching above, GPIO26 (POWER channel, idx=0) is explicitly controlled in conjunction with
  starting/exiting the Pi 4 app (`pi4/gui/main.py`) itself (`_send_ptt_channel_state()`, using `/ch?idx=0&state=on|off`).
  - GPIO26 is turned ON 5 seconds after app start (also when switching to Langstone V2Modify and when Langstone is selected in the boot menu)
  - At app exit, GPIO26 is turned OFF first, and the app actually exits after waiting 3 seconds
  - The Pi 4's own (Raspberry Pi 4) GPIO is not used for controlling the 12 V power. Only GPIO26 on the MCU1 side is
    controlled over the network.
- ★The ESP32 W5500 (this controller) is not required. GPIO21 of the Pi 4 (pin 40; GND on pin 39) is HIGH (3.3 V) while
  transmitting and LOW while receiving, so by buffering it with a transistor/relay driver, etc., the PA and LNA can be
  switched between TX and RX without the ESP32 (the same pin as Langstone V2Modify's Tx Output; on the Shonan_Lite side it is
  driven with `pinctrl` by `_set_pi_tx_gpio()` in `pi4/gui/backend.py`). When the ESP32 is also used, this controller's
  PTT (J6) switches at the same time. This controller is required for switching the 12 V power ON/OFF.

---

## 5. 未確定・今後の課題 / Open Items and Future Work

- ★ 12V電源／PTTの実際の駆動回路との結合試験（Q1/Q3/Q5の実機動作確認）は未実施。
- ★ mDNS対応（`http://shonan-ptt.local/` 等）による自動検出は未実装（IPアドレスは固定IP方式で、アプリ側に手入力する）。運用上必要であれば追加検討。
- ★ shonan-androidアプリ側でのHTTPリクエスト送出実装は本スケッチのスコープ外。アプリ側の送信ボタンハンドラに追加が必要。
- 実機ESP32への書き込みは完了（2026-08-30、MAC: `70:4b:ca:7b:eb:94`）。ただしW5500・12V電源/PTT駆動回路を実際に接続した結合試験、Pi4(pi4/gui)側との通信確認は未実施。
- GPIO25(旧LNA)は物理的に未接続のまま。今後LNA制御が必要になった場合は、駆動回路の追加とスケッチ・本書の再改訂が必要。

- ★ Integration testing with the actual 12 V power/PTT drive circuits (checking Q1/Q3/Q5 on real hardware) has not been done.
- ★ Automatic discovery via mDNS (such as `http://shonan-ptt.local/`) is not implemented (the IP address uses the fixed-IP method and is entered manually in the app). To be considered if needed in operation.
- ★ Sending HTTP requests from the shonan-android app is outside the scope of this sketch. It must be added to the app's transmit button handler.
- Writing to the actual ESP32 is complete (2026-08-30, MAC: `70:4b:ca:7b:eb:94`). However, the integration test with the W5500 and the 12 V power/PTT drive circuits actually connected, and the communication check with the Pi 4 (pi4/gui) side, have not been done.
- GPIO25 (former LNA) remains physically unconnected. If LNA control becomes necessary in the future, a drive circuit must be added and the sketch and this document revised again.

---

## 6. 関連ファイル / Related Files

- スケッチ本体 / Sketch: `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
- 回路図 / Schematic: `hardware/W5500_PA_PTT_Control/kicad/w5500-esp32.kicad_sch`（KiCad原本 / KiCad original）／`hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_回路図.svg`（KiCadから書き出したSVG。旧Rev.1.0の手書き概略図は実機と内容が乖離していたため2026-08-30に廃止し、KiCad原本からの書き出しに置き換えた / SVG exported from KiCad. The hand-drawn outline schematic of the old Rev.1.0 diverged from the actual hardware, so it was abolished on 2026-08-30 and replaced with an export from the KiCad original）
- MCU1/J1/W5500ピン対応の詳細表 / Detailed MCU1/J1/W5500 pin mapping table: [`MCU1_J1_W5500_接続一覧.md`](MCU1_J1_W5500_接続一覧.md)
