"""Pi5版と同じ構成の送信画面。"""
from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from widgets import SettingsSubScreen, error_dialog


class TxScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("送信 / Transmit", lambda: main_window.navigate_to("home"))
        self.header_bar.hide()
        self.main_window = main_window
        self.controller = main_window.tx_controller
        self._rx_restart_pending = False
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(10, 8, 10, 16)
        self.body_layout.setSpacing(6)

        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)
        self.body_layout.addLayout(top_row, 1)
        self.preview_label = QtWidgets.QLabel("送信開始前")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: black; border-radius: 10px; color: #999999;")
        self.preview_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        # テストパターンは枠の大きさが確定・変化した時点で縮小し直す(eventFilter参照)。
        self.preview_label.installEventFilter(self)
        top_row.addWidget(self.preview_label, 1)

        self.status_card = QtWidgets.QFrame()
        self.status_card.setFixedWidth(270)
        self.status_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        top_row.addWidget(self.status_card)
        status_layout = QtWidgets.QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(8)
        header = QtWidgets.QHBoxLayout()
        self.status_dot = QtWidgets.QLabel()
        self.status_dot.setFixedSize(12, 12)
        header.addWidget(self.status_dot)
        self.status_label = QtWidgets.QLabel("送信停止中")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(self.status_label)
        header.addStretch(1)
        self.on_air_badge = QtWidgets.QLabel("ON AIR")
        self.on_air_badge.setStyleSheet(
            "background-color: #d02020; color: white; font-size: 10px;"
            " font-weight: bold; border-radius: 8px; padding: 2px 8px;")
        self.on_air_badge.hide()
        header.addWidget(self.on_air_badge)
        status_layout.addLayout(header)

        fields = QtWidgets.QGridLayout()
        fields.setHorizontalSpacing(16)
        fields.setVerticalSpacing(6)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        self.freq_value = self._add_field(fields, 0, 0, "周波数")
        self.symbol_value = self._add_field(fields, 0, 1, "シンボルレート")
        self.modulation_value = self._add_field(fields, 1, 0, "変調方式")
        self.fec_value = self._add_field(fields, 1, 1, "FEC")
        status_layout.addLayout(fields)
        divider = QtWidgets.QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #303538;")
        status_layout.addWidget(divider)
        stats = QtWidgets.QGridLayout()
        stats.setHorizontalSpacing(16)
        stats.setVerticalSpacing(6)
        stats.setColumnStretch(0, 1)
        stats.setColumnStretch(1, 1)
        self.power_value = self._add_field(stats, 0, 0, "出力減衰")
        self.packets_value = self._add_field(stats, 0, 1, "パケット数")
        self.frames_value = self._add_field(stats, 1, 0, "フレーム数")
        self.connection_value = self._add_field(stats, 1, 1, "接続")
        status_layout.addLayout(stats)
        status_layout.addStretch(1)

        self.panel = QtWidgets.QFrame()
        self.panel.setFixedHeight(68)
        self.panel.setStyleSheet("QFrame { background: transparent; color: white; }")
        self.body_layout.addWidget(self.panel)
        panel_layout = QtWidgets.QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.start_stop_btn = QtWidgets.QPushButton("送信開始")
        self.start_stop_btn.setMinimumSize(120, 40)
        self.start_stop_btn.clicked.connect(self._on_start_stop)
        buttons.addWidget(self.start_stop_btn)
        self.receive_screen_btn = self._secondary_button("受信画面へ")
        self.receive_screen_btn.clicked.connect(lambda: self.main_window.navigate_to("rx"))
        buttons.addWidget(self.receive_screen_btn)
        self.settings_btn = self._secondary_button("設定")
        self.settings_btn.clicked.connect(lambda: self.main_window.navigate_to("settings"))
        buttons.addWidget(self.settings_btn)
        self.home_btn = self._secondary_button("ホームへ戻る")
        self.home_btn.clicked.connect(lambda: self.main_window.navigate_to("home"))
        buttons.addWidget(self.home_btn)
        buttons.addStretch(1)
        panel_layout.addLayout(buttons)

        self.controller.status_updated.connect(self._on_status)
        self.controller.error.connect(self._on_error)
        self.controller.stopped.connect(self._on_stopped)
        self.controller.log_line.connect(self._on_log)
        self.controller.video_frame.connect(self._on_video_frame)

    @staticmethod
    def _add_field(grid, row, col, label):
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
    def _secondary_button(text):
        button = QtWidgets.QPushButton(text)
        button.setMinimumSize(100, 40)
        button.setStyleSheet(
            "QPushButton { background-color: #303538; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: bold; }"
            "QPushButton:pressed { background-color: #222222; }")
        return button

    def on_show(self):
        settings = self.main_window.settings
        lo_hz = settings.effective_lo_hz()
        self.freq_value.setText(f"{lo_hz / 1000:.0f} kHz" if lo_hz else "未設定")
        self.symbol_value.setText(f"{settings.symbol_rate_msps * 1000:.0f} kS/s")
        self.modulation_value.setText(settings.modulation_scheme)
        self.fec_value.setText(settings.fec_rate)
        self.power_value.setText(f"{settings.tx_power_db:.0f} dB")
        self.packets_value.setText("0")
        self.frames_value.setText("0")
        self._sync_button_state()
        if self._uses_colorbar():
            self.preview_label.setPixmap(self._colorbar_pixmap())
            # ★on_show()の時点ではレイアウト前で枠の大きさが確定しておらず、古い大きさで
            # 拡大するとテストパターンの四隅が切れる。レイアウト後にもう一度縮小する。
            QtCore.QTimer.singleShot(0, self._refresh_colorbar_preview)
        elif not self.controller.is_running():
            self.preview_label.setText("送信開始前")

    def _uses_colorbar(self) -> bool:
        settings = self.main_window.settings
        return settings.use_color_bar_source or settings.video_source == "colorbar"

    def _refresh_colorbar_preview(self) -> None:
        if self._uses_colorbar():
            self.preview_label.setPixmap(self._colorbar_pixmap())

    def eventFilter(self, obj, event):
        if obj is self.preview_label and event.type() == QtCore.QEvent.Resize:
            self._refresh_colorbar_preview()
        return super().eventFilter(obj, event)

    def _colorbar_pixmap(self) -> QtGui.QPixmap:
        asset = Path(__file__).resolve().parents[1] / "assets" / "test_pattern.png"
        pixmap = QtGui.QPixmap(str(asset))
        if not pixmap.isNull():
            return pixmap.scaled(
                self.preview_label.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        return QtGui.QPixmap()

    def _sync_button_state(self):
        running = self.controller.is_running()
        self.status_dot.setStyleSheet(
            f"background-color: {'#d02020' if running else '#5a5a5a'}; border-radius: 6px;")
        self.on_air_badge.setVisible(running)
        self.status_label.setText("送信中" if running else "送信停止中")
        self.start_stop_btn.setText("送信停止" if running else "送信開始")
        color = "#d02020" if running else "#1677ff"
        pressed = "#901010" if running else "#0b55c7"
        self.start_stop_btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; border: none;"
            f" border-radius: 8px; padding: 4px 10px; font-size: 14px; font-weight: bold; }}"
            f"QPushButton:pressed {{ background-color: {pressed}; }}")

    def _on_start_stop(self):
        if self.controller.is_running():
            self.controller.stop()
        elif self.main_window.settings.simultaneous_tx_rx_test and self.main_window.rx_controller.is_running():
            self._rx_restart_pending = True
            self.main_window.rx_controller.stop()
            self.start_stop_btn.setEnabled(False)
            QtCore.QTimer.singleShot(100, self._start_tx_after_rx_stop)
        else:
            self.controller.start(self.main_window.settings)
        self._sync_button_state()

    def _start_tx_after_rx_stop(self):
        if not self._rx_restart_pending:
            return
        if self.main_window.rx_controller.is_running():
            QtCore.QTimer.singleShot(100, self._start_tx_after_rx_stop)
            return
        self._rx_restart_pending = False
        self.controller.start(self.main_window.settings)
        QtCore.QTimer.singleShot(300, self._restart_rx_after_tx_start)

    def _restart_rx_after_tx_start(self):
        if self.main_window.settings.simultaneous_tx_rx_test and not self.main_window.rx_controller.is_running():
            self.main_window.rx_controller.start(self.main_window.settings)
        self.start_stop_btn.setEnabled(True)
        self._sync_button_state()

    def _on_status(self, status):
        self.connection_value.setText("接続中" if status.get("connected", False) else "未接続")
        self.packets_value.setText(str(status.get("packets", 0)))
        self.frames_value.setText(str(status.get("frames", 0)))
        self._sync_button_state()

    def _on_error(self, message):
        error_dialog(self, "送信エラー", message)
        self._sync_button_state()

    def _on_stopped(self):
        self._sync_button_state()
        self.packets_value.setText("0")
        self.frames_value.setText("0")
        settings = self.main_window.settings
        if not (settings.use_color_bar_source or settings.video_source == "colorbar"):
            self.preview_label.setPixmap(QtGui.QPixmap())
            self.preview_label.setText("送信開始前")

    def _on_log(self, line):
        # 統計はstatus_updated(_on_status)で更新する。
        pass

    def _on_video_frame(self, data: bytes, width: int, height: int) -> None:
        image = QtGui.QImage(data, width, height, width * 3, QtGui.QImage.Format_RGB888).copy()
        pixmap = QtGui.QPixmap.fromImage(image).scaled(
            self.preview_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.preview_label.setPixmap(pixmap)


def create(main_window):
    return TxScreen(main_window)
