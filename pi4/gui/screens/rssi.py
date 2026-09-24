"""RSSI測定画面(旧: 相手局検索/AFC)。Shonan_Lite-RasPI5のrssi.pyからの移植
(800x480向けレイアウト。警告はPi4のlinuxfbでも表示されるerror_dialogを使う)。"""
from __future__ import annotations

import dataclasses
import os
import shutil
import subprocess

from PyQt5 import QtCore, QtGui, QtWidgets

from i18n import tr
from widgets import SettingsSubScreen, error_dialog

# ★ネイティブビルド環境のiio_attrが無い機体(apt版libiio-utilsのみ)もあるため、無ければPATH上の
# iio_attr(/usr/bin/iio_attr)を使う。固定パスのままだと起動に失敗し、RSSIが1点も取れない。
_NATIVE_IIO_ATTR = "/home/pi/shonan-pi4-native-build/dvbs2-deps-install-native-aarch64/bin/iio_attr"
IIO_ATTR_BIN = (_NATIVE_IIO_ATTR if os.path.exists(_NATIVE_IIO_ATTR)
                else shutil.which("iio_attr") or "iio_attr")
STEP_INTERVAL_MS = 150
# RXゲイン(AD9361の手動ゲイン範囲。RXゲイン画面のスライダーと同じ)
RX_GAIN_MIN_DB = 0
RX_GAIN_MAX_DB = 73


class RssiGraphWidget(QtWidgets.QWidget):
    """検索中の周波数(横軸)とRSSI(縦軸)を折れ線で表示する。

    AD9361の`voltage0/rssi`属性は値が小さいほど信号が強い(減衰量に近い指標)ため、
    グラフは値が小さいほど上に来るよう反転して描画し、直感的な「山」がそのまま
    信号が強い箇所を表すようにする。
    """

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.setStyleSheet("background: #050607; border: 1px solid #34434b; border-radius: 8px;")
        self._points: list[tuple[float, float]] = []
        self._freq_range: tuple[float, float] | None = None
        self._center_hz: float | None = None

    def set_range(self, start_hz: float, end_hz: float) -> None:
        self._freq_range = (start_hz, end_hz)
        self._points = []
        self.update()

    def set_center(self, center_hz: float | None) -> None:
        self._center_hz = center_hz
        self.update()

    def add_point(self, freq_hz: float, rssi_db: float) -> None:
        self._points.append((freq_hz, rssi_db))
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        plot_rect = self.rect().adjusted(44, 10, -10, -26)
        painter.setPen(QtGui.QPen(QtGui.QColor("#46545b"), 1))
        painter.drawRect(plot_rect)

        if not self._freq_range or not self._points:
            painter.setPen(QtGui.QColor("#6b7880"))
            font = painter.font()
            font.setPixelSize(13)
            painter.setFont(font)
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, tr("検索開始でRSSIを表示します", "RSSI appears after you start a search"))
            return

        start_hz, end_hz = self._freq_range
        span_hz = max(end_hz - start_hz, 1)
        rssi_values = [rssi for _freq, rssi in self._points]
        y_min, y_max = min(rssi_values), max(rssi_values)
        if y_min == y_max:
            y_min, y_max = y_min - 1, y_max + 1
        else:
            pad = (y_max - y_min) * 0.1
            y_min, y_max = y_min - pad, y_max + pad

        def x_for(freq_hz: float) -> float:
            return plot_rect.left() + (freq_hz - start_hz) / span_hz * plot_rect.width()

        def y_for(rssi: float) -> float:
            # 値が小さいほど信号が強い指標なので、上に行くほど強くなるよう反転する。
            ratio = (rssi - y_min) / (y_max - y_min)
            return plot_rect.top() + ratio * plot_rect.height()

        painter.setPen(QtGui.QPen(QtGui.QColor("#2a3236"), 1))
        for i in (1, 2, 3):
            y = plot_rect.top() + plot_rect.height() * i / 4
            painter.drawLine(plot_rect.left(), int(y), plot_rect.right(), int(y))

        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#9aa0a6"))
        painter.drawText(
            QtCore.QRectF(0, plot_rect.top() - 8, 40, 14),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{y_min:.0f}")
        painter.drawText(
            QtCore.QRectF(0, plot_rect.bottom() - 8, 40, 14),
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{y_max:.0f}")
        # ★drawTextは枠からはみ出した分を切り取るため、枠幅を固定(70px)にすると
        # 「1283000 kHz」の先頭の「1」が欠けて「283000 kHz」に見えることがある。
        # 枠幅は文字列の実測幅から決める(Windows版で実機確認済みの修正を移植)。
        fm = painter.fontMetrics()
        start_text = f"{start_hz / 1000:.0f}"
        end_text = f"{end_hz / 1000:.0f} kHz"
        start_w = fm.horizontalAdvance(start_text) + 6
        end_w = fm.horizontalAdvance(end_text) + 6
        painter.drawText(
            QtCore.QRectF(plot_rect.left() - 20, plot_rect.bottom() + 4, start_w, 18),
            QtCore.Qt.AlignLeft, start_text)
        painter.drawText(
            QtCore.QRectF(plot_rect.right() - end_w, plot_rect.bottom() + 4, end_w, 18),
            QtCore.Qt.AlignRight, end_text)

        if self._center_hz is not None and start_hz <= self._center_hz <= end_hz:
            x = x_for(self._center_hz)
            painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff"), 1, QtCore.Qt.DashLine))
            painter.drawLine(QtCore.QPointF(x, plot_rect.top()), QtCore.QPointF(x, plot_rect.bottom()))

        if len(self._points) >= 2:
            painter.setPen(QtGui.QPen(QtGui.QColor("#e03030"), 2))
            path = QtGui.QPainterPath()
            path.moveTo(x_for(self._points[0][0]), y_for(self._points[0][1]))
            for freq_hz, rssi in self._points[1:]:
                path.lineTo(x_for(freq_hz), y_for(rssi))
            painter.drawPath(path)

        # 測定値そのものを目立たせるため、各点に赤丸を重ねて描画する。
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#ff3b30"))
        for freq_hz, rssi in self._points:
            painter.drawEllipse(QtCore.QPointF(x_for(freq_hz), y_for(rssi)), 2, 2)

        best_freq, best_rssi = min(self._points, key=lambda point: point[1])
        painter.setBrush(QtGui.QColor("#ffcc33"))
        painter.drawEllipse(QtCore.QPointF(x_for(best_freq), y_for(best_rssi)), 2, 2)


class RssiScreen(SettingsSubScreen):
    # ★祖先(SettingsSubScreen)のQSSがQPushButton/QLineEditにmin-height/paddingを
    # 全体適用しており(52px/42px)、個別スタイルで上書きしていないプロパティは
    # そのまま継承されて肥大化する。800x480に収めるため、以下は必ずmin-height/
    # max-height/paddingを明示して継承を断ち切る。
    _EDIT_STYLE = "font-size: 18px; font-weight: bold; padding: 2px 6px; min-height: 30px; max-height: 30px;"
    _EDIT_STYLE_ACTIVE = _EDIT_STYLE + " border: 2px solid #0797bd;"
    _PRESET_STYLE = (
        "QPushButton { background: #303538; color: white; border: none;"
        " border-radius: 6px; font-size: 13px; font-weight: bold;"
        " padding: 2px 4px; min-height: 30px; max-height: 30px; }"
        "QPushButton:pressed { background: #222222; }")
    # 選択中のレンジを水色でハイライトする。
    _PRESET_STYLE_SELECTED = (
        "QPushButton { background: #54bce0; color: #101416; border: none;"
        " border-radius: 6px; font-size: 13px; font-weight: bold;"
        " padding: 2px 4px; min-height: 30px; max-height: 30px; }"
        "QPushButton:pressed { background: #3f96b3; }")
    # 画面表示時に周波数画面の設定を自動で取り込む際の既定レンジ幅。
    _DEFAULT_RANGE_KHZ = 10000
    _PEAK_THRESHOLD_DB = 3.0

    def __init__(self, main_window):
        super().__init__("RSSI測定 / RSSI Measurement", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self._scanning = False
        self._tx_started_by_scan = False
        self._current_freq = 0
        self._start_freq = 0
        self._end_freq = 0
        self._step_hz = 10_000
        self._best_rssi = None
        self._best_freq = None
        self._scan_best_rssi = None
        self._scan_best_freq = None
        self._scan_rssi_values = []
        self._active_edit = None
        self.step_edit = None
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(10, 8, 10, 10)
        self.body_layout.setSpacing(6)

        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame { background: #101416; border: 1px solid #34434b; border-radius: 14px; }"
            "QLabel { color: #eeeeee; background: transparent; }"
        )
        self.body_layout.addWidget(card, 1)
        outer = QtWidgets.QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 8)
        outer.setSpacing(6)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(10)
        outer.addLayout(columns, 1)

        left = QtWidgets.QFrame()
        left.setFixedWidth(300)
        left.setStyleSheet("QFrame { background: #191d1f; border: 1px solid #34434b; border-radius: 10px; } QLabel { font-size: 13px; }")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(8, 6, 8, 6)
        left_layout.setSpacing(4)
        title = QtWidgets.QLabel(tr("検索条件", "Search Conditions"))
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #54bce0;")
        left_layout.addWidget(title)
        self.start_edit = QtWidgets.QLabel("435000")
        self.end_edit = QtWidgets.QLabel("439000")

        self.center_freq_label = QtWidgets.QLabel()
        self.center_freq_label.setWordWrap(True)
        self.center_freq_label.setStyleSheet("color: #54bce0; font-size: 13px; font-weight: bold;")
        left_layout.addWidget(self.center_freq_label)
        preset_row = QtWidgets.QHBoxLayout()
        preset_row.setSpacing(6)
        self._preset_buttons: dict[int, QtWidgets.QPushButton] = {}
        self._selected_preset_mhz: int | None = None
        for offset_mhz in (5, 10, 20):
            preset_btn = QtWidgets.QPushButton(f"±{offset_mhz}MHz")
            preset_btn.setMinimumHeight(34)
            preset_btn.clicked.connect(
                lambda _checked=False, mhz=offset_mhz: self._apply_preset_range(mhz * 1000))
            preset_row.addWidget(preset_btn)
            self._preset_buttons[offset_mhz] = preset_btn
        left_layout.addLayout(preset_row)
        self._set_selected_preset(self._DEFAULT_RANGE_KHZ // 1000)

        step_row = QtWidgets.QHBoxLayout()
        step_row.addWidget(QtWidgets.QLabel(tr("ステップ", "Step")))
        self.step_edit = QtWidgets.QLineEdit("100")
        self.step_edit.setAlignment(QtCore.Qt.AlignRight)
        self.step_edit.setMaximumWidth(100)
        self.step_edit.setStyleSheet(self._EDIT_STYLE)
        self.step_edit.setReadOnly(True)
        self.step_edit.setFocusPolicy(QtCore.Qt.NoFocus)
        self.step_edit.setAttribute(QtCore.Qt.WA_InputMethodEnabled, False)
        self.step_edit.installEventFilter(self)
        step_row.addWidget(self.step_edit)
        step_row.addWidget(QtWidgets.QLabel("kHz"))
        step_row.addStretch(1)
        left_layout.addLayout(step_row)

        keypad = QtWidgets.QWidget()
        keypad_grid = QtWidgets.QGridLayout(keypad)
        keypad_grid.setContentsMargins(0, 0, 0, 0)
        keypad_grid.setHorizontalSpacing(4)
        keypad_grid.setVerticalSpacing(4)
        keypad_grid.setAlignment(QtCore.Qt.AlignCenter)
        keypad_positions = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("DEL", 0, 3),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("C", 1, 3),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("0", 3, 0), ("OK", 3, 3),
        ]
        for label, row, column in keypad_positions:
            button = QtWidgets.QPushButton(label)
            button.setFixedSize(50, 30)
            button.setStyleSheet(
                "QPushButton { background: #252a2d; color: white; border: 1px solid #69747a;"
                " border-radius: 6px; font-size: 14px; font-weight: bold;"
                " min-width: 50px; max-width: 50px; min-height: 30px; max-height: 30px; padding: 0px; }"
                "QPushButton:pressed { background: #0c9bc0; }")
            button.clicked.connect(lambda _checked=False, value=label: self._on_key(value))
            keypad_grid.addWidget(button, row, column)
        left_layout.addWidget(keypad, 0, QtCore.Qt.AlignHCenter)
        left_layout.addStretch(1)
        self.search_btn = QtWidgets.QPushButton(tr("検索開始", "Start Search"))
        self.search_btn.setFixedHeight(36)
        self.search_btn.clicked.connect(self._on_start_stop)
        self.search_btn.setStyleSheet(
            "QPushButton { background: #0c91b5; color: white; border: none;"
            " border-radius: 6px; font-size: 15px; font-weight: bold;"
            " padding: 2px 6px; min-height: 36px; max-height: 36px; }")
        left_layout.addWidget(self.search_btn)
        columns.addWidget(left, 1)

        right = QtWidgets.QFrame()
        right.setStyleSheet("QFrame { background: #191d1f; border: 1px solid #34434b; border-radius: 10px; }")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(4)
        result_title = QtWidgets.QLabel(tr("検索結果", "Search Result"))
        result_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #54bce0;")
        right_layout.addWidget(result_title)
        self.rssi_graph = RssiGraphWidget()
        self.rssi_graph.setMinimumHeight(140)
        right_layout.addWidget(self.rssi_graph, 1)

        best_row = QtWidgets.QHBoxLayout()
        self.best_freq_label = QtWidgets.QLabel(tr("最も強い周波数: -", "Strongest frequency: -"))
        self.best_freq_label.setStyleSheet("color: #eeeeee; font-size: 13px; font-weight: bold;")
        best_row.addWidget(self.best_freq_label)
        best_row.addStretch(1)
        right_layout.addLayout(best_row)

        # 検索の繰り返し方: 連続(「検索停止」まで繰り返す)/ 1回(範囲の終わりで自動停止)。
        # 検索中に切り替えた場合は、実行中の周回が終わった時点から反映される。
        mode_row = QtWidgets.QHBoxLayout()
        mode_title = QtWidgets.QLabel(tr("検索方法", "Search Mode"))
        mode_title.setStyleSheet("color: #eeeeee; font-size: 13px; font-weight: bold;")
        mode_row.addWidget(mode_title)
        mode_row.addStretch(1)
        self._mode_group = QtWidgets.QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self.repeat_btn = QtWidgets.QPushButton(tr("連続", "Repeat"))
        self.once_btn = QtWidgets.QPushButton(tr("1回", "Once"))
        for button in (self.repeat_btn, self.once_btn):
            button.setCheckable(True)
            button.setMinimumSize(64, 30)
            button.setStyleSheet(
                "QPushButton { background: #303538; color: white; border: none;"
                " border-radius: 6px; font-size: 13px; font-weight: bold; padding: 2px 8px;"
                " min-height: 30px; max-height: 30px; }"
                "QPushButton:checked { background: #54bce0; color: #101416; }")
            self._mode_group.addButton(button)
            mode_row.addWidget(button)
        self.repeat_btn.toggled.connect(self._on_scan_mode_changed)
        right_layout.addLayout(mode_row)

        # ★RXゲイン。RXゲイン画面と同じ設定値(rx_agc_enabled/rx_gain_db)を共有し、
        # 検索中でも変更できる。変更は少し待ってから(連打・長押しをまとめて)Plutoへ反映する。
        gain_row = QtWidgets.QHBoxLayout()
        gain_title = QtWidgets.QLabel(tr("RXゲイン", "RX Gain"))
        gain_title.setStyleSheet("color: #eeeeee; font-size: 13px; font-weight: bold;")
        gain_row.addWidget(gain_title)
        gain_row.addStretch(1)
        gain_button_style = (
            "QPushButton { background: #0c91b5; color: white; border: none;"
            " border-radius: 6px; font-size: 14px; font-weight: bold; padding: 2px 8px;"
            " min-height: 30px; max-height: 30px; }"
            "QPushButton:pressed { background: #3f96b3; }"
            "QPushButton:disabled { background: #303538; color: #6b7880; }")
        self.agc_btn = QtWidgets.QPushButton("AGC")
        self.agc_btn.setCheckable(True)
        self.agc_btn.setMinimumHeight(30)
        self.agc_btn.setStyleSheet(
            "QPushButton { background: #303538; color: white; border: none;"
            " border-radius: 6px; font-size: 12px; font-weight: bold; padding: 2px 8px;"
            " min-height: 30px; max-height: 30px; }"
            "QPushButton:checked { background: #0c91b5; }")
        self.agc_btn.toggled.connect(self._on_agc_toggled)
        gain_row.addWidget(self.agc_btn)
        self.gain_down_btn = QtWidgets.QPushButton("−")
        self.gain_up_btn = QtWidgets.QPushButton("+")
        for button, delta in ((self.gain_down_btn, -1), (self.gain_up_btn, 1)):
            button.setMinimumSize(36, 30)
            button.setStyleSheet(gain_button_style)
            button.setAutoRepeat(True)          # 長押しで連続変更
            button.setAutoRepeatDelay(400)
            button.setAutoRepeatInterval(80)
            button.clicked.connect(lambda _checked=False, d=delta: self._change_rx_gain(d))
        self.gain_label = QtWidgets.QLabel("60 dB")
        self.gain_label.setAlignment(QtCore.Qt.AlignCenter)
        self.gain_label.setMinimumWidth(60)
        self.gain_label.setStyleSheet("color: #eeeeee; font-size: 13px; font-weight: bold;")
        gain_row.addWidget(self.gain_down_btn)
        gain_row.addWidget(self.gain_label)
        gain_row.addWidget(self.gain_up_btn)
        right_layout.addLayout(gain_row)
        self._gain_apply_timer = QtCore.QTimer(self)
        self._gain_apply_timer.setSingleShot(True)
        self._gain_apply_timer.setInterval(250)
        self._gain_apply_timer.timeout.connect(self._apply_rx_gain)
        self._load_rx_gain_controls()
        self._load_scan_mode_controls()
        columns.addWidget(right, 2)

        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel(tr("検索待機中", "Search idle"))
        self.status_label.setStyleSheet("color: #176f94; font-size: 14px; font-weight: bold;")
        bottom.addWidget(self.status_label)
        bottom.addStretch(1)
        outer.addLayout(bottom)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._scan_step)
        self._update_center_label()

    def on_show(self) -> None:
        self._update_center_label()
        self._load_rx_gain_controls()
        self._load_scan_mode_controls()
        # 画面遷移のたびに、周波数画面で設定した運用周波数を中心とした範囲を
        # 自動的に取り込む(既定は±5MHz。±10MHzが必要ならプリセットボタンで
        # 広げ直す)。未設定の場合は既存の範囲欄をそのまま残す(警告は出さない
        # ―― 単に画面を開いただけで警告ダイアログが出るのは煩わしいため)。
        lo_hz = self.main_window.settings.effective_lo_hz()
        if lo_hz is not None:
            self._set_range_from_center(lo_hz, self._DEFAULT_RANGE_KHZ)
            self._set_selected_preset(self._DEFAULT_RANGE_KHZ // 1000)

    def _update_center_label(self) -> None:
        lo_hz = self.main_window.settings.effective_lo_hz()
        if lo_hz is None:
            self.center_freq_label.setText(
                tr("中心周波数: 未設定(周波数画面で設定してください)",
                   "Center frequency: Not set (set it on the Frequency screen)"))
        else:
            self.center_freq_label.setText(tr(f"中心周波数: {lo_hz / 1000:.0f} kHz", f"Center frequency: {lo_hz / 1000:.0f} kHz"))

    def _set_range_from_center(self, lo_hz: float, offset_khz: int) -> None:
        offset_hz = offset_khz * 1000
        start_khz = max(round((lo_hz - offset_hz) / 1000), 0)
        end_khz = round((lo_hz + offset_hz) / 1000)
        self.start_edit.setText(str(start_khz))
        self.end_edit.setText(str(end_khz))

    def _on_start_stop(self) -> None:
        if self._scanning:
            self._stop_scan()
        else:
            self._start_scan()

    def eventFilter(self, watched, event):
        editable = (self.step_edit,)
        if watched in editable and event.type() == QtCore.QEvent.MouseButtonPress:
            self._active_edit = watched
            watched.setStyleSheet(self._EDIT_STYLE_ACTIVE)
            for edit in editable:
                if edit is not watched:
                    edit.setStyleSheet(self._EDIT_STYLE)
            return True
        return super().eventFilter(watched, event)

    def _on_key(self, value: str) -> None:
        if self._active_edit is None:
            self._active_edit = self.step_edit
        edit = self._active_edit
        text = edit.text()
        if value == "DEL":
            if text:
                edit.setText(text[:-1])
        elif value == "C":
            edit.clear()
        elif value == "OK":
            edit.setStyleSheet(self._EDIT_STYLE)
            self._active_edit = None
        elif len(text) < 8:
            edit.setText(text + value)

    def _apply_preset_range(self, offset_khz: int) -> None:
        lo_hz = self.main_window.settings.effective_lo_hz()
        if lo_hz is None:
            error_dialog(
                self, tr("周波数未設定", "Frequency Not Set"),
                tr("周波数画面で運用周波数を設定してください", "Set the operating frequency on the Frequency screen"))
            return
        self._set_range_from_center(lo_hz, offset_khz)
        self._set_selected_preset(offset_khz // 1000)

    def _set_selected_preset(self, offset_mhz: int) -> None:
        self._selected_preset_mhz = offset_mhz
        for mhz, button in self._preset_buttons.items():
            button.setStyleSheet(
                self._PRESET_STYLE_SELECTED if mhz == offset_mhz else self._PRESET_STYLE)

    def _start_scan(self) -> None:
        # ★TxControllerはPluto+のWeb CGI(save.php)経由でpluto_dvbを操作するのみで、
        # Pi5側のIIOコンテキスト(RX_LO・RXゲイン・RSSI)には一切触れない。そのため
        # 送信中でも検索は安全に併用できる(TX→アッテネータ→RXのループバック試験で
        # 実際に信号を見つけられることを実機で確認済み)。RxController(shonan_rx.py、
        # gr-iio)はRX側のIIOコンテキストを排他的に握るため、これとは同時実行できない。
        if self.main_window.rx_controller.is_running():
            error_dialog(self, tr("検索不可", "Cannot Search"), tr("受信中は開始できません", "Cannot start while receiving"))
            return
        try:
            start_khz = int(self.start_edit.text())
            end_khz = int(self.end_edit.text())
            step_khz = int(self.step_edit.text())
        except ValueError:
            error_dialog(self, tr("入力エラー", "Input Error"),
                                           tr("周波数範囲・ステップを数値で入力してください", "Enter the frequency range and step as numbers"))
            return
        if end_khz <= start_khz:
            error_dialog(self, tr("入力エラー", "Input Error"),
                                           tr("終了周波数は開始周波数より大きくしてください", "The end frequency must be greater than the start frequency"))
            return
        if step_khz <= 0:
            error_dialog(self, tr("入力エラー", "Input Error"),
                                           tr("ステップは1kHz以上で指定してください", "The step must be 1 kHz or more"))
            return
        settings = self.main_window.settings
        self._start_freq = start_khz * 1000
        self._end_freq = end_khz * 1000
        self._step_hz = step_khz * 1000
        self._apply_rx_gain()
        self._begin_sweep()
        self._scanning = True
        self.status_label.setText(tr("検索中...", "Searching..."))
        self.search_btn.setText(tr("検索停止", "Stop Search"))
        if settings.use_on_device_demod and self.main_window.tx_controller.is_running():
            # ★検索が管理する送信として状態を揃えるため、既存の送信を一旦止めてから
            # 検索用に送信をやり直す(周波数・設定を検索開始時点のものへ確実に合わせる
            # ため)。停止は非同期(terminate())なので、実際に止まるまでポーリングする。
            self._tx_started_by_scan = True
            self.main_window.tx_controller.stop()
            QtCore.QTimer.singleShot(100, self._start_tx_after_stop_for_scan)
        elif settings.use_on_device_demod:
            self.main_window.tx_controller.start(self._scan_tx_settings())
            self._tx_started_by_scan = True
            # ★TX起動直後は送信がまだ安定していないため、送信開始から3秒待って
            # からスキャンループ(RSSI測定)を開始する。
            QtCore.QTimer.singleShot(3000, self._start_timer_if_still_scanning)
        else:
            self.timer.start(STEP_INTERVAL_MS)

    def _start_tx_after_stop_for_scan(self) -> None:
        # ★「検索停止」が押されていたら何もしない。
        if not self._scanning:
            return
        if self.main_window.tx_controller.is_running():
            # まだ停止処理中。止まるまで100msごとに確認する。
            QtCore.QTimer.singleShot(100, self._start_tx_after_stop_for_scan)
            return
        self.main_window.tx_controller.start(self._scan_tx_settings())
        QtCore.QTimer.singleShot(3000, self._start_timer_if_still_scanning)

    def _scan_tx_settings(self):
        """検索用の自動送信に使う設定。映像ソースの選択に関係なくテストパターンで送る。

        ★RSSI測定では映像の中身は関係なく、電波が出ていればよい。映像ソースが
        カメラのままだと、カメラ未接続時にTX側のffmpegが起動直後に終了して再起動を
        繰り返すだけになり、何も送信されずRSSIが変化しなかった(実機で確認)。
        保存済みの設定は変えず、この送信にだけ使う複製で映像ソースを差し替える
        (TxControllerは受け取った設定を自動再起動にも使うので、再起動後も同じ)。
        """
        return dataclasses.replace(self.main_window.settings,
                                   video_source="colorbar", use_color_bar_source=True)

    def _start_timer_if_still_scanning(self) -> None:
        # ★3秒の待機中に「検索停止」が押されていた場合は何もしない。
        if not self._scanning:
            return
        # ★TX側がffmpeg起動失敗等で実際には送信を開始できていない場合、
        # is_running()がFalseのままになる。何も送信されていない状態で
        # RSSI測定を始めても無意味なため、その場合はスキャン自体を中止する。
        if self._tx_started_by_scan and not self.main_window.tx_controller.is_running():
            self._tx_started_by_scan = False
            self._stop_scan()
            error_dialog(self, tr("送信を開始できません", "Cannot Start TX"),
                                           tr("送信の自動開始に失敗したため、検索を中止しました。",
                                              "Automatic TX start failed, so the search was canceled."))
            return
        self.timer.start(STEP_INTERVAL_MS)

    def _stop_scan(self) -> None:
        self.timer.stop()
        self._scanning = False
        if self._tx_started_by_scan:
            self._tx_started_by_scan = False
            self.main_window.tx_controller.stop()
        self.status_label.setText(tr("検索待機中", "Search idle"))
        self.search_btn.setText(tr("検索開始", "Start Search"))
        self._commit_scan_result()

    def _load_scan_mode_controls(self) -> None:
        repeat = self.main_window.settings.rssi_repeat_scan
        blocked = self.repeat_btn.blockSignals(True)
        self.repeat_btn.setChecked(repeat)
        self.once_btn.setChecked(not repeat)
        self.repeat_btn.blockSignals(blocked)

    def _on_scan_mode_changed(self, repeat: bool) -> None:
        self.main_window.settings.rssi_repeat_scan = repeat
        self.main_window.save_settings()

    def _load_rx_gain_controls(self) -> None:
        settings = self.main_window.settings
        blocked = self.agc_btn.blockSignals(True)
        self.agc_btn.setChecked(settings.rx_agc_enabled)
        self.agc_btn.blockSignals(blocked)
        self._update_rx_gain_controls()

    def _update_rx_gain_controls(self) -> None:
        settings = self.main_window.settings
        self.gain_label.setText(f"{settings.rx_gain_db} dB")
        # AGC ON中は手動ゲインは効かないので、RXゲイン画面と同様に−/+を無効にする。
        manual = not settings.rx_agc_enabled
        self.gain_down_btn.setEnabled(manual)
        self.gain_up_btn.setEnabled(manual)

    def _on_agc_toggled(self, checked: bool) -> None:
        self.main_window.settings.rx_agc_enabled = checked
        self.main_window.save_settings()
        self._update_rx_gain_controls()
        self._gain_apply_timer.start()

    def _change_rx_gain(self, delta_db: int) -> None:
        settings = self.main_window.settings
        new_gain = max(RX_GAIN_MIN_DB, min(RX_GAIN_MAX_DB, settings.rx_gain_db + delta_db))
        if new_gain == settings.rx_gain_db:
            return
        settings.rx_gain_db = new_gain
        self.main_window.save_settings()
        self._update_rx_gain_controls()
        self._gain_apply_timer.start()      # 連打・長押し中は最後の操作から250ms後に1回だけ反映

    def _iio_set_rx(self, attribute: str, value: str) -> None:
        settings = self.main_window.settings
        subprocess.run([IIO_ATTR_BIN, "-u", settings.pluto_uri, "-i", "-c", "ad9361-phy",
                        "voltage0", attribute, value], capture_output=True, timeout=2)

    def _apply_rx_gain(self) -> None:
        """RXゲイン設定(AGC/手動ゲイン)をPlutoへ反映する。検索中でも呼べる。"""
        settings = self.main_window.settings
        try:
            if settings.rx_agc_enabled:
                self._iio_set_rx("gain_control_mode", "slow_attack")
            else:
                self._iio_set_rx("gain_control_mode", "manual")
                self._iio_set_rx("hardwaregain", str(settings.rx_gain_db))
        except (subprocess.TimeoutExpired, OSError):
            return      # Plutoに届かない場合も設定値は保存済み。次回の検索・受信開始で反映される。
        if self._scanning:
            # ★ゲインが変わるとRSSIの絶対値が変わる。同じ1周の中に異なるゲインの測定値が
            # 混ざると「最も強い周波数」を誤判定するため、この周回を最初からやり直す。
            self._begin_sweep()

    def on_hide(self) -> None:
        # ★「検索停止」が押されるまで繰り返す動作のため、他の画面へ移った後も
        # スキャン(Plutoへの周波数設定・RSSI取得)が裏で続かないよう、画面を離れる時に止める。
        if self._scanning:
            self._stop_scan()

    def _begin_sweep(self) -> None:
        """1回分のスキャン(開始周波数〜終了周波数)を先頭から始める。"""
        self._current_freq = self._start_freq
        self._scan_best_rssi = None
        self._scan_best_freq = None
        self._scan_rssi_values = []
        self.rssi_graph.set_range(self._start_freq, self._end_freq)
        self.rssi_graph.set_center(self.main_window.settings.effective_lo_hz())

    def _commit_scan_result(self) -> None:
        """直前までのスキャンで得た「最も強い周波数」を確定して表示する。"""
        if self._scan_best_freq is None or not self._scan_rssi_values:
            return
        spread = max(self._scan_rssi_values) - min(self._scan_rssi_values)
        if spread < self._PEAK_THRESHOLD_DB:
            # 明らかなピークが検出できなかった場合は検索開始時の値を保持する。
            return
        self._best_rssi = self._scan_best_rssi
        self._best_freq = self._scan_best_freq
        self.best_freq_label.setText(tr(
            f"最も強い周波数: {self._best_freq / 1000:.0f} kHz (RSSI {self._best_rssi:g})",
            f"Strongest frequency: {self._best_freq / 1000:.0f} kHz (RSSI {self._best_rssi:g})"))

    def _scan_step(self) -> None:
        if self._current_freq > self._end_freq:
            if not self.main_window.settings.rssi_repeat_scan:
                # 「1回」: 範囲の終わりで自動停止する(結果の確定は_stop_scan内)。
                self._stop_scan()
                return
            # 「連続」: 1回分のスキャンが終わったら結果を確定し、「検索停止」が押される
            # まで開始周波数に戻って繰り返す。
            self._commit_scan_result()
            self._begin_sweep()
            return
        freq = self._current_freq
        settings = self.main_window.settings
        try:
            subprocess.run([IIO_ATTR_BIN, "-u", settings.pluto_uri, "-c", "ad9361-phy",
                            "altvoltage0", "frequency", str(freq)], capture_output=True, timeout=2)
            result = subprocess.run([IIO_ATTR_BIN, "-u", settings.pluto_uri, "-c", "ad9361-phy",
                                     "voltage0", "rssi"], capture_output=True, text=True, timeout=2)
            text = result.stdout.strip()
            rssi = float(text.split()[0]) if text else None
        except (subprocess.TimeoutExpired, ValueError, IndexError, OSError):
            rssi = None
        if rssi is not None:
            self.rssi_graph.add_point(freq, rssi)
            self._scan_rssi_values.append(rssi)
        if rssi is not None and (self._scan_best_rssi is None or rssi < self._scan_best_rssi):
            self._scan_best_rssi = rssi
            self._scan_best_freq = freq
            self.status_label.setText(tr(f"検索中: {freq / 1000:.0f} kHz / RSSI {rssi:g}",
                                          f"Searching: {freq / 1000:.0f} kHz / RSSI {rssi:g}"))
        self._current_freq += self._step_hz


def create(main_window) -> QtWidgets.QWidget:
    return RssiScreen(main_window)
