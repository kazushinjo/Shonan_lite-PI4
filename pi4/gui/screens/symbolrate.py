"""シンボルレート画面。モックのプリセット一覧+カスタム設定レイアウト。"""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from widgets import SettingsSubScreen

_PRESETS_MSPS = (0.333, 0.5, 0.666, 1.0, 1.25, 1.666, 2.0)


def _ksps(msps: float) -> int:
    return round(msps * 1000)


class SymbolRateScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("シンボルレート / Symbol Rate", lambda: main_window.navigate_to("home"))
        self.main_window = main_window

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        # --- 左カラム: プリセット選択 ---
        preset_card = QtWidgets.QFrame()
        preset_card.setFixedWidth(220)
        preset_card.setStyleSheet(
            "QFrame { background-color: #0f1214; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        preset_layout = QtWidgets.QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(14, 12, 14, 12)
        preset_layout.setSpacing(5)
        preset_title = QtWidgets.QLabel("プリセット選択")
        preset_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        preset_layout.addWidget(preset_title)

        self._preset_group = QtWidgets.QButtonGroup(self)
        self._preset_buttons = {}
        for msps in _PRESETS_MSPS:
            button = QtWidgets.QPushButton(f"{_ksps(msps)} kS/s")
            button.setCheckable(True)
            button.setStyleSheet(
                "QPushButton { background: #303538; color: white; border: 1px solid #4b5357;"
                " border-radius: 6px; padding: 3px 8px; text-align: left; font-size: 13px;"
                " min-height: 30px; max-height: 30px; }"
                "QPushButton:checked { background: #1677ff; border-color: #1677ff; }"
                "QPushButton:pressed { background: #102a5c; }")
            button.setFixedHeight(30)
            button.clicked.connect(lambda _checked=False, value=msps: self._select(value))
            self._preset_group.addButton(button)
            self._preset_buttons[msps] = button
            preset_layout.addWidget(button)
        preset_layout.addStretch(1)
        columns.addWidget(preset_card)

        # --- 右カラム: カスタム設定 ---
        custom_card = QtWidgets.QFrame()
        custom_card.setStyleSheet(
            "QFrame { background-color: #0f1214; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        custom_layout = QtWidgets.QVBoxLayout(custom_card)
        custom_layout.setContentsMargins(16, 12, 16, 12)
        custom_layout.setSpacing(8)

        custom_title = QtWidgets.QLabel("カスタム設定")
        custom_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        custom_layout.addWidget(custom_title)

        rate_label = QtWidgets.QLabel()
        rate_label.setAlignment(QtCore.Qt.AlignCenter)
        rate_label.setMinimumHeight(45)
        rate_label.setStyleSheet("font-size: 30px; font-weight: bold; color: white;")
        self.rate_label = rate_label
        custom_layout.addWidget(rate_label)

        unit = QtWidgets.QLabel("シンボルレート (kS/s)")
        unit.setAlignment(QtCore.Qt.AlignCenter)
        unit.setStyleSheet("font-size: 12px; color: #9aa0a6;")
        custom_layout.addWidget(unit)

        keypad = QtWidgets.QGridLayout()
        keypad.setHorizontalSpacing(8)
        keypad.setVerticalSpacing(6)
        keypad.setAlignment(QtCore.Qt.AlignCenter)
        for text, row, column in [("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("DEL", 0, 3),
                                  ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("C", 1, 3),
                                  ("1", 2, 0), ("2", 2, 1), ("3", 2, 2), ("−", 2, 3),
                                  ("0", 3, 0), ("＋", 3, 1), ("OK", 3, 3)]:
            button = QtWidgets.QPushButton(text)
            button.setFixedSize(66, 38)
            button.setStyleSheet("QPushButton { background: #1d4388; color: white; border: 1px solid #2c5aa8; border-radius: 6px; font-size: 16px; font-weight: bold; min-width: 66px; max-width: 66px; min-height: 38px; max-height: 38px; padding: 0px; } QPushButton:pressed { background: #102a5c; }")
            if text == "−":
                button.clicked.connect(lambda: self._step(-1))
            elif text == "＋":
                button.clicked.connect(lambda: self._step(1))
            else:
                button.clicked.connect(lambda _checked=False, value=text: self._on_key(value))
            keypad.addWidget(button, row, column)
        custom_layout.addLayout(keypad)
        custom_layout.addStretch(1)

        current = QtWidgets.QLabel()
        current.setStyleSheet("font-size: 13px; color: #0c9bc0; font-weight: bold;")
        self.current_label = current
        custom_layout.addWidget(current)
        recommended = QtWidgets.QLabel("帯域幅の目安: 5.0 MHz")
        recommended.setStyleSheet("font-size: 12px; color: #9aa0a6;")
        custom_layout.addWidget(recommended)
        columns.addWidget(custom_card, 1)

    def on_show(self) -> None:
        self._refresh(self.main_window.settings.symbol_rate_msps)

    def _refresh(self, msps: float) -> None:
        ksps = _ksps(msps)
        self._pending_text = str(ksps)
        self.rate_label.setText(str(ksps))
        self.current_label.setText(f"現在の設定: {ksps} kS/s")
        for value, button in self._preset_buttons.items():
            button.setChecked(abs(value - msps) < 0.0005)

    def _select(self, msps: float) -> None:
        self.main_window.settings.symbol_rate_msps = msps
        self.main_window.save_settings()
        self._refresh(msps)

    def _step(self, direction: int) -> None:
        values = list(_PRESETS_MSPS)
        current = self.main_window.settings.symbol_rate_msps
        nearest = min(range(len(values)), key=lambda i: abs(values[i] - current))
        index = max(0, min(len(values) - 1, nearest + direction))
        self._select(values[index])

    def _on_key(self, value: str) -> None:
        if value == "C":
            self._pending_text = ""
        elif value == "DEL":
            self._pending_text = self._pending_text[:-1]
        elif value == "OK":
            if not self._pending_text:
                return
            ksps = int(self._pending_text)
            if not 333 <= ksps <= 2000:
                return
            self._select(ksps / 1000)
            return
        elif value.isdigit() and len(self._pending_text) < 4:
            self._pending_text += value
        else:
            return
        self.rate_label.setText(self._pending_text or "0")


def create(main_window) -> QtWidgets.QWidget:
    return SymbolRateScreen(main_window)
