#!/usr/bin/env python3
"""shonan-pi4 タッチGUI エントリポイント。

「Homeがハブ、各画面はHomeから直接遷移・Homeへ直接戻る」フラットな1階層ナビゲーションを
QStackedWidgetで再現する。

起動: QT_QPA_PLATFORM=eglfs python3 main.py
(X11/Wayland不要。Pi4のDSI接続LCD/EGLFSへ直接描画する)
"""
from __future__ import annotations

import http.client
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ★QApplication構築前に設定する必要がある(QPAプラットフォーム統合が起動時に読む)。
# ソースからビルドしたOpenWnn(日本語)対応版qtvirtualkeyboardを使う
# (docs/qtvirtualkeyboard_ja_build.md参照)。
os.environ.setdefault("QT_IM_MODULE", "qtvirtualkeyboard")


def _configure_dfr0550_touch() -> None:
    """Bind Qt eglfs explicitly to the firmware DSI touchscreen."""
    for name_file in sorted(Path("/sys/class/input").glob("event*/device/name")):
        try:
            if name_file.read_text(encoding="utf-8").strip() == "raspberrypi-ts":
                event = name_file.parents[1].name
                os.environ["QT_QPA_EGLFS_DISABLE_INPUT"] = "1"
                os.environ["QT_QPA_GENERIC_PLUGINS"] = \
                    f"evdevtouch:/dev/input/{event}"
                return
        except OSError:
            continue


_configure_dfr0550_touch()

from PyQt5 import QtCore, QtNetwork, QtQuickWidgets, QtWidgets

import settings_store
from backend import (
    PTT_CHANNEL_POWER, RxController, TxController, _push_pluto_settings,
    _send_ptt_channel_state,
)
from i18n import apply_language, is_english, set_language
from widgets import error_dialog

# 電源投入(アプリ起動)からMCU1(ESP32)のGPIO26(12V電源チャンネル)をONにするまでの遅延。
MCU1_GPIO26_ON_DELAY_MS = 5_000
# プログラム終了時、MCU1のGPIO26をOFFにしてから実際に終了するまでの遅延。
MCU1_GPIO26_OFF_DELAY_SEC = 3

SCREEN_ROUTES = [
    "home", "tx", "rx", "frequency", "rssi", "symbolrate", "fec", "modulation",
    "videosource", "streamoutput", "rxgain", "txpower", "manual", "settings",
    "testequipment", "presets",
]


class MainWindow(QtWidgets.QMainWindow):
    restart_finished = QtCore.pyqtSignal(bool, str)
    CONTROL_SOCKET = "/tmp/shonan-pi4-gui.sock"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shonan for RasPI4")

        self.settings = settings_store.load()
        # tr()(Pi5版から移植した画面が使う)の表示言語を設定に合わせる。
        set_language(self.settings.language)
        # オンデバイス復調はテスト用(自局送信を受信する)のため、起動時は前回の状態に
        # かかわらず必ずOFFにする(ONのままだと送信開始時に受信も自動で始まる)。
        self.settings.use_on_device_demod = False
        self.settings.simultaneous_tx_rx_test = self.settings.use_on_device_demod
        settings_store.save(self.settings)
        self.tx_controller = TxController(self)
        self.rx_controller = RxController(self)

        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.hide()
        self._control_server = QtNetwork.QLocalServer(self)
        QtNetwork.QLocalServer.removeServer(self.CONTROL_SOCKET)
        self._control_server.newConnection.connect(self._on_control_connection)
        self._control_server.listen(self.CONTROL_SOCKET)

        self._screens = {}
        self._restart_dialog = None
        self._app_restarting = False
        self._restart_title = "アプリ再起動"
        self._build_screens()
        self._startup_restart_pending = False
        # 起動直後にPlutoを再起動し、復旧確認と設定再適用が完了してから
        # ホーム画面を表示する。Pluto再起動中にRX確認は実行しない。
        QtCore.QTimer.singleShot(0, self._startup_reboot_pluto)
        # 電源投入(アプリ起動)からMCU1_GPIO26_ON_DELAY_MS後にMCU1(ESP32)のGPIO26
        # (12V電源チャンネル)をONにする。Pi4本体のGPIOは使用しない。
        QtCore.QTimer.singleShot(MCU1_GPIO26_ON_DELAY_MS, self._power_on_mcu1_gpio26)

        self._build_keyboard_panel()
        QtWidgets.QApplication.instance().installEventFilter(self)

    def _power_on_mcu1_gpio26(self) -> None:
        host = self.settings.ptt_controller_host
        if not host:
            return
        try:
            _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "on")
        except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
            print(f"[MCU1] GPIO26 ON通知に失敗しました: {exc}", flush=True)

    def rebuild_language(self) -> None:
        """設定画面の言語変更後、全画面を再生成して切替を即時反映する。"""
        set_language(self.settings.language)
        route = "home"
        current = self.stack.currentWidget()
        for name, widget in self._screens.items():
            if widget is current:
                route = name
                break
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self._screens = {}
        self._build_screens()
        self.navigate_to(route)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Show and isinstance(watched, QtWidgets.QDialog):
            apply_language(watched, is_english(self.settings))
        return super().eventFilter(watched, event)

    def _build_keyboard_panel(self) -> None:
        """テキスト入力欄(コールサイン・備考等)フォーカス時に画面下部へ表示する
        オンスクリーンキーボード。eglfs(コンポジタなし直描画)はトップレベル
        ウィンドウを1つしか扱えないため、Qt Virtual KeyboardのInputPanel.qmlを
        別ウィンドウとしてではなくQQuickWidgetとしてこのQMainWindowに埋め込む
        (docs/qtvirtualkeyboard_ja_build.md参照)。
        """
        self.keyboard_panel = QtQuickWidgets.QQuickWidget(self)
        self.keyboard_panel.setResizeMode(
            QtQuickWidgets.QQuickWidget.SizeRootObjectToView)
        self.keyboard_panel.setSource(
            QtCore.QUrl.fromLocalFile(
                str(Path(__file__).resolve().parent
                    / "qml" / "InputPanelWrapper.qml")))
        # ★キーボードのキーをタップするとQQuickWidget自体がQtのウィジェットフォーカスを
        # 奪ってしまい、入力対象のQLineEditとの紐付けが切れて文字が入力できなくなる
        # 不具合があった(実機で確認)。NoFocusにしてタップしてもフォーカスを奪わない
        # ようにする(キー入力自体はQt Virtual Keyboard内部のInputContext経由で
        # フォーカスを移動せずに送られるため、これで問題なく動作する)。
        self.keyboard_panel.setFocusPolicy(QtCore.Qt.NoFocus)
        self.keyboard_panel.hide()
        self._active_scroll_area = None
        self._keyboard_spacer = None
        # ★実機の実タッチでは、キーボード初期表示時にフォーカスが一瞬ぶれて
        # (フィールド→None/他ウィジェット→キーボード自身、のように)
        # focusChangedが連続発火することがあり、即座にhideすると
        # スクロール位置がリセットされてしまう不具合があった。
        # 短いディレイを挟み、その間に入力欄へフォーカスが戻ればhideを取り消す。
        self._hide_timer = QtCore.QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(200)
        self._hide_timer.timeout.connect(self._hide_keyboard_panel)
        QtWidgets.QApplication.instance().focusChanged.connect(
            self._on_focus_changed)

    def _on_focus_changed(self, _old, new) -> None:
        # ★NumericKeypadDialog(周波数入力等)はQLineEditを一時的に別のトップレベル
        # ウィンドウへ移動して使う。そのフィールドがフォーカスを得た場合もこの
        # ハンドラが反応してしまうと、_scroll_field_above_keyboardが既にMainWindow
        # 配下から外れたウィジェットに対してmapTo()を呼びクラッシュする(実機で確認)。
        # このMainWindow自身のウィジェットツリー内でのフォーカス移動のみを扱う。
        # ★読み取り専用の欄(送信先ポート等)は入力できないので、フォーカスが来ても
        # キーボードを出さない。
        if (isinstance(new, (QtWidgets.QLineEdit, QtWidgets.QPlainTextEdit))
                and not new.isReadOnly() and new.window() is self):
            self._hide_timer.stop()
            self._show_keyboard_panel(new)
        elif new is not self.keyboard_panel:
            self._hide_timer.start()

    def _show_keyboard_panel(self, focused_widget: QtWidgets.QWidget) -> None:
        height = min(260, self.height() // 2)
        keyboard_top = self.height() - height
        self.keyboard_panel.setGeometry(0, keyboard_top, self.width(), height)
        self.keyboard_panel.show()
        self.keyboard_panel.raise_()
        self._scroll_field_above_keyboard(focused_widget, height)

    def _scroll_field_above_keyboard(
            self, field: QtWidgets.QWidget, keyboard_height: int) -> None:
        """フォーカスした入力欄がキーボードで隠れないようにする。単純に
        QScrollAreaをスクロールするだけでは、入力欄より下のコンテンツが
        足りずキーボード分の高さを確保できないことがあった(実機で確認、
        スクロール可能範囲がキーボードの高さより小さかった)。
        スクロール末尾に一時的な余白(スペーサー)を足してスクロール可能範囲
        自体を広げてから、絶対位置でスクロールする(「現在値+差分」方式だと
        フォーカスの連続発火で値がずれることがあったため)。"""
        scroll_area = None
        widget = field.parentWidget()
        while widget is not None:
            if isinstance(widget, QtWidgets.QScrollArea):
                scroll_area = widget
                break
            widget = widget.parentWidget()
        if scroll_area is None:
            return
        content_widget = scroll_area.widget()
        body_layout = content_widget.layout()
        if self._active_scroll_area is None:
            self._active_scroll_area = scroll_area
            # ★keyboard_heightちょうどだと、キーボードの上端ぎりぎりまで
            # 引き上げたい場合にスクロール可能範囲が足りずクランプされることが
            # あった(実機で確認)。余裕を持たせて多めに確保する。
            self._keyboard_spacer = QtWidgets.QSpacerItem(
                0, keyboard_height + 150, QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Fixed)
            body_layout.addItem(self._keyboard_spacer)
            # ★スペーサーを足しただけではQScrollAreaのスクロール範囲(maximum)が
            # 実機で即座に再計算されず、singleShot(0)後でも古い値のまま
            # クランプされてしまう不具合を確認した。レイアウトとコンテンツ
            # ウィジェットのリサイズを強制的に確定させる。
            body_layout.activate()
            content_widget.resize(content_widget.sizeHint())
            content_widget.updateGeometry()

        def apply_scroll() -> None:
            # ★QApplication自体のクリック時自動フォーカス処理は、フィールド側の
            # mousePressEvent上書き(例: frequency.pyのNumericKeypadDialog起動)より
            # 先に働くことがある。その場合ここがスケジュールされた直後に、同じ
            # クリック処理の中でフィールドが別のトップレベルウィンドウ(ダイアログ等)
            # へ再親化されてしまい、発火時にはfield.mapTo(content_widget, ...)が
            # 既にcontent_widgetの子孫でなくなったウィジェットを指してクラッシュする
            # (実機で確認)。発火時点でまだMainWindow配下にあるか再検証する。
            if field.window() is not self:
                return
            # ★キーボードのすぐ上ぎりぎりではなく、タイトルバーの下あたりまで
            # 入力欄を引き上げる(キーボードに隠れるとの指摘を受けて余裕を持たせた)。
            target_top = 50
            field_y_in_content = field.mapTo(content_widget, QtCore.QPoint(0, 0)).y()
            bar = scroll_area.verticalScrollBar()
            new_value = max(0, min(bar.maximum(), field_y_in_content - target_top))
            bar.setValue(new_value)

        QtCore.QTimer.singleShot(50, apply_scroll)

    def _hide_keyboard_panel(self) -> None:
        self.keyboard_panel.hide()
        if self._active_scroll_area is not None:
            body_layout = self._active_scroll_area.widget().layout()
            body_layout.removeItem(self._keyboard_spacer)
            self._active_scroll_area.verticalScrollBar().setValue(0)
            self._active_scroll_area = None
            self._keyboard_spacer = None

    def _build_screens(self) -> None:
        # 各screens.*モジュールは create(main_window) -> QWidget を提供する規約にする。
        from screens import (
            fec, frequency, home, manual, modulation, rssi, rx, rxgain,
            settings as settings_screen, streamoutput, symbolrate,
            testequipment, tx, txpower, videosource, presets,
        )

        modules = {
            "home": home, "tx": tx, "rx": rx, "frequency": frequency, "rssi": rssi,
            "symbolrate": symbolrate, "fec": fec, "modulation": modulation,
            "videosource": videosource, "streamoutput": streamoutput,
            "rxgain": rxgain, "txpower": txpower, "manual": manual,
            "settings": settings_screen, "testequipment": testequipment,
            "presets": presets,
        }
        for route, module in modules.items():
            widget = module.create(self)
            self._screens[route] = widget
            self.stack.addWidget(widget)

    def navigate_to(self, route: str) -> None:
        widget = self._screens[route]
        current = self.stack.currentWidget()
        if current is not widget and hasattr(current, "on_hide"):
            current.on_hide()
        if hasattr(widget, "on_show"):
            widget.on_show()
        apply_language(widget, is_english(self.settings))
        self.stack.setCurrentWidget(widget)

    def _on_control_connection(self) -> None:
        client = self._control_server.nextPendingConnection()
        if client is None:
            return
        client.readyRead.connect(lambda s=client: self._handle_control_socket(s))
        client.disconnected.connect(client.deleteLater)

    def _handle_control_socket(self, client) -> None:
        command = bytes(client.readAll()).decode("utf-8", errors="replace").strip()
        if command == "tx":
            self.navigate_to("tx")
            self._screens["tx"]._on_start_stop()
        elif command == "rx":
            self.navigate_to("rx")
            # 画面操作と同じ開始経路を通し、同時動作設定時はTXも開始する。
            self._screens["rx"]._on_start_stop()
        elif command == "fec":
            self.navigate_to("fec")
        elif command == "symbolrate":
            self.navigate_to("symbolrate")
        elif command == "frequency":
            self.navigate_to("frequency")
        elif command == "modulation":
            self.navigate_to("modulation")
        elif command == "videosource":
            self.navigate_to("videosource")
        elif command == "streamoutput":
            self.navigate_to("streamoutput")
        elif command == "rxgain":
            self.navigate_to("rxgain")
        elif command == "txpower":
            self.navigate_to("txpower")
        elif command == "settings":
            self.navigate_to("settings")
        elif command == "testequipment":
            self.navigate_to("testequipment")
        elif command in ("videosource:camera", "videosource:colorbar"):
            # 映像ソース画面のボタンを押すのと同じ(ファイル選択はダイアログが出るため対象外)。
            self.navigate_to("videosource")
            self._screens["videosource"]._source_buttons[command.split(":", 1)[1]].click()
        elif command == "testequipment:run":
            # 機器試験画面へ移動して「全体試験」を実行する(送受信停止中のみ開始される)。
            self.navigate_to("testequipment")
            self._screens["testequipment"]._on_run()
        elif command == "presets":
            self.navigate_to("presets")
        elif command == "rssi":
            # Pi5版と同じく、RSSI測定画面へ移動して検索を開始/停止する。
            self.navigate_to("rssi")
            self._screens["rssi"]._on_start_stop()
        elif command.startswith("rssi_mode:"):
            # 検索方法の切替(rssi_mode:once / rssi_mode:repeat)。検索は開始しない。
            self.navigate_to("rssi")
            rssi = self._screens["rssi"]
            button = rssi.once_btn if command.endswith(":once") else rssi.repeat_btn
            button.click()
        elif command == "home":
            self.navigate_to("home")
        elif command == "shutdown_dialog":
            self._screens["home"]._on_shutdown_clicked()
        elif command == "cancel_dialog":
            dialog = QtWidgets.QApplication.activeModalWidget()
            if dialog is not None:
                dialog.reject()
            else:
                # linuxfbでは重ね表示(widgets._run_as_overlay)のダイアログがモーダル扱いに
                # ならないため、表示中のQDialogを探して閉じる。
                for dialog in reversed(self.findChildren(QtWidgets.QDialog)):
                    if dialog.isVisible():
                        dialog.reject()
                        break
        elif command == "screenshot":
            self.capture_screenshot()
        elif command == "restart":
            self.restart_app()
        elif command.startswith("navigate:"):
            # 任意の画面へ移動するだけ(送受信は開始しない)。Pi5版と同じ書式。
            route = command[len("navigate:"):]
            if route in self._screens:
                self.navigate_to(route)
        # ★shutdown_dialog等はダイアログを閉じるまでここへ戻らず、その間に送信側が切断すると
        # clientは削除済みになる。削除済みのソケットへ書くとGUIごと異常終了するため無視する。
        try:
            client.write(b"OK\n")
            client.flush()
        except RuntimeError:
            pass

    def save_settings(self) -> None:
        settings_store.save(self.settings)

    def restart_app(self) -> None:
        if self._app_restarting:
            return
        self.tx_controller.stop()
        self.rx_controller.stop()
        self.save_settings()
        self._startup_restart_pending = True
        self.stack.hide()
        self._begin_pluto_restart("アプリ再起動", "アプリを再起動しています…")

    def _startup_reboot_pluto(self) -> None:
        self._startup_restart_pending = True
        try:
            host = self.settings.pluto_host()
        except ValueError:
            host = ""
        if not host:
            self._startup_restart_pending = False
            self.navigate_to("home")
            self.stack.show()
            self.rx_controller.run_iio_preflight(self.settings)
            return
        self._begin_pluto_restart("起動時Pluto再起動", "アプリ起動時にPlutoも再起動しています…")

    def _begin_pluto_restart(self, title: str, message_text: str) -> None:
        if self._app_restarting:
            return
        self._app_restarting = True
        self._restart_title = title
        # ★QDialog(別トップレベルウィンドウ)はQT_QPA_PLATFORM=linuxfbでは
        # メインウィンドウの上に重ねて描画されず、画面中央にメッセージが
        # 表示されない不具合を実機で確認した(linuxfbはKMS/eglfsと違い、
        # 複数トップレベルウィンドウの合成に対応しないため)。同一ウィンドウ内の
        # 子Widgetとしてstackの上に重ねるオーバーレイ方式に変更する。
        overlay = QtWidgets.QWidget(self)
        overlay.setStyleSheet("background: rgba(0, 0, 0, 200);")
        # ★起動直後(showFullScreen()直後)はself.rect()がまだ実際の画面サイズに
        # 更新されておらず小さいデフォルトサイズのままになることがあるため、
        # 画面自体のサイズから取得する。
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geo = screen.geometry() if screen is not None else self.rect()
        overlay.setGeometry(0, 0, screen_geo.width(), screen_geo.height())
        outer = QtWidgets.QVBoxLayout(overlay)
        outer.setContentsMargins(0, 0, 0, 0)
        panel = QtWidgets.QFrame(overlay)
        panel.setFixedSize(500, 240 if title in ("起動時Pluto再起動", "アプリ再起動") else 210)
        panel.setStyleSheet(
            "QFrame { background: #0a0c0d; color: white; border-radius: 12px; } "
            "QLabel { color: white; }"
        )
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)
        icon = QtWidgets.QLabel("⟳")
        icon.setAlignment(QtCore.Qt.AlignCenter)
        icon.setStyleSheet("color: #0c9bc0; font-size: 52px; font-weight: bold;")
        layout.addWidget(icon)
        message = QtWidgets.QLabel(message_text)
        message.setAlignment(QtCore.Qt.AlignCenter)
        message.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(message)
        if title in ("起動時Pluto再起動", "アプリ再起動"):
            sub_message = QtWidgets.QLabel("Plutoも再起動しています…")
            sub_message.setAlignment(QtCore.Qt.AlignCenter)
            sub_message.setStyleSheet("font-size: 14px; color: #0c9bc0;")
            layout.addWidget(sub_message)
            note = QtWidgets.QLabel("Plutoの再起動に20秒以上かかる場合は確認をスキップしてホーム画面表示")
            note.setAlignment(QtCore.Qt.AlignCenter)
            note.setWordWrap(True)
            note.setStyleSheet("font-size: 11px; color: #aeb9bd;")
            layout.addWidget(note)
        center_row = QtWidgets.QHBoxLayout()
        center_row.addStretch(1)
        center_row.addWidget(panel)
        center_row.addStretch(1)
        outer.addStretch(1)
        outer.addLayout(center_row)
        outer.addStretch(1)
        self._restart_dialog = overlay
        self.restart_finished.connect(self._finish_app_restart)
        overlay.show()
        overlay.raise_()
        if title in ("起動時Pluto再起動", "アプリ再起動"):
            QtCore.QTimer.singleShot(20000, self._skip_startup_restart)
        threading.Thread(target=self._restart_pluto_and_restore, daemon=True).start()

    def _skip_startup_restart(self) -> None:
        if not self._app_restarting or not self._startup_restart_pending:
            return
        print("[pluto-startup] confirmation timeout; continuing to home screen", flush=True)
        if self._restart_dialog is not None:
            self._restart_dialog.hide()
            self._restart_dialog.deleteLater()
            self._restart_dialog = None
        try:
            self.restart_finished.disconnect(self._finish_app_restart)
        except TypeError:
            pass
        self._startup_restart_pending = False
        self._app_restarting = False
        self.navigate_to("home")
        self.stack.show()

    def _restart_pluto_and_restore(self) -> None:
        try:
            host = self.settings.pluto_host()
            cmd = ["sshpass", "-p", "analog", "ssh",
                   "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=6",
                   "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no",
                   f"root@{host}", "reboot"]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                print(f"[pluto-startup] reboot command finished rc={result.returncode}", flush=True)
            except (OSError, subprocess.TimeoutExpired):
                print("[pluto-startup] reboot command ended while Pluto was restarting", flush=True)

            # 再起動前の接続を復旧済みと誤判定しないよう、まずPlutoが
            # オフラインになったことを確認してから復旧を待つ。
            print("[pluto-startup] waiting for Pluto to go offline", flush=True)
            time.sleep(5)
            offline_deadline = time.monotonic() + 20
            went_offline = False
            while time.monotonic() < offline_deadline:
                if not self._pluto_is_online(host):
                    went_offline = True
                    print("[pluto-startup] Pluto offline confirmed", flush=True)
                    break
                time.sleep(1)
            if not went_offline:
                print("[pluto-startup] Pluto offline was not confirmed", flush=True)
                self.restart_finished.emit(False, "Plutoの再起動完了を確認できませんでした")
                return

            print("[pluto-startup] waiting for Pluto Web UI and IIO", flush=True)
            deadline = time.monotonic() + 90
            online = False
            while time.monotonic() < deadline:
                if self._pluto_is_online(host):
                    online = True
                    print("[pluto-startup] Pluto Web UI and IIO online confirmed", flush=True)
                    break
                time.sleep(2)
            if not online:
                print("[pluto-startup] Pluto online was not confirmed", flush=True)
                self.restart_finished.emit(False, "Plutoへ再接続できませんでした")
                return
            lo_hz = self.settings.effective_lo_hz()
            if lo_hz is None:
                self.restart_finished.emit(False, "周波数が未設定です")
                return
            verified = False
            last_error = "設定値の読み戻しに失敗しました"
            for attempt in range(5):
                try:
                    _push_pluto_settings(self.settings, lo_hz)
                    if self._wait_for_pluto_settings(host, self.settings, lo_hz, timeout=8):
                        verified = True
                        print(f"[pluto-startup] settings verified (attempt={attempt + 1})", flush=True)
                        break
                    last_error = f"Pluto設定の確認に失敗しました (attempt={attempt + 1})"
                except OSError as exc:
                    last_error = f"Pluto設定書き込みに失敗しました (attempt={attempt + 1}): {exc}"
                    print(f"[pluto-startup] {last_error}", flush=True)
                time.sleep(1)
            if not verified:
                raise RuntimeError(last_error)
            print("[pluto-startup] settings reapplied and verified; startup restart complete", flush=True)
            self.restart_finished.emit(True, "設定を再適用しました")
        except Exception as exc:  # noqa: BLE001 - UIへ失敗を返して再起動処理を完了する
            self.restart_finished.emit(False, f"Pluto設定の再適用に失敗しました: {exc}")

    @staticmethod
    def _pluto_is_online(host: str) -> bool:
        try:
            request = urllib.request.Request(f"http://{host}/pluto.php", method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                if not 200 <= response.status < 300:
                    return False
            with socket.create_connection((host, 30431), timeout=3):
                return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def _wait_for_pluto_settings(
        host: str, settings: settings_store.AppSettings, lo_hz: float, timeout: float
    ) -> bool:
        """SSHで書き込んだDVB-S2設定をPlutoから読み戻して確認する。"""
        expected = {
            "freq": f"{lo_hz / 1_000_000:.3f}",
            "channel": "Custom",
            "mode": "DVBS2",
            "mod": settings.modulation_scheme,
            "sr": str(round(settings.symbol_rate_msps * 1000)),
            "fec": settings.fec_rate.replace("/", ""),
            "pilots": "On",
            "frame": "LongFrame",
            "power": str(int(settings.tx_power_db)),
            "rolloff": "0.35",
        }
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                command = [
                    "sshpass", "-p", "analog", "ssh",
                    "-o", "StrictHostKeyChecking=accept-new",
                    "-o", "ConnectTimeout=6",
                    "-o", "PreferredAuthentications=password",
                    "-o", "PubkeyAuthentication=no",
                    f"root@{host}", "cat", "/www/settings.txt",
                ]
                result = subprocess.run(command, capture_output=True, text=True, timeout=8)
                if result.returncode != 0:
                    raise OSError(result.stderr.strip() or "SSH読み戻しに失敗しました")
                text = result.stdout
                actual = {}
                for line in text.splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        actual[parts[0]] = parts[1].strip()
                if all(actual.get(key) == value for key, value in expected.items()):
                    return True
            except (OSError, ValueError):
                pass
            time.sleep(1)
        return False

    @QtCore.pyqtSlot(bool, str)
    def _finish_app_restart(self, success: bool, detail: str) -> None:
        startup_restart = self._startup_restart_pending
        if self._restart_dialog is not None:
            self._restart_dialog.hide()
            self._restart_dialog.deleteLater()
            self._restart_dialog = None
        try:
            self.restart_finished.disconnect(self._finish_app_restart)
        except TypeError:
            pass
        self._app_restarting = False
        if startup_restart:
            self._startup_restart_pending = False
            self.navigate_to("home")
            self.stack.show()
            self.rx_controller.run_iio_preflight(self.settings)
        if not success:
            error_dialog(self, self._restart_title, detail)

    def capture_screenshot(self) -> None:
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return
        pixmap = screen.grabWindow(0)
        if not pixmap.isNull():
            pixmap.save("/tmp/shonan_lcd_actual.png", "PNG")

    def closeEvent(self, event) -> None:
        self.tx_controller.stop()
        self.rx_controller.stop()
        # 先にMCU1(ESP32)のGPIO26をOFFにしてから、実際の終了(super().closeEvent)を
        # MCU1_GPIO26_OFF_DELAY_SEC秒待つ(電源系統が安全に落ちきるのを待つ猶予)。
        # Pi4本体のGPIOは使用しない。
        host = self.settings.ptt_controller_host
        if host:
            try:
                _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "off")
            except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
                print(f"[MCU1] GPIO26 OFF通知に失敗しました: {exc}", flush=True)
            time.sleep(MCU1_GPIO26_OFF_DELAY_SEC)
        super().closeEvent(event)


_GLOBAL_STYLESHEET = """
QWidget { background-color: black; color: #eeeeee; font-size: 14px; }
QPushButton {
  background-color: #1d4388; color: white; font-weight: bold;
  border: 2px solid #2c5aa8; border-radius: 8px; padding: 8px;
  outline: none;
}
QPushButton:pressed { background-color: #102a5c; }
QPushButton:disabled { background-color: #999999; border-color: #777777; color: #dddddd; }
QPushButton:focus { outline: none; }
QRadioButton, QCheckBox { color: #eeeeee; }
QRadioButton::indicator, QCheckBox::indicator { width: 28px; height: 28px; }
QGroupBox { font-weight: bold; color: #eeeeee; border: 1px solid #555555; border-radius: 6px; margin-top: 8px; }
QLineEdit, QComboBox { background-color: #222222; color: #eeeeee; border: 1px solid #555555; border-radius: 4px; padding: 6px; }
QScrollArea { background-color: black; border: none; }
"""


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    # ★QT_QPA_PLATFORMのlinuxfb:...:nocursorオプションだけではマウスカーソルが
    # 消えなかった(実機で確認)。タッチ専用キオスク用途のためアプリ側でも
    # カーソルを明示的に非表示にする(プラットフォームに依存せず確実)。
    app.setOverrideCursor(QtCore.Qt.BlankCursor)
    app.setStyleSheet(_GLOBAL_STYLESHEET)
    window = MainWindow()
    window.showFullScreen()
    signal.signal(signal.SIGUSR1, lambda _signum, _frame: QtCore.QTimer.singleShot(
        0, window.capture_screenshot))
    signal.signal(signal.SIGUSR2, lambda _signum, _frame: QtCore.QTimer.singleShot(
        0, lambda: (window.navigate_to("tx"), window._screens["tx"]._on_start_stop())))
    signal.signal(signal.SIGWINCH, lambda _signum, _frame: QtCore.QTimer.singleShot(
        0, lambda: (window.navigate_to("rx"), window.rx_controller.start(window.settings))))
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
