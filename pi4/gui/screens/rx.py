"""Pi5版と同じ構成の受信画面。"""
from __future__ import annotations

import time

from PyQt5 import QtCore, QtGui, QtWidgets

from widgets import SettingsSubScreen, error_dialog
from i18n import tr


class RxScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("受信 / Receive", lambda: main_window.navigate_to("home"))
        self.header_bar.hide()
        self.main_window = main_window
        self.controller = main_window.rx_controller
        self._last_rate_packets = None
        self._last_rate_time = None
        self._bitrate_mbps = 0.0
        self._video_fullscreen = False
        self._tx_started_alongside_rx = False

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(10, 8, 10, 32)
        self.body_layout.setSpacing(6)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)
        self.body_layout.addLayout(top_row, 1)

        self.status_card = QtWidgets.QFrame()
        self.status_card.setFixedWidth(270)
        self.status_card.setStyleSheet(
            "QFrame { background-color: #0f1214; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        top_row.addWidget(self.status_card)
        status_layout = QtWidgets.QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(8)

        status_header = QtWidgets.QHBoxLayout()
        self.status_dot = QtWidgets.QLabel()
        self.status_dot.setFixedSize(12, 12)
        status_header.addWidget(self.status_dot)
        self.status_label = QtWidgets.QLabel(tr("受信停止中", "RX Stopped"))
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        status_header.addWidget(self.status_label)
        status_header.addStretch(1)
        self.lock_badge = QtWidgets.QLabel("LOCK")
        self.lock_badge.setStyleSheet(
            "background-color: #20a040; color: white; font-size: 10px;"
            " font-weight: bold; border-radius: 8px; padding: 2px 8px;")
        self.lock_badge.hide()
        status_header.addWidget(self.lock_badge)
        status_layout.addLayout(status_header)

        fields_grid = QtWidgets.QGridLayout()
        fields_grid.setHorizontalSpacing(16)
        fields_grid.setVerticalSpacing(6)
        fields_grid.setColumnStretch(0, 1)
        fields_grid.setColumnStretch(1, 1)
        self.freq_value = self._add_field(fields_grid, 0, 0, tr("周波数", "Frequency"))
        self.symbol_value = self._add_field(fields_grid, 0, 1, tr("シンボルレート", "Symbol Rate"))
        self.modulation_value = self._add_field(fields_grid, 1, 0, tr("変調方式", "Modulation"))
        self.fec_value = self._add_field(fields_grid, 1, 1, "FEC")
        status_layout.addLayout(fields_grid)

        divider = QtWidgets.QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #202427;")
        status_layout.addWidget(divider)

        stats_grid = QtWidgets.QGridLayout()
        stats_grid.setHorizontalSpacing(16)
        stats_grid.setVerticalSpacing(6)
        stats_grid.setColumnStretch(0, 1)
        stats_grid.setColumnStretch(1, 1)
        self.state_value = self._add_field(stats_grid, 0, 0, tr("状態", "State"))
        self.bitrate_value = self._add_field(stats_grid, 0, 1, tr("ビットレート", "Bitrate"))
        self.packets_value = self._add_field(stats_grid, 1, 0, tr("パケット/秒", "Packets/sec"))
        self.errors_value = self._add_field(stats_grid, 1, 1, tr("エラー", "Errors"))
        status_layout.addLayout(stats_grid)
        status_layout.addStretch(1)

        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        self.video_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.video_label.mousePressEvent = self._on_video_tap
        top_row.addWidget(self.video_label, 1)

        self.panel = QtWidgets.QFrame()
        self.panel.setFixedHeight(116)
        self.panel.setStyleSheet(
            "QFrame { background: transparent; color: white; }"
            "QLabel { color: white; background: transparent; }"
            "QSlider::groove:horizontal { height: 8px; background: #303437; border-radius: 4px; }"
            "QSlider::handle:horizontal { width: 20px; margin: -6px 0;"
            " background: #dddddd; border-radius: 10px; }"
            "QSlider::sub-page:horizontal { background: #1677ff; border-radius: 4px; }")
        self.body_layout.addWidget(self.panel)
        panel_layout = QtWidgets.QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)

        volume_row = QtWidgets.QHBoxLayout()
        volume_label = QtWidgets.QLabel(tr("音量", "Volume"))
        volume_label.setFixedWidth(60)
        volume_row.addWidget(volume_label)
        self.volume_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider, 1)
        panel_layout.addLayout(volume_row)

        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        self.start_stop_btn = QtWidgets.QPushButton(tr("受信開始", "Start RX"))
        self.start_stop_btn.setMinimumSize(120, 40)
        self.start_stop_btn.clicked.connect(self._on_start_stop)
        button_row.addWidget(self.start_stop_btn)
        self.tx_screen_btn = self._secondary_button(tr("送信画面へ", "Go to TX"))
        self.tx_screen_btn.clicked.connect(lambda: self.main_window.navigate_to("tx"))
        button_row.addWidget(self.tx_screen_btn)
        self.settings_btn = self._secondary_button(tr("設定", "Settings"))
        self.settings_btn.clicked.connect(lambda: self.main_window.navigate_to("settings"))
        button_row.addWidget(self.settings_btn)
        self.home_btn = self._secondary_button(tr("ホームへ戻る", "Back to Home"))
        self.home_btn.clicked.connect(lambda: self.main_window.navigate_to("home"))
        button_row.addWidget(self.home_btn)
        button_row.addStretch(1)
        panel_layout.addLayout(button_row)

        self.controller.status_updated.connect(self._on_status)
        self.controller.error.connect(self._on_error)
        self.controller.stopped.connect(self._on_stopped)
        self.controller.video_frame.connect(self._on_video_frame)

    @staticmethod
    def _add_field(grid, row: int, col: int, label: str) -> QtWidgets.QLabel:
        box = QtWidgets.QVBoxLayout()
        box.setSpacing(1)
        caption = QtWidgets.QLabel(label)
        caption.setStyleSheet("color: #9aa0a6; font-size: 13px;")
        box.addWidget(caption)
        value = QtWidgets.QLabel("---")
        value.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        box.addWidget(value)
        grid.addLayout(box, row, col)
        return value

    @staticmethod
    def _secondary_button(text: str) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setMinimumSize(100, 40)
        button.setStyleSheet(
            "QPushButton { background-color: #1d4388; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: bold; }"
            "QPushButton:pressed { background-color: #102a5c; }")
        return button

    def on_show(self) -> None:
        self.scroll_area.verticalScrollBar().setValue(0)
        settings = self.main_window.settings
        lo_hz = settings.effective_lo_hz()
        self.freq_value.setText(f"{lo_hz / 1000:.0f} kHz" if lo_hz else tr("未設定", "Not set"))
        self.symbol_value.setText(f"{settings.symbol_rate_msps * 1000:.0f} kS/s")
        self.modulation_value.setText(settings.modulation_scheme)
        self.fec_value.setText(settings.fec_rate)
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(round(settings.rx_volume * 100))
        self.volume_slider.blockSignals(False)
        self._sync_button_state()
        self._set_video_fullscreen(False)
        self._last_rate_packets = None
        self._last_rate_time = None
        self._bitrate_mbps = 0.0
        self._set_stats(False, 0, 0)

    def _on_volume_changed(self, value: int) -> None:
        self.main_window.settings.rx_volume = value / 100.0
        self.main_window.save_settings()
        self.controller.set_volume(value)

    def _sync_button_state(self, locked: bool = False) -> None:
        running = self.controller.is_running()
        self.status_dot.setStyleSheet(
            f"background-color: {'#20c020' if running else '#5a5a5a'}; border-radius: 6px;")
        self.lock_badge.setVisible(locked)
        if running:
            self.status_label.setText(tr("受信中", "Receiving"))
            self.start_stop_btn.setText(tr("受信停止", "Stop RX"))
            self.start_stop_btn.setStyleSheet(
                "QPushButton { background-color: #d02020; color: white; border: none;"
                " border-radius: 8px; padding: 4px 10px; font-size: 14px; font-weight: bold; }"
                "QPushButton:pressed { background-color: #901010; }")
        else:
            self.status_label.setText(tr("受信停止中", "RX Stopped"))
            self.start_stop_btn.setText(tr("受信開始", "Start RX"))
            self.start_stop_btn.setStyleSheet(
                "QPushButton { background-color: #1677ff; color: white; border: none;"
                " border-radius: 8px; padding: 4px 10px; font-size: 14px; font-weight: bold; }"
                "QPushButton:pressed { background-color: #102a5c; }")

    def _on_start_stop(self) -> None:
        if self.controller.is_running():
            self.controller.stop()
        else:
            settings = self.main_window.settings
            self.controller.start(settings)
        self._sync_button_state()

    def _on_status(self, status: dict) -> None:
        locked = status["locked"]
        packets = status.get("packets", 0)
        now = time.monotonic()
        if self._last_rate_packets is not None and self._last_rate_time is not None:
            elapsed = now - self._last_rate_time
            packet_delta = packets - self._last_rate_packets
            if elapsed > 0 and packet_delta >= 0:
                self._bitrate_mbps = packet_delta * 188 * 8 / elapsed / 1_000_000
        self._last_rate_packets = packets
        self._last_rate_time = now
        self._sync_button_state(locked)
        self._set_stats(locked, packets, status.get("errors", 0))

    def _set_stats(self, locked: bool, packets: int, errors: int) -> None:
        self.state_value.setText(tr("接続中", "Connected") if locked else tr("切断中", "Disconnected"))
        error_text = str(errors) if errors < 1_000_000 else "999999+"
        self.bitrate_value.setText(f"{self._bitrate_mbps:.2f} Mbps")
        self.packets_value.setText(str(packets))
        self.errors_value.setText(error_text)

    def _on_error(self, message: str) -> None:
        error_dialog(self, tr("受信エラー", "RX Error"), message)
        self._sync_button_state()

    def _on_stopped(self) -> None:
        if self._tx_started_alongside_rx:
            self._tx_started_alongside_rx = False
            self.main_window.tx_controller.stop()
        self.video_label.clear()
        self._sync_button_state()
        self._set_stats(False, 0, 0)
        self._last_rate_packets = None
        self._last_rate_time = None
        self._bitrate_mbps = 0.0

    def _on_video_frame(self, data: bytes, width: int, height: int) -> None:
        image = QtGui.QImage(data, width, height, width * 3, QtGui.QImage.Format_RGB888).copy()
        pixmap = QtGui.QPixmap.fromImage(image).scaled(
            self.video_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    def _on_video_tap(self, _event) -> None:
        self._set_video_fullscreen(not self._video_fullscreen)

    def _set_video_fullscreen(self, enabled: bool) -> None:
        self._video_fullscreen = enabled
        self.status_card.setVisible(not enabled)
        self.panel.setVisible(not enabled)


def create(main_window) -> QtWidgets.QWidget:
    return RxScreen(main_window)
