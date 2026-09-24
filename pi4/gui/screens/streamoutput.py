"""出力設定画面。モック準拠の出力先設定+出力情報レイアウト。"""
from __future__ import annotations

import threading

from PyQt5 import QtCore, QtGui, QtWidgets
from backend import PLUTO_UDP_TS_PORT, discover_pluto_ip
from settings_store import normalize_pluto_host
from i18n import tr
from widgets import SettingsSubScreen, error_dialog


class StreamOutputScreen(SettingsSubScreen):
    pluto_discovery_finished = QtCore.pyqtSignal(object)

    def __init__(self, main_window):
        super().__init__("出力設定 / Stream Output", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self.fields = {}
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        left = QtWidgets.QFrame()
        left.setStyleSheet("QFrame { background: #191d1f; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(3)
        title = QtWidgets.QLabel(tr("出力先設定", "Output Destination"))
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        left_layout.addWidget(title)
        protocol = QtWidgets.QComboBox()
        protocol.addItem("UDP")
        protocol.setFixedHeight(30)
        protocol.setStyleSheet("QComboBox { min-height: 30px; max-height: 30px; padding: 2px 8px; }")
        left_layout.addWidget(QtWidgets.QLabel(tr("出力先", "Destination")))
        left_layout.addWidget(protocol)
        left_layout.addWidget(QtWidgets.QLabel("Pluto URI"))
        pluto_uri_row = QtWidgets.QHBoxLayout()
        pluto_uri_row.setSpacing(6)
        self.pluto_uri_edit = QtWidgets.QLineEdit()
        self.pluto_uri_edit.setFixedHeight(30)
        self.pluto_uri_edit.setStyleSheet("QLineEdit { min-height: 30px; max-height: 30px; padding: 3px 8px; }")
        self.pluto_uri_edit.editingFinished.connect(self._save_pluto_uri)
        pluto_uri_row.addWidget(self.pluto_uri_edit, 1)
        self.pluto_search_btn = QtWidgets.QPushButton(tr("自動検出", "Detect"))
        self.pluto_search_btn.setFixedHeight(30)
        self.pluto_search_btn.setFixedWidth(90)
        self.pluto_search_btn.setStyleSheet("QPushButton { min-height: 30px; max-height: 30px; padding: 2px 4px; }")
        # ★ボタンがフォーカスを持ったまま検出中に無効化(setEnabled(False))されると、
        # Qtはフォーカスをタブ順で次の「送信先ポート」欄(QLineEdit)へ移すため、
        # 入力の必要が無いのにオンスクリーンキーボードが表示されていた(実機で確認)。
        self.pluto_search_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pluto_search_btn.clicked.connect(self._search_pluto_ip)
        pluto_uri_row.addWidget(self.pluto_search_btn)
        left_layout.addLayout(pluto_uri_row)
        self.pluto_discovery_status_label = QtWidgets.QLabel("")
        self.pluto_discovery_status_label.setStyleSheet("color: #9aa0a6; font-size: 11px;")
        self.pluto_discovery_status_label.setWordWrap(True)
        left_layout.addWidget(self.pluto_discovery_status_label)
        self.pluto_discovery_finished.connect(self._on_pluto_discovery_finished)
        left_layout.addWidget(QtWidgets.QLabel(tr("送信先ポート（Pluto側固定）", "Destination port (fixed on Pluto)")))
        self.dest_port_edit = QtWidgets.QLineEdit(str(PLUTO_UDP_TS_PORT))
        self.dest_port_edit.setReadOnly(True)
        self.dest_port_edit.setFixedHeight(30)
        self.dest_port_edit.setStyleSheet(
            "QLineEdit { min-height: 30px; max-height: 30px; padding: 3px 8px; color: #9aa0a6; }")
        left_layout.addWidget(self.dest_port_edit)
        self._add_int_field("rx_listen_port", tr("受信TSポート", "RX TS port"), left_layout)
        self._add_int_field("rx_status_port", tr("ステータスポート", "Status port"), left_layout)
        left_layout.addStretch(1)
        columns.addWidget(left, 1)

        right = QtWidgets.QFrame()
        right.setStyleSheet("QFrame { background: #191d1f; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(8)
        title = QtWidgets.QLabel(tr("出力情報", "Output Info"))
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        right_layout.addWidget(title)
        self.info_labels = {}
        for key, label in (("protocol", tr("プロトコル", "Protocol")), ("ip", "Pluto URI"),
                           ("port", tr("ポート", "Port")), ("mtu", "MTU"), ("ttl", "TTL")):
            row = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(label)
            name.setStyleSheet("color: #9aa0a6; font-size: 12px;")
            value = QtWidgets.QLabel()
            value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            value.setStyleSheet("color: white; font-size: 13px;")
            row.addWidget(name)
            row.addWidget(value, 1)
            right_layout.addLayout(row)
            self.info_labels[key] = value
        right_layout.addSpacing(8)
        status = QtWidgets.QLabel(tr("ステータス: 待機中", "Status: Idle"))
        status.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        right_layout.addWidget(status)
        columns.addWidget(right, 1)

    def _add_int_field(self, key, label, parent_layout):
        edit = QtWidgets.QLineEdit()
        edit.setFixedHeight(30)
        edit.setStyleSheet("QLineEdit { min-height: 30px; max-height: 30px; padding: 3px 8px; }")
        edit.setValidator(QtGui.QIntValidator(1, 65535, edit))
        edit.editingFinished.connect(lambda k=key, e=edit: self._save_int(k, e))
        parent_layout.addWidget(QtWidgets.QLabel(label))
        parent_layout.addWidget(edit)
        self.fields[key] = edit

    def on_show(self):
        settings = self.main_window.settings
        for key, edit in self.fields.items():
            edit.setText(str(getattr(settings, key)))
        self.pluto_uri_edit.setText(settings.pluto_host())
        self.pluto_discovery_status_label.setText("")
        self.info_labels["protocol"].setText("UDP")
        self.info_labels["ip"].setText(settings.pluto_uri)
        self.info_labels["port"].setText(str(settings.rx_listen_port))
        self.info_labels["mtu"].setText("1500")
        self.info_labels["ttl"].setText("1")

    def _save_pluto_uri(self) -> None:
        value = self.pluto_uri_edit.text().strip()
        try:
            host = normalize_pluto_host(value)
        except ValueError as exc:
            self.pluto_uri_edit.setText(self.main_window.settings.pluto_host())
            error_dialog(self, tr("Pluto接続先エラー", "Pluto Destination Error"), str(exc))
            return
        self.main_window.settings.pluto_uri = f"ip:{host}"
        self.main_window.save_settings()
        self.info_labels["ip"].setText(self.main_window.settings.pluto_uri)

    def _search_pluto_ip(self) -> None:
        if not self.pluto_search_btn.isEnabled():
            return
        self.pluto_search_btn.setEnabled(False)
        self.pluto_discovery_status_label.setText(tr("Plutoを検索中...", "Searching for Pluto..."))
        threading.Thread(target=self._run_pluto_discovery, daemon=True).start()

    def _run_pluto_discovery(self) -> None:
        # 全インタフェース×最大254ホスト総当たりの場合もあるため専用スレッドで実行し、
        # UIをブロックしない(backend.discover_pluto_ip参照)。
        host = discover_pluto_ip()
        self.pluto_discovery_finished.emit(host)

    def _on_pluto_discovery_finished(self, host: object) -> None:
        self.pluto_search_btn.setEnabled(True)
        if host is None:
            self.pluto_discovery_status_label.setText(tr(
                "Plutoが見つかりませんでした(電源・LAN接続を確認してください)",
                "Pluto not found (check power and LAN connection)"))
            return
        self.pluto_uri_edit.setText(host)
        self._save_pluto_uri()
        self.pluto_discovery_status_label.setText(tr(f"Plutoを検出しました: {host}", f"Pluto detected: {host}"))

    def _save_int(self, key, edit):
        try:
            value = int(edit.text().strip())
        except ValueError:
            return
        if 1 <= value <= 65535:
            setattr(self.main_window.settings, key, value)
            self.main_window.save_settings()


def create(main_window):
    return StreamOutputScreen(main_window)
