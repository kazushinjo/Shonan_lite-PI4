"""RXゲイン画面。モック準拠のゲイン調整+信号レベル表示。"""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from widgets import SettingsSubScreen
from i18n import tr


class RxGainScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("RXゲイン / RX Gain", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        # --- 左カラム: RXゲイン調整 ---
        gain_card = QtWidgets.QFrame()
        gain_card.setStyleSheet("QFrame { background: #0f1214; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        gain_layout = QtWidgets.QVBoxLayout(gain_card)
        gain_layout.setContentsMargins(16, 12, 16, 12)
        gain_layout.setSpacing(8)
        title_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel(tr("RXゲイン調整", "RX Gain Adjustment"))
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        auto_label = QtWidgets.QLabel(tr("自動調整", "Auto"))
        auto_label.setStyleSheet("font-size: 12px; color: #cccccc;")
        title_row.addWidget(auto_label)
        self.agc_checkbox = QtWidgets.QCheckBox("ON")
        self.agc_checkbox.setChecked(True)
        self.agc_checkbox.setStyleSheet("QCheckBox { color: white; font-weight: bold; min-height: 28px; } QCheckBox::indicator { width: 38px; height: 22px; border-radius: 11px; background: #465057; } QCheckBox::indicator:checked { background: #0c9bc0; }")
        self.agc_checkbox.toggled.connect(self._on_agc_toggled)
        title_row.addWidget(self.agc_checkbox)
        gain_layout.addLayout(title_row)

        scale = QtWidgets.QHBoxLayout()
        for text in ("0", "20", "40", "60", "80", "100"):
            label = QtWidgets.QLabel(text)
            label.setStyleSheet("font-size: 10px; color: #9aa0a6;")
            scale.addWidget(label)
        gain_layout.addLayout(scale)

        self.gain_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.gain_slider.setRange(0, 73)
        self.gain_slider.setMinimumHeight(32)
        self.gain_slider.setStyleSheet("QSlider::groove:horizontal { height: 5px; background: #69747a; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0c9bc0; border-radius: 2px; } QSlider::handle:horizontal { width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; background: #0c9bc0; }")
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        gain_layout.addWidget(self.gain_slider)

        self.gain_label = QtWidgets.QLabel("60 dB")
        self.gain_label.setAlignment(QtCore.Qt.AlignCenter)
        self.gain_label.setStyleSheet("font-size: 20px; color: white;")
        gain_layout.addWidget(self.gain_label)
        gain_layout.addStretch(1)
        columns.addWidget(gain_card, 1)

        # --- 右カラム: 信号レベル ---
        level_card = QtWidgets.QFrame()
        level_card.setStyleSheet("QFrame { background: #0f1214; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        level_layout = QtWidgets.QVBoxLayout(level_card)
        level_layout.setContentsMargins(16, 12, 16, 12)
        level_layout.setSpacing(8)
        level_title = QtWidgets.QLabel(tr("信号レベル", "Signal Level"))
        level_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        level_layout.addWidget(level_title)
        self.level_value = QtWidgets.QLabel("72 %")
        self.level_value.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        level_layout.addWidget(self.level_value)
        self.level_bar = QtWidgets.QProgressBar()
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(72)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(12)
        self.level_bar.setStyleSheet("QProgressBar { background: #30383c; border: none; border-radius: 6px; } QProgressBar::chunk { background: #36b47a; border-radius: 6px; }")
        level_layout.addWidget(self.level_bar)
        level_layout.addStretch(1)
        columns.addWidget(level_card, 1)

    def on_show(self) -> None:
        settings = self.main_window.settings
        self.agc_checkbox.setChecked(settings.rx_agc_enabled)
        self.gain_slider.setValue(settings.rx_gain_db)
        self._update_visibility()

    def _on_agc_toggled(self, checked: bool) -> None:
        self.main_window.settings.rx_agc_enabled = checked
        self.main_window.save_settings()
        self._update_visibility()

    def _on_gain_changed(self, value: int) -> None:
        self.gain_label.setText(f"{value} dB")
        self.main_window.settings.rx_gain_db = value
        self.main_window.save_settings()

    def _update_visibility(self) -> None:
        self.gain_slider.setEnabled(not self.agc_checkbox.isChecked())


def create(main_window) -> QtWidgets.QWidget:
    return RxGainScreen(main_window)
