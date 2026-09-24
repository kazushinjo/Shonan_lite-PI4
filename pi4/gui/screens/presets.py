"""プリセット選択・登録画面。"""
from __future__ import annotations

from copy import deepcopy

from PyQt5 import QtCore, QtWidgets

from backend import _push_pluto_settings
from i18n import tr
from widgets import SettingsSubScreen, _run_as_overlay, confirm_dialog, error_dialog


_PRESET_FIELDS = (
    "selected_band", "use_custom_lo_frequency", "custom_lo_frequency_hz",
    "pluto_uri", "symbol_rate_msps", "modulation_scheme", "fec_rate",
    "rx_gain_db", "rx_agc_enabled", "tx_power_db", "video_source",
    "video_file_path", "use_color_bar_source", "audio_enabled",
    "camera_device", "overlay_callsign", "overlay_note",
    "overlay_callsign_font_size", "overlay_note_font_size", "overlay_callsign_color",
    "overlay_note_color",
    "use_on_device_demod", "simultaneous_tx_rx_test",
    "rf_loopback_enabled", "loopback_use_localhost", "loopback_target_ip",
)


class PresetsScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("プリセット / Presets", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self.header_bar.hide()
        self.body_layout.setContentsMargins(10, 6, 10, 6)
        self.body_layout.setSpacing(4)

        title = QtWidgets.QLabel(tr("プリセット", "Presets"))
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #54bce0;")
        self.body_layout.addWidget(title)

        card = QtWidgets.QFrame()
        card.setObjectName("presetCard")
        card.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        card.setStyleSheet(
            "QFrame#presetCard { background: #101416; border: 1px solid #34434b; border-radius: 14px; }"
            "QLabel { color: #eeeeee; background: transparent; }"
            "QPushButton { background-color: #303538; color: white; border: none; border-radius: 8px; }"
            "QPushButton:pressed { background-color: #222222; }"
        )
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(4)

        heading = QtWidgets.QLabel(tr("プリセット選択・登録", "Select/Register Preset"))
        heading.setStyleSheet("font-size: 12px; font-weight: bold; color: #54bce0;")
        card_layout.addWidget(heading)

        self._preset_group = QtWidgets.QButtonGroup(self)
        self._preset_group.setExclusive(True)
        self._preset_buttons = []
        self._edit_buttons = []
        self._delete_buttons = []

        self.loopback_btn = None
        for index in range(5):
            select = self._make_button("")
            edit = QtWidgets.QPushButton(tr("登録/変更", "Save"))
            delete = QtWidgets.QPushButton(tr("削除", "Delete"))
            edit.setMinimumHeight(34)
            delete.setMinimumHeight(34)
            edit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            delete.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            compact_style = "QPushButton { min-height: 0px; max-height: 34px; padding: 2px; }"
            edit.setStyleSheet(compact_style)
            delete.setStyleSheet(compact_style)
            select.clicked.connect(lambda checked, i=index: self._select_or_register(i))
            edit.clicked.connect(lambda checked, i=index: self._save_current(i))
            delete.clicked.connect(lambda checked, i=index: self._delete_preset(i))
            self._add_row(card_layout, select, edit, delete)
            self._preset_group.addButton(select)
            self._preset_buttons.append(select)
            self._edit_buttons.append(edit)
            self._delete_buttons.append(delete)

        note = QtWidgets.QLabel(tr(
            "各設定画面の現在値を登録/変更で保存。選択時はPlutoにも反映します。\n"
            "送受信中は編集不可。RFループバックは TX → 40 dB以上 → RX。",
            "\"Save\" stores the current values from each settings screen. Selecting a "
            "preset also applies it to Pluto.\nCannot be edited while transmitting/"
            "receiving. RF loopback is TX → 40 dB or more → RX."))
        note.setWordWrap(True)
        note.setStyleSheet("color: #aeb9bd; font-size: 10px;")
        card_layout.addWidget(note)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        back = QtWidgets.QPushButton(tr("ホームへ戻る", "Back to Home"))
        back.setFixedSize(130, 30)
        back.clicked.connect(lambda: main_window.navigate_to("home"))
        footer.addWidget(back)
        card_layout.addLayout(footer)
        self.body_layout.addWidget(card, 1)

    @staticmethod
    def _make_button(text):
        button = QtWidgets.QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(34)
        button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        button.setStyleSheet(
            "QPushButton { background-color: #303538; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; text-align: left;"
            " font-size: 13px; font-weight: bold; min-height: 0px; max-height: 34px; }"
            "QPushButton:checked { background-color: #1677ff; }"
            "QPushButton:pressed { background-color: #222222; }")
        return button

    def _add_row(self, layout, select, edit, delete):
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(5)
        row.addWidget(select, 1)
        if edit is not None:
            row.addWidget(edit)
            row.addWidget(delete)
        layout.addLayout(row, 1)

    def on_show(self):
        self._refresh()

    def _refresh(self):
        presets = self.main_window.settings.presets
        for index, button in enumerate(self._preset_buttons):
            item = presets[index] if index < len(presets) else None
            if index == 0 and not item:
                label = tr("RFループバック  437.000 MHz / 500 kS/s / QPSK / FEC 3/5",
                           "RF Loopback  437.000 MHz / 500 kS/s / QPSK / FEC 3/5")
            else:
                label = item.get('name', '') if item else tr('未登録', 'Not registered')
            button.setText(tr(f"プリセット{index + 1}  {label}", f"Preset {index + 1}  {label}"))
            button.setChecked(index == 0 and not item
                             and self.main_window.settings.rf_loopback_enabled)
            self._edit_buttons[index].setEnabled(not self._busy())
            self._delete_buttons[index].setEnabled(item is not None and not self._busy())

    def _busy(self):
        return (self.main_window.tx_controller.is_running()
                or self.main_window.rx_controller.is_running())

    def _current_values(self):
        settings = self.main_window.settings
        return {name: deepcopy(getattr(settings, name)) for name in _PRESET_FIELDS}

    def _ask_name(self, initial=""):
        # ★QInputDialog.getText()は独立ウィンドウで開くためlinuxfb(Pi4)では表示されない。
        # ダイアログを作ってPi4の重ね表示(_run_as_overlay)で出す。
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle(tr("プリセット名", "Preset Name"))
        dialog.setLabelText(tr("プリセット名を入力してください:", "Enter a preset name:"))
        dialog.setTextValue(initial)
        accepted = _run_as_overlay(dialog) == QtWidgets.QDialog.Accepted
        name = dialog.textValue().strip()
        return name if accepted and name else None

    def _save_current(self, index):
        if self._busy():
            error_dialog(self, tr("登録できません", "Cannot Save"), tr("送受信を停止してから実行してください。", "Stop TX/RX before doing this."))
            return
        presets = self.main_window.settings.presets
        old = presets[index] if index < len(presets) else None
        name = self._ask_name(old.get("name", "") if old else "")
        if not name:
            return
        item = {"name": name, "values": self._current_values()}
        while len(presets) <= index:
            presets.append({})
        presets[index] = item
        self.main_window.save_settings()
        self._refresh()

    def _select_or_register(self, index):
        presets = self.main_window.settings.presets
        if index >= len(presets) or not presets[index].get("values"):
            if index == 0:
                self._select_loopback(True)
                return
            self._save_current(index)
            return
        if self._busy():
            error_dialog(self, tr("選択できません", "Cannot Select"), tr("送受信を停止してから実行してください。", "Stop TX/RX before doing this."))
            return
        values = presets[index]["values"]
        for name, value in values.items():
            if hasattr(self.main_window.settings, name):
                setattr(self.main_window.settings, name, deepcopy(value))
        self.main_window.save_settings()
        self._apply_pluto()

    def _delete_preset(self, index):
        if self._busy():
            error_dialog(self, tr("削除できません", "Cannot Delete"), tr("送受信を停止してから実行してください。", "Stop TX/RX before doing this."))
            return
        presets = self.main_window.settings.presets
        if index >= len(presets) or not presets[index].get("values"):
            return
        # ★QMessageBox.question()はlinuxfb(Pi4)では表示されないため、Pi4の重ね表示の確認ダイアログを使う。
        if confirm_dialog(
                self, tr("プリセット削除", "Delete Preset"),
                tr(f"「{presets[index].get('name', '')}」を削除しますか？", f"Delete \"{presets[index].get('name', '')}\"?")):
            presets.pop(index)
            self.main_window.save_settings()
            self._refresh()

    def _apply_pluto(self):
        settings = self.main_window.settings
        try:
            _push_pluto_settings(settings, settings.effective_lo_hz())
        except (OSError, ValueError) as exc:
            error_dialog(self, tr("Pluto設定エラー", "Pluto Settings Error"),
                         tr(f"プリセットをPlutoへ反映できませんでした。\n{exc}",
                            f"Failed to apply the preset to Pluto.\n{exc}"))

    def _select_loopback(self, checked):
        if not checked:
            self.main_window.settings.rf_loopback_enabled = False
            self.main_window.save_settings()
            return
        settings = self.main_window.settings
        settings.selected_band = "LOOPBACK"
        settings.use_custom_lo_frequency = True
        settings.custom_lo_frequency_hz = 437_000_000
        settings.symbol_rate_msps = 0.5
        settings.modulation_scheme = "QPSK"
        settings.fec_rate = "3/5"
        settings.rx_gain_db = 60
        settings.rx_agc_enabled = False
        settings.video_source = "colorbar"
        settings.use_color_bar_source = True
        settings.rf_loopback_enabled = True
        settings.use_on_device_demod = True
        settings.simultaneous_tx_rx_test = True
        self.main_window.save_settings()
        self._apply_pluto()


def create(main_window):
    return PresetsScreen(main_window)
