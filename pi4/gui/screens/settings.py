"""設定画面。Mac版Shonan_Liteの設定画面に合わせ、表示言語・バンドプロファイル・
Wi-Fi案内・ビットレート・Pluto接続先・オンデバイス復調状態をまとめて表示する。
"""
from __future__ import annotations

from settings_store import normalize_pluto_host, normalize_ptt_controller_host
import subprocess

from PyQt5 import QtCore, QtWidgets

from settings_store import BAND_PROFILES
from i18n import set_language, tr
from widgets import SettingsSubScreen, confirm_dialog, error_dialog


class SettingsScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("設定 / Config", lambda: main_window.navigate_to("home"))
        self.main_window = main_window

        # Mac版設定画面を参考にした中央パネル。800x480のPi5画面では、
        # スクロール可能なダークパネルとしてタッチ操作に合わせる。
        content_layout = self.body_layout
        content_layout.setContentsMargins(14, 8, 14, 14)
        content_layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        panel = QtWidgets.QFrame()
        panel.setObjectName("settingsPanel")
        panel.setMinimumWidth(740)
        panel.setMaximumWidth(780)
        panel.setStyleSheet(
            "QFrame#settingsPanel { background-color: #171a1c;"
            " border: 1px solid #4b5357; border-radius: 18px; }"
            "QFrame#settingsPanel QLabel { color: #eeeeee; background-color: transparent; }"
            "QFrame#settingsPanel QComboBox, QLineEdit, QDateTimeEdit {"
            " background-color: #202427; color: #eeeeee;"
            " border: 1px solid #42494d; border-radius: 8px; padding: 8px; }"
            "QFrame#settingsPanel QCheckBox { color: #eeeeee; }"
            "QFrame#settingsPanel QPushButton { border-radius: 8px; }"
        )
        content_layout.addWidget(panel)
        self.body_layout = QtWidgets.QVBoxLayout(panel)
        self.body_layout.setContentsMargins(20, 14, 20, 14)
        self.body_layout.setSpacing(10)

        heading = QtWidgets.QLabel(tr("設定", "Settings"))
        heading.setStyleSheet("font-size: 21px; font-weight: bold; color: white;")
        self.body_layout.addWidget(heading)

        self.body_layout.addWidget(self._section_label(tr("表示言語", "Display Language")))
        lang_layout = QtWidgets.QHBoxLayout()
        lang_layout.setSpacing(0)
        lang_group = QtWidgets.QButtonGroup(self)
        self.ja_lang_btn = self._segment_button("日本語", main_window.settings.language == "JAPANESE")
        self.en_lang_btn = self._segment_button("English", main_window.settings.language == "ENGLISH")
        lang_group.addButton(self.ja_lang_btn)
        lang_group.addButton(self.en_lang_btn)
        self.ja_lang_btn.clicked.connect(lambda: self._set_language("JAPANESE"))
        self.en_lang_btn.clicked.connect(lambda: self._set_language("ENGLISH"))
        lang_layout.addWidget(self.ja_lang_btn)
        lang_layout.addWidget(self.en_lang_btn)
        lang_layout.addStretch(1)
        self.body_layout.addLayout(lang_layout)

        # ★バンドプロファイルUIは非表示化(要望により)。settings.selected_bandの
        # 保存値・読み込み・変更ロジック自体は維持し、ウィジェットのみ隠す。
        self.band_section_label = self._section_label("バンドプロファイル / Band Profile")
        self.band_section_label.setVisible(False)
        self.body_layout.addWidget(self.band_section_label)
        self.band_combo = QtWidgets.QComboBox()
        self.band_combo.setMinimumHeight(48)
        for band, info in BAND_PROFILES.items():
            if band == "LOOPBACK":
                continue
            self.band_combo.addItem(f"{info['label_ja']} / {info['label_en']}", band)
        self.band_combo.currentIndexChanged.connect(self._on_band_combo_changed)
        self.band_combo.setVisible(False)
        self.body_layout.addWidget(self.band_combo)

        # ★推奨Wi-Fi帯・目安ビットレート表示は非表示化(要望により)。値の更新
        # ロジック自体は維持し、ウィジェットのみ隠す。
        self.wifi_label = QtWidgets.QLabel()
        self.wifi_reason_label = QtWidgets.QLabel()
        self.wifi_reason_label.setStyleSheet("color: #999999; font-size: 12px;")
        self.bitrate_label = QtWidgets.QLabel()
        self.wifi_label.setVisible(False)
        self.wifi_reason_label.setVisible(False)
        self.bitrate_label.setVisible(False)
        self.body_layout.addWidget(self.wifi_label)
        self.body_layout.addWidget(self.wifi_reason_label)
        self.body_layout.addWidget(self.bitrate_label)

        self.body_layout.addWidget(self._section_label(tr("送信先 (Pluto Tx)", "Destination (Pluto Tx)")))
        self.pluto_ip_edit = QtWidgets.QLineEdit()
        self.pluto_ip_edit.setMinimumHeight(48)
        self.pluto_ip_edit.setPlaceholderText("192.168.0.136")
        self.pluto_ip_edit.editingFinished.connect(self._save_pluto_ip)
        self.body_layout.addWidget(self.pluto_ip_edit)
        self.pluto_udp_port_label = QtWidgets.QLabel(
            tr("UDP-TSポート: 8282（Pluto側固定）", "UDP-TS port: 8282 (fixed on Pluto)"))
        self.pluto_udp_port_label.setStyleSheet("color: #cccccc;")
        self.body_layout.addWidget(self.pluto_udp_port_label)

        self.body_layout.addWidget(self._section_label(
            tr("PA_Power/PTTコントローラ (ESP32)", "PA_Power/PTT Controller (ESP32)")))
        self.ptt_controller_ip_edit = QtWidgets.QLineEdit()
        self.ptt_controller_ip_edit.setMinimumHeight(48)
        self.ptt_controller_ip_edit.setPlaceholderText(tr("未使用の場合は空欄のまま", "Leave empty if not used"))
        self.ptt_controller_ip_edit.editingFinished.connect(self._save_ptt_controller_ip)
        self.body_layout.addWidget(self.ptt_controller_ip_edit)
        ptt_note = QtWidgets.QLabel(tr(
            "hardware/W5500_PA_PTT_Control のESP32+W5500ボードのIPアドレス。"
            "送信開始/終了に連動してPTTを、アプリ起動/終了に連動して12V電源を自動切替します。"
            "空欄なら連携しません。",
            "IP address of the ESP32 + W5500 board (hardware/W5500_PA_PTT_Control). "
            "PTT follows TX start/stop and the 12 V power is switched automatically at "
            "app start/exit. Leave empty to disable the link."
        ))
        # ★長い説明文(特に英語)が折り返されずに画面の右端で切れていたため、折り返す。
        ptt_note.setWordWrap(True)
        self.body_layout.addWidget(ptt_note)

        self.body_layout.addWidget(self._section_label(tr("オンデバイス復調", "On-device Demodulation")))
        self.on_device_checkbox = QtWidgets.QCheckBox(tr("オンデバイス復調 (GNU Radio)", "On-device demodulation (GNU Radio)"))
        self.on_device_checkbox.toggled.connect(self._on_on_device_toggled)
        self.body_layout.addWidget(self.on_device_checkbox)
        self.body_layout.addWidget(QtWidgets.QLabel(
            tr("ONのとき、送信画面に「受信画面へ」ボタンを表示します。",
               "When ON, the \"Go to RX\" button is shown on the TX screen.")
        ))

        self.body_layout.addWidget(self._section_label(tr("受信診断 / RX Diagnostics", "RX Diagnostics")))
        self.iio_preflight_checkbox = QtWidgets.QCheckBox(
            tr("IIOプリフライト試験を実施する", "Run IIO preflight test"))
        self.iio_preflight_checkbox.setMinimumHeight(48)
        self.iio_preflight_checkbox.toggled.connect(
            self._on_iio_preflight_toggled)
        self.body_layout.addWidget(self.iio_preflight_checkbox)

        # ★このPi5にはRTCバッテリがなく、ネットワーク接続がない現場運用では起動のたびに
        # 日時がリセットされる。オーバーレイ(コールサイン+日時焼き込み、映像ソース画面参照)
        # の日時を正しくするため、手動で日時を設定できるようにする。
        self.body_layout.addWidget(self._section_label(tr("システム日時 / System Date & Time", "System Date & Time")))
        self.datetime_edit = QtWidgets.QDateTimeEdit()
        self.datetime_edit.setMinimumHeight(48)
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.body_layout.addWidget(self.datetime_edit)
        self.set_datetime_btn = QtWidgets.QPushButton(tr("この日時を設定 / Set", "Set This Date & Time"))
        self.set_datetime_btn.setMinimumHeight(48)
        self.set_datetime_btn.clicked.connect(self._on_set_datetime)
        self.body_layout.addWidget(self.set_datetime_btn)
        settings = self.main_window.settings
        index = self.band_combo.findData(settings.selected_band)
        if index >= 0:
            self.band_combo.blockSignals(True)
            self.band_combo.setCurrentIndex(index)
            self.band_combo.blockSignals(False)
        self._update_band_info(settings.selected_band)
        self.pluto_ip_edit.setText(settings.pluto_host())
        self.ptt_controller_ip_edit.setText(settings.ptt_controller_host)
        self.on_device_checkbox.blockSignals(True)
        self.on_device_checkbox.setChecked(settings.use_on_device_demod)
        self.on_device_checkbox.blockSignals(False)
        self.iio_preflight_checkbox.blockSignals(True)
        self.iio_preflight_checkbox.setChecked(settings.iio_preflight_enabled)
        self.iio_preflight_checkbox.blockSignals(False)
        self.datetime_edit.setDateTime(QtCore.QDateTime.currentDateTime())

    @staticmethod
    def _section_label(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f2f2f2; padding-top: 8px;")
        return label

    @staticmethod
    def _segment_button(text: str, checked: bool) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setFixedSize(82, 34)
        button.setStyleSheet(
            "QPushButton { background-color: #303538; color: #eeeeee; border: none;"
            " min-height: 32px; padding: 3px 8px; font-size: 12px; font-weight: bold; }"
            "QPushButton:checked { background-color: #1677ff; color: white; }"
            "QPushButton:pressed { background-color: #102a5c; }"
        )
        return button

    def _set_language(self, lang: str) -> None:
        self.main_window.settings.language = lang
        set_language(lang)
        self.main_window.save_settings()
        self.main_window.rebuild_language()

    def _on_band_combo_changed(self, index: int) -> None:
        band = self.band_combo.itemData(index)
        settings = self.main_window.settings
        settings.selected_band = band
        settings.use_custom_lo_frequency = False
        lo_hz = BAND_PROFILES[band]["lo_hz"]
        if lo_hz is not None:
            settings.custom_lo_frequency_hz = lo_hz
        self._update_band_info(band)
        self.main_window.save_settings()

    def _update_band_info(self, band: str) -> None:
        info = BAND_PROFILES.get(band, BAND_PROFILES["BAND_1200"])
        # Pi4に残っているループバック試験のバンドにはWi-Fi情報が無いため、1200MHz帯の表示で代用する。
        if "wifi" not in info:
            info = BAND_PROFILES["BAND_1200"]
        self.wifi_label.setText(f"推奨Wi-Fi帯: {info['wifi']}")
        self.wifi_reason_label.setText(info["wifi_reason"])
        self.bitrate_label.setText(f"目安ビットレート: {info['bitrate_mbps']:g} Mbps")

    def _save_pluto_ip(self) -> None:
        value = self.pluto_ip_edit.text().strip()
        try:
            host = normalize_pluto_host(value)
        except ValueError as exc:
            self.pluto_ip_edit.setText(self.main_window.settings.pluto_host())
            error_dialog(self, tr("Pluto接続先エラー", "Pluto Destination Error"), str(exc))
            return
        self.main_window.settings.pluto_uri = f"ip:{host}"
        self.main_window.save_settings()

    def _save_ptt_controller_ip(self) -> None:
        value = self.ptt_controller_ip_edit.text().strip()
        try:
            host = normalize_ptt_controller_host(value)
        except ValueError as exc:
            self.ptt_controller_ip_edit.setText(self.main_window.settings.ptt_controller_host)
            error_dialog(self, tr("PTTコントローラ接続先エラー", "PTT Controller Destination Error"), str(exc))
            return
        self.main_window.settings.ptt_controller_host = host
        self.main_window.save_settings()

    def _on_on_device_toggled(self, checked: bool) -> None:
        if checked:
            # ★オンデバイス復調は開発時の動作確認用機能。PlutoのTX端子とRX端子間に
            # 40 dB以上の外部アッテネータが入っていない状態で有効にすると、TX出力が
            # 直接RXに回り込みPlutoを破損する恐れがあるため、有効化前に必ず警告する。
            if not confirm_dialog(
                self, tr("オンデバイス復調の注意", "On-device Demodulation Warning"),
                tr(
                    "オンデバイス復調は開発時の動作確認用の機能です。<br>"
                    "<span style='color:#ff3b30;'>PlutoのTX端子とRX端子の間に40 dB以上の"
                    "外部アッテネータが入っていない状態で送信すると、"
                    "Plutoを破損する恐れがあります。</span><br><br>"
                    "アッテネータが接続されていることを確認しましたか?",
                    "On-device demodulation is a feature for development testing.<br>"
                    "<span style='color:#ff3b30;'>Transmitting without a 40 dB or greater "
                    "external attenuator between the Pluto's TX and RX ports may damage "
                    "the Pluto.</span><br><br>"
                    "Have you confirmed that an attenuator is connected?"
                )
            ):
                self.on_device_checkbox.blockSignals(True)
                self.on_device_checkbox.setChecked(False)
                self.on_device_checkbox.blockSignals(False)
                return
        self.main_window.settings.use_on_device_demod = checked
        self.main_window.settings.simultaneous_tx_rx_test = checked
        self.main_window.save_settings()
        tx_screen = self.main_window._screens.get("tx")
        if tx_screen is not None and hasattr(tx_screen, "update_navigation_buttons"):
            tx_screen.update_navigation_buttons()

    def _on_iio_preflight_toggled(self, checked: bool) -> None:
        self.main_window.settings.iio_preflight_enabled = checked
        self.main_window.save_settings()

    def _on_set_datetime(self) -> None:
        # ★手動設定してもNTPが有効なままだとsystemdが直後に上書きしてしまうため、
        # 先にNTP同期を止めてからtimedatectlで反映する(RTCバッテリなし・現場運用で
        # ネットワーク未接続の機体を想定)。
        value = self.datetime_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        try:
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-ntp", "false"],
                check=True, capture_output=True, text=True, timeout=5)
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-time", value],
                check=True, capture_output=True, text=True, timeout=5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            message = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else str(exc)
            error_dialog(self, tr("日時設定エラー", "Date & Time Error"),
                         tr(f"日時の設定に失敗しました:\n{message}", f"Failed to set date & time:\n{message}"))


def create(main_window) -> QtWidgets.QWidget:
    return SettingsScreen(main_window)
