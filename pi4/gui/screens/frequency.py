"""周波数設定画面。Android版 ui/FrequencySettingsScreen.kt 相当。

レイアウトはモック(shonan-16screens-mock-v4.png)の周波数画面(左に周波数入力、
右にバンド選択)を踏襲する。配色は既存のダークテーマを維持する。
"""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from settings_store import BAND_PROFILES
from widgets import SettingsSubScreen

_CHIP_STYLE = (
    "QPushButton { background-color: #303538; color: white; border: none;"
    " border-radius: 8px; padding: 8px; font-size: 13px; font-weight: bold;"
    " min-height: 20px; text-align: left; }"
    "QPushButton:checked { background-color: #1677ff; }"
    "QPushButton:pressed { background-color: #222222; }"
)


class FrequencyScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("周波数 / Frequency", lambda: main_window.navigate_to("home"))
        self.main_window = main_window

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)
        self.body_layout.setSpacing(8)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        # --- 左カラム: 周波数入力 ---
        input_card = QtWidgets.QFrame()
        input_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        input_layout = QtWidgets.QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(6)
        input_title = QtWidgets.QLabel("周波数入力")
        input_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        input_layout.addWidget(input_title)

        # モックに合わせ、入力欄の直下にテンキーを常設する。
        self.freq_edit = QtWidgets.QLineEdit()
        self.freq_edit.setAlignment(QtCore.Qt.AlignRight)
        self.freq_edit.setStyleSheet(
            "background-color: #0a0a0a; color: white; border: 1px solid #4b5357;"
            " border-radius: 8px; font-size: 30px; font-weight: bold; padding: 6px 12px;")
        self.freq_edit.setMinimumHeight(56)
        # eglfs環境ではOSのソフトキーボードを出さず、画面内テンキーで入力する。
        self.freq_edit.setReadOnly(True)
        self.freq_edit.setAttribute(QtCore.Qt.WA_InputMethodEnabled, False)
        self.freq_edit.setInputMethodHints(QtCore.Qt.ImhNone)
        self.freq_edit.setFocusPolicy(QtCore.Qt.NoFocus)
        input_layout.addWidget(self.freq_edit)

        unit_label = QtWidgets.QLabel("kHz")
        unit_label.setAlignment(QtCore.Qt.AlignRight)
        unit_label.setStyleSheet("font-size: 14px; color: #9aa0a6; font-weight: bold;")
        input_layout.addWidget(unit_label)

        # グリッド自体がカードの余白を取り込んで行を拡大しないよう、
        # テンキー領域も固定高にする。
        keypad_container = QtWidgets.QWidget()
        keypad_container.setFixedSize(270, 178)
        keypad = QtWidgets.QGridLayout(keypad_container)
        keypad.setContentsMargins(0, 0, 0, 0)
        keypad.setSpacing(5)
        keypad_positions = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("DEL", 0, 3),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("C", 1, 3),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("0", 3, 1), ("OK", 3, 3),
        ]
        for label, row, column in keypad_positions:
            button = QtWidgets.QPushButton(label)
            # QGridLayoutの余白配分で縦に引き伸ばされないよう固定する。
            # 800x480 LCDではモックに合わせてコンパクトな4行テンキーにする。
            button.setFixedSize(60, 38)
            button.setStyleSheet(
                "QPushButton { background: #f5f7f8; color: #101820; border: 1px solid #c7d0d6;"
                " border-radius: 5px; font-size: 16px; font-weight: bold;"
                " min-width: 60px; max-width: 60px; min-height: 38px;"
                " max-height: 38px; padding: 0px; }"
                "QPushButton:pressed { background: #dbeaf2; }"
                + ("QPushButton { background: #0797bd; color: white; border: none; }"
                   if label == "OK" else ""))
            button.clicked.connect(lambda _checked=False, value=label: self._on_key(value))
            keypad.addWidget(button, row, column)
        input_layout.addWidget(keypad_container, 0, QtCore.Qt.AlignHCenter)
        input_layout.addStretch(1)

        self.current_label = QtWidgets.QLabel()
        self.current_label.setStyleSheet("font-size: 13px; color: #9aa0a6;")
        input_layout.addWidget(self.current_label)
        columns.addWidget(input_card, 1)

        # --- 右カラム: バンド選択 ---
        band_card = QtWidgets.QFrame()
        band_card.setFixedWidth(240)
        band_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        band_layout = QtWidgets.QVBoxLayout(band_card)
        band_layout.setContentsMargins(14, 12, 14, 12)
        band_layout.setSpacing(6)
        band_title = QtWidgets.QLabel("バンド選択")
        band_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        band_layout.addWidget(band_title)

        self._band_group = QtWidgets.QButtonGroup(self)
        self._band_buttons = {}
        for band, info in BAND_PROFILES.items():
            if info["lo_hz"] is None:
                continue
            mhz = info["lo_hz"] / 1_000_000
            chip = QtWidgets.QPushButton(f"{info['label_ja']}\n{mhz:g} MHz")
            chip.setCheckable(True)
            chip.setStyleSheet(_CHIP_STYLE)
            chip.toggled.connect(lambda checked, b=band: self._select_band(b) if checked else None)
            self._band_group.addButton(chip)
            self._band_buttons[band] = chip
            band_layout.addWidget(chip)
        band_layout.addStretch(1)
        columns.addWidget(band_card)

    def on_show(self) -> None:
        settings = self.main_window.settings
        lo_hz = settings.effective_lo_hz()
        if lo_hz is not None:
            self.freq_edit.setText(str(int(lo_hz / 1000)))
        self._update_current_label()
        if settings.use_custom_lo_frequency:
            self._uncheck_band()
        else:
            chip = self._band_buttons.get(settings.selected_band)
            if chip is not None:
                chip.setChecked(True)

    def _update_current_label(self) -> None:
        settings = self.main_window.settings
        lo_hz = settings.effective_lo_hz()
        text = f"{lo_hz / 1000:.0f} kHz" if lo_hz else "未設定"
        self.current_label.setText(f"現在の周波数: {text}")

    def _select_band(self, band: str) -> None:
        settings = self.main_window.settings
        settings.selected_band = band
        settings.use_custom_lo_frequency = False
        settings.custom_lo_frequency_hz = BAND_PROFILES[band]["lo_hz"]
        self.main_window.save_settings()
        self.freq_edit.setText(str(int(settings.custom_lo_frequency_hz / 1000)))
        self._update_current_label()

    def _on_key(self, value: str) -> None:
        """モックの画面内テンキーから周波数を入力・確定する。"""
        self._uncheck_band()
        if value == "DEL":
            cursor = self.freq_edit.cursorPosition()
            text = self.freq_edit.text()
            # DELはカーソル直前を消すバックスペースとして動作させる。
            if cursor > 0:
                self.freq_edit.setText(text[:cursor - 1] + text[cursor:])
                self.freq_edit.setCursorPosition(cursor - 1)
            return
        if value == "C":
            self.freq_edit.clear()
            return
        if value != "OK":
            text = self.freq_edit.text()
            cursor = self.freq_edit.cursorPosition()
            if len(text) < 8:
                self.freq_edit.setText(text[:cursor] + value + text[cursor:])
                self.freq_edit.setCursorPosition(cursor + 1)
            return
        if not self.freq_edit.text():
            return
        khz = int(self.freq_edit.text())
        settings = self.main_window.settings
        settings.use_custom_lo_frequency = True
        settings.custom_lo_frequency_hz = khz * 1000
        self.main_window.save_settings()
        self._update_current_label()

    def _uncheck_band(self) -> None:
        checked = self._band_group.checkedButton()
        if checked is not None:
            # ★排他的なQButtonGroupでは、現在チェック中のボタンをsetChecked(False)だけでは
            # 外せない(Qt側で無視される)。exclusiveを一時解除してから外す。
            self._band_group.setExclusive(False)
            checked.setChecked(False)
            self._band_group.setExclusive(True)


def create(main_window) -> QtWidgets.QWidget:
    return FrequencyScreen(main_window)
