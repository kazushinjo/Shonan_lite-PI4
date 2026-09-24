"""目次ジャンプと全文検索を備えた操作説明Help画面。"""
from __future__ import annotations

from PyQt5 import QtWidgets

from i18n import is_english
from manual_content import MANUAL_SECTIONS
from widgets import SettingsSubScreen


MANUAL_SECTIONS_EN = [
    ("1. Overview", [
        ("What this app does", "Shonan_Lite is a DVB-S2 DATV transmitter, receiver, and RF loopback test tool for ADALM-Pluto."),
        ("Home screen", "Use the cards for Transmit, Receive, Frequency, RSSI Measurement, Symbol Rate, FEC, Modulation, Video Source, Stream Output, RX Gain, TX Power, Settings, Diagnostic, Help, App Restart, Power Off, Langstone, Presets, and Pluto Power. Every card shows its icon and name in the same layout; the Frequency card also shows the current frequency."),
        ("Common operation", "Tap a card or button to open it. Use Back to Home to return. Stop transmit and receive before changing operating parameters."),
    ]),
    ("2. Startup and shutdown", [
        ("Before startup", "Power on Pluto and connect it to Pi 4 over Ethernet. Set the Pluto address for your network."),
        ("Startup sequence", "The startup menu selects Shonan_Lite or Langstone. Shonan_Lite restarts Pluto, checks the connection, and reapplies settings before showing Home. If confirmation takes over 20 seconds, it continues to Home."),
        ("Shutdown", "Stop transmit and receive, then use Power Off from Home."),
        ("RF safety", "Never connect TX directly to RX. Use TX → external attenuator of at least 40 dB → RX."),
    ]),
    ("3. Operating parameters", [
        ("Standard example", "Frequency 437.000 MHz, symbol rate 500 kS/s, QPSK, FEC 3/5, and Pilot ON. TX and RX must use the same values."),
        ("Settings", "Open Settings, choose the display language (Japanese/English), and enter the Pluto IP address under Destination (Pluto Tx); the UDP-TS port is fixed at 8282. Enter the PA_Power/PTT controller (ESP32) IP address only if you use one."),
        ("Frequency", "Enter the agreed frequency and press OK. Confirm that the Home card shows the same value."),
        ("Symbol Rate", "Choose or enter the agreed symbol rate. The standard example is 500 kS/s."),
        ("Modulation and FEC", "Select the same modulation and FEC as the other station. Modulation is QPSK or 8PSK, and the FEC choices are limited to working combinations (QPSK: 1/2, 3/5, 8/9; 8PSK: 3/5, 8/9). QPSK and FEC 3/5 are the standard example."),
        ("Video Source", "Choose Camera for live video, Test Pattern for diagnostics, or File to send a still image (png/jpg/jpeg/bmp); the preview on the right shows the selected source. The camera is captured at 1280x720 (MJPEG at 30 fps when supported; cameras without 1280x720 use their default size), and in dim light the camera may lower its frame rate. With Camera, Capture saves a 1920x1080 JPG to Pictures/Shonan_Lite (not while transmitting), and File opens that folder. The Callsign and Note fields are burned into camera and image video with the date and time; choose their font size and color next to each field. The transmitted video is fixed at Full HD (1920x1080) with black bars when the aspect ratio differs. Only video is transmitted (No Audio)."),
        ("Stream Output", "Enter the Pluto IP address in Pluto URI, or press Detect to find the Pluto on the same LAN automatically. The destination port is fixed at 8282 on the Pluto. Change the RX TS port and Status port only if needed."),
        ("RX Gain and TX Power", "Use AGC or set RX gain manually. The standard test gain is 60 dB. TX Power sets the output attenuation: 0 dB is maximum output, and the value is shown as TX Attenuation (dB) on the Transmit screen."),
        ("On-device demodulation", "ON automatically enables TX/RX simultaneous operation, but starting RX does not automatically start TX. Turning it ON first asks you to confirm that an attenuator of 40 dB or more is connected between the Pluto TX and RX ports. OFF keeps TX and RX exclusive."),
        ("Final check", "Read every Home card and compare frequency, symbol rate, modulation, FEC, source, RX gain, and TX power with the other station."),
    ]),
    ("4. Presets", [
        ("Apply", "Open Presets and select one of five entries. The values are applied to the app and Pluto; transmit and receive do not start automatically."),
        ("Register or edit", "Set values manually in the individual screens, return to Presets, press Save / Edit, and enter the preset name with the keyboard."),
        ("Delete", "Press Delete on the selected row. Edit and delete while transmit and receive are stopped."),
    ]),
    ("5. Transmit", [
        ("Start", "Open Transmit, check the preview and parameters, and press Start Transmit. Opening the screen does not start transmission."),
        ("While transmitting", "Check the preview, frequency, symbol rate, modulation, FEC, and TX attenuation (dB). Packets is the total number of UDP packets sent to the Pluto and Frames is the number of encoded video frames; both keep increasing while transmitting and return to 0 when stopped. Connection shows Connected while the stream is being sent to the Pluto."),
        ("Stop", "Press Stop Transmit before changing settings or wiring."),
    ]),
    ("6. Receive", [
        ("Start", "Match frequency, symbol rate, modulation, FEC, and Pilot with the transmitting station, then press Start Receive."),
        ("Check", "LOCK, SOF, packets, bitrate, errors, and the video image should be monitored. SOF and packets must continue to increase."),
        ("No video", "First check LOCK and packets, then check video source, H.264 encoding, transmitter state, test pattern, and wiring."),
        ("Stop", "Press Stop Receive when finished."),
    ]),
    ("7. Normal operation", [
        ("Station-to-station procedure", "Agree on all parameters, configure each screen in order, compare Home cards, start RX or TX as required, and verify LOCK, SOF, packets, errors, and video."),
        ("RSSI Measurement", "RSSI Measurement scans ±5/±10/±20 MHz around the center frequency (from the Frequency screen) and graphs the received level; a smaller RSSI value means a stronger signal. Choose Repeat or Once, and adjust RX gain (AGC/manual) on the right. With on-device demodulation OFF (normal operation) it does not transmit and measures the other station. With it ON (a test feature) your station also transmits the test pattern automatically and measures its own signal; always use an attenuator of 40 dB or more."),
        ("TX/RX switching", "When TX starts while RX is active, the app performs RX stop → TX configuration → TX start → RX restart."),
    ]),
    ("8. TX/RX and RF loopback test", [
        ("Test values", "437.000 MHz, 500 kS/s, QPSK, FEC 3/5, Long Frame, roll-off 0.35, RX gain 60 dB, Test Pattern, Pilot ON, on-device demodulation ON, and RF loopback ON."),
        ("Important distinction", "On-device demodulation permits simultaneous TX/RX in one Pluto. RF loopback describes the physical attenuated RF path; it is not enabled by on-device demodulation alone."),
        ("Pass criteria", "LOCK is established, SOF and packet counts increase continuously, errors remain stable, and the test pattern is displayed."),
    ]),
    ("9. Langstone", [
        ("Switching", "Select Langstone from the startup menu or Home. Only one application uses Pluto at a time."),
        ("Return", "Use GOTO SHONAN_LITE in Langstone to stop it and return to Shonan_Lite."),
    ]),
    ("10. Help, diagnostics, and restart", [
        ("Help", "Use the table of contents or search field to find an operating procedure."),
        ("Diagnostic", "Stop TX and RX, then press Full Test. It restarts the Pluto and checks four items in order: Pluto SDR connection (IIO context), TX test (8 s of continuous output), RX test (8 s of continuous reception), and temperature sensor (Pi 4 CPU temperature), then shows an overall TX/RX result. TX and RX are stopped automatically at the end. Camera + Audio Diagnostic checks that the USB camera video and its microphone audio can actually be captured and sent. The result does not guarantee antenna or RF performance."),
        ("App Restart", "Stop TX/RX first. App Restart restarts Pluto, checks recovery, and reapplies saved settings in order."),
    ]),
    ("11. Troubleshooting", [
        ("Cannot transmit", "Check Pluto IP, frequency, video source, TX power, and that Start Transmit was pressed."),
        ("Cannot receive", "Match all five RF parameters and Pilot, confirm TX is active, and check attenuator, wiring, and RX gain."),
        ("SOF does not increase", "Recheck Pluto settings, frequency, symbol rate, modulation, FEC, Pilot, RX gain, TX power, and attenuation."),
        ("Cannot connect to Pluto", "Check power, IP address, and Ethernet. Wait for configuration reapplication after a restart."),
    ]),
    ("12. Pluto and connection information", [
        ("Firmware", "Use the F5OEO DATV custom firmware on an ADALM-Pluto. Pluto settings must match the app."),
        ("Pi 4", "Host name: DVB-S2-PI4. Configure the IP address and SSH destination for the operating environment."),
        ("Standard test", "437.000 MHz, 500 kS/s, QPSK, FEC 3/5, Test Pattern, and RX gain 60 dB."),
    ]),
    ("13. Notes and validation scope", [
        ("Validation", "This guide is based on actual equipment checks. Bugs may still exist depending on Pluto, RF wiring, power, network, and video equipment combinations."),
        ("Credit", "Receiver method and original system design: Shinji Yamazaki (JE1BTA). Receiver stabilization and application development: Kazuichi Shinjo."),
    ]),
]


class ManualScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("操作説明 / Help", lambda: main_window.navigate_to("home"))
        sections = MANUAL_SECTIONS_EN if is_english(main_window.settings) else MANUAL_SECTIONS

        self.body_layout.addWidget(QtWidgets.QLabel("目次 / Table of Contents"))
        self.toc_combo = QtWidgets.QComboBox()
        self.toc_combo.setMinimumHeight(48)
        self.toc_combo.addItem("章を選択してください")
        for title, _items in sections:
            self.toc_combo.addItem(title)
        self.toc_combo.currentIndexChanged.connect(self._jump_to_section)
        self.body_layout.addWidget(self.toc_combo)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("操作・設定・エラーを検索...")
        self.search_edit.setMinimumHeight(48)
        self.search_edit.textChanged.connect(self._on_search)
        self.body_layout.addWidget(self.search_edit)

        self._section_widgets = []
        for title, items in sections:
            box = QtWidgets.QGroupBox(title)
            layout = QtWidgets.QVBoxLayout(box)
            searchable = [title]
            for subtitle, text in items:
                heading = QtWidgets.QLabel(subtitle)
                heading.setStyleSheet("font-weight: bold; color: #8fb3ff;")
                detail = QtWidgets.QLabel(text)
                detail.setWordWrap(True)
                detail.setTextInteractionFlags(detail.textInteractionFlags())
                layout.addWidget(heading)
                layout.addWidget(detail)
                searchable.extend((subtitle, text))
            self.body_layout.addWidget(box)
            self._section_widgets.append((" ".join(searchable).lower(), box))

    def _jump_to_section(self, index: int) -> None:
        if index <= 0:
            return
        widget = self._section_widgets[index - 1][1]
        widget.setVisible(True)
        self.scroll_area.ensureWidgetVisible(widget, 0, 8)

    def _on_search(self, text: str) -> None:
        needle = text.strip().lower()
        for haystack, widget in self._section_widgets:
            widget.setVisible(not needle or needle in haystack)


def create(main_window) -> QtWidgets.QWidget:
    return ManualScreen(main_window)
