"""TX出力画面。モック準拠のTX出力設定+出力レベルレイアウト。"""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets
from widgets import SettingsSubScreen


class TxPowerScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("TX出力 / TX Power", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)

        columns = QtWidgets.QHBoxLayout()
        self.body_layout.addLayout(columns, 1)

        setting_card = QtWidgets.QFrame()
        setting_card.setStyleSheet("QFrame { background: #191d1f; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        setting_layout = QtWidgets.QVBoxLayout(setting_card)
        setting_layout.setContentsMargins(16, 12, 16, 12)
        setting_layout.setSpacing(8)
        title_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("出力減衰量設定")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        setting_layout.addLayout(title_row)
        ticks = QtWidgets.QHBoxLayout()
        for text in ("-70", "-50", "-30", "-10", "0"):
            label = QtWidgets.QLabel(text)
            label.setStyleSheet("font-size: 10px; color: #9aa0a6;")
            ticks.addWidget(label)
        setting_layout.addLayout(ticks)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(-70, 0)
        self.slider.setMinimumHeight(32)
        self.slider.setStyleSheet("QSlider::groove:horizontal { height: 5px; background: #69747a; border-radius: 2px; } QSlider::sub-page:horizontal { background: #0c9bc0; border-radius: 2px; } QSlider::handle:horizontal { width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; background: #0c9bc0; }")
        self.slider.valueChanged.connect(self._on_changed)
        setting_layout.addWidget(self.slider)
        self.power_label = QtWidgets.QLabel("0 dB")
        self.power_label.setAlignment(QtCore.Qt.AlignCenter)
        self.power_label.setStyleSheet("font-size: 20px; color: white;")
        setting_layout.addWidget(self.power_label)
        setting_layout.addStretch(1)
        columns.addWidget(setting_card, 1)
        note = QtWidgets.QLabel("0 dB = 最大出力、値が小さいほど減衰します。")
        note.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        setting_layout.addWidget(note)

    def on_show(self) -> None:
        self.slider.setValue(int(self.main_window.settings.tx_power_db))

    def _on_changed(self, value: int) -> None:
        self.power_label.setText(f"{value} dB")
        self.main_window.settings.tx_power_db = value
        self.main_window.save_settings()


def create(main_window):
    return TxPowerScreen(main_window)
