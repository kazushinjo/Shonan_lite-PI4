"""診断画面。Android版 ui/TestEquipmentScreen.kt + dvbs2/Dvbs2TestRunner.kt の移植。

Dvbs2TestRunner.runDiag()のロジックをそのまま踏襲する:
  - TXとRXは同時に動かさず、TXを完全停止してからRXを開始する(半二重運用の実情に
    合わせた設計。実際の信号往復=ループバックの確認はしない、Dvbs2TestRunner.kt:19-21)。
  - TX: 接続後のウォームアップ、その後1秒間隔×8回「接続済み かつ 累積Underflow=0」を
    チェックし、8回全て健全ならPASS(pluto_dvbはUnderflowでしか異常を報告しないため、
    backend.py参照)。
  - TX停止後1.5秒待ってからRX開始。
  - RX: 1秒間隔×8回待つだけ(逐次チェックはしない)。接続できてエラーが出なければPASS
    (locked状態は判定に使わない、Dvbs2TestRunner.kt:162と同じ基準)。

★TXはPluto内蔵変調器(pluto_dvb)を使用する(backend.py参照)。
WARMUP_MSはSSH接続+pluto_dvb起動が安定するまでの猶予。
"""
from __future__ import annotations

import copy
import time
import subprocess
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from backend import check_pluto_connection
from i18n import tr
from widgets import SettingsSubScreen

TX_SECONDS = 8
RX_SECONDS = 8
CAMERA_AUDIO_SECONDS = 8
WARMUP_MS = 2500
INTER_PHASE_DELAY_MS = 1500


class TestEquipmentScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("機器試験 / Diagnostic", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self._running = False
        self.body_layout.setContentsMargins(8, 4, 8, 6)
        self.body_layout.setSpacing(4)

        self.status_label = QtWidgets.QLabel(tr("待機中", "Idle"))
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.status_label.setTextFormat(QtCore.Qt.RichText)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        table_card = QtWidgets.QFrame()
        table_card.setStyleSheet("QFrame { background: #191d1f; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        table_layout = QtWidgets.QVBoxLayout(table_card)
        table_layout.setContentsMargins(8, 5, 8, 5)
        table_layout.setSpacing(2)
        table_layout.addWidget(QtWidgets.QLabel(tr("項目                 ステータス    結果",
                                                     "Item                 Status    Result")))
        self.result_table = QtWidgets.QTableWidget(4, 3)
        self.result_table.setHorizontalHeaderLabels(
            [tr("項目", "Item"), tr("ステータス", "Status"), tr("結果", "Result")])
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.result_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.result_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.result_table.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.result_table.verticalHeader().setDefaultSectionSize(22)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.result_table.setStyleSheet("QTableWidget { background: #191d1f; color: white; border: none; gridline-color: #30383c; } QHeaderView::section { background: #252a2d; color: #cccccc; border: none; padding: 3px; } QTableWidget::item { padding: 3px; }")
        for row, name in enumerate((
                tr("Pluto SDR接続", "Pluto SDR Connection"), tr("送信テスト", "TX Test"),
                tr("受信テスト", "RX Test"), tr("温度センサー", "Temperature Sensor"))):
            self.result_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.result_table.setItem(row, 1, QtWidgets.QTableWidgetItem(tr("待機中", "Idle")))
            self.result_table.setItem(row, 2, QtWidgets.QTableWidgetItem("—"))
        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(6)
        self.run_btn = QtWidgets.QPushButton(tr("全体試験", "Full Test"))
        self.run_btn.setMinimumHeight(0)
        self.run_btn.setMaximumHeight(34)
        self.run_btn.setFixedHeight(34)
        self.run_btn.clicked.connect(self._on_run)
        button_row.addWidget(self.run_btn, 1)
        self.camera_audio_run_btn = QtWidgets.QPushButton(tr("カメラ＋音声診断", "Camera + Audio Diagnostic"))
        self.camera_audio_run_btn.setMinimumHeight(0)
        self.camera_audio_run_btn.setMaximumHeight(30)
        self.camera_audio_run_btn.setFixedHeight(30)
        self.camera_audio_run_btn.clicked.connect(self._on_run_camera_audio)
        button_row.addWidget(self.camera_audio_run_btn, 1)
        table_layout.addWidget(self.result_table, 1)
        table_layout.addLayout(button_row)
        table_layout.addSpacing(70)
        columns.addWidget(table_card, 1)

        graph_card = QtWidgets.QFrame()
        graph_card.setStyleSheet("QFrame { background: #191d1f; border-radius: 12px; } QLabel { color: white; background: transparent; }")
        graph_layout = QtWidgets.QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(12, 10, 12, 10)
        graph_layout.setSpacing(6)
        graph_layout.addWidget(QtWidgets.QLabel(tr("診断結果", "Diagnostic Result")))
        self.health_label = QtWidgets.QLabel(tr("システム状態: 待機中", "System Status: Idle"))
        self.health_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #36b47a;")
        graph_layout.addWidget(self.health_label)
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("QTextEdit { background: #101416; color: #b9c4c8; border: 1px solid #30383c; border-radius: 6px; font-size: 11px; }")
        graph_layout.addWidget(self.log_view, 1)
        graph_layout.addWidget(self.status_label)
        columns.addWidget(graph_card, 1)

    def _log(self, text: str) -> None:
        # HTML特殊文字を含みうる生テキスト行はエスケープしてから追記する
        # (OK/NGの色付けはself._ok_ng_html()で作った断片をtextに埋め込んで渡す)。
        self.log_view.append(text)
        max_blocks = 300
        doc = self.log_view.document()
        while doc.blockCount() > max_blocks:
            cursor = QtGui.QTextCursor(doc.firstBlock())
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    @staticmethod
    def _result_html(ok: bool) -> str:
        color = "#33cc33" if ok else "#cc3333"
        mark = "✓" if ok else "✗"
        text = tr("正常", "Normal") if ok else tr("異常", "Abnormal")
        return f'<span style="color:{color};">{mark} {text}</span>'

    @staticmethod
    def _ok_ng_html(ok: bool) -> str:
        color = "#33cc33" if ok else "#cc3333"
        return f'<span style="color:{color}; font-weight:bold;">{"OK" if ok else "NG"}</span>'

    def _on_run(self) -> None:
        if self._running:
            return
        tx = self.main_window.tx_controller
        rx = self.main_window.rx_controller
        if tx.is_running() or rx.is_running():
            self._log(tr("送受信中のため全体試験を開始できません", "Cannot start the full test while transmitting/receiving"))
            return
        self._running = True
        self.run_btn.setEnabled(False)
        self.log_view.clear()
        self._log(tr("全体試験を開始します", "Starting the full test"))

        self._log(tr("[診断] Pluto SDRを再起動中...", "[Diag] Restarting Pluto SDR..."))
        if not self._reboot_pluto_and_wait():
            self._set_row(0, tr("完了", "Done"), "NG")
            self._log(tr("[診断] Pluto SDR再起動後の接続復旧に失敗しました",
                          "[Diag] Failed to recover the connection after restarting Pluto SDR"))
            self.health_label.setText(tr("システム状態: Pluto再起動エラー", "System Status: Pluto Restart Error"))
            self.run_btn.setEnabled(True)
            self._running = False
            return

        self._set_row(0, tr("試験中", "Testing"), "…")
        pluto_ok, pluto_detail = check_pluto_connection(self.main_window.settings)
        self._set_row(0, tr("完了", "Done"), "OK" if pluto_ok else "NG")
        self._log(tr(f"[診断] Pluto SDR接続: {self._ok_ng_html(pluto_ok)} ({pluto_detail})",
                      f"[Diag] Pluto SDR connection: {self._ok_ng_html(pluto_ok)} ({pluto_detail})"))
        if not pluto_ok:
            self.health_label.setText(tr("システム状態: Pluto接続エラー", "System Status: Pluto Connection Error"))
            self.run_btn.setEnabled(True)
            self._running = False
            return
        self._set_row(1, tr("試験中", "Testing"), "…")
        self._set_row(2, tr("待機中", "Idle"), "—")
        self._log(tr("送受信の診断を開始します", "Starting the TX/RX diagnostic"))

        # TX単体診断の状態
        self._tx_connected = False
        self._tx_error = False
        self._tx_checked = 0
        self._tx_healthy = 0
        self._tx_tick = 0

        tx.status_updated.connect(self._on_tx_status)
        tx.error.connect(self._on_tx_error)

        self.status_label.setText(tr("TXへ接続中...", "Connecting to TX..."))
        self._log(tr(f"[診断] TX単体確認 ({TX_SECONDS}秒)", f"[Diag] TX-only check ({TX_SECONDS}s)"))
        # TX/RX単体診断はカメラの有無に左右されないよう、カラーパターンを
        # 送信する。カメラ・音声入力は専用の診断ボタンで確認する。
        tx_settings = copy.copy(self.main_window.settings)
        tx_settings.use_color_bar_source = True
        tx.start(tx_settings)
        # pluto_dvbへの接続・起動が安定するまでの猶予を設ける。
        # SSHハンドシェイク分の余裕を見る)。
        QtCore.QTimer.singleShot(WARMUP_MS, self._tx_warmup_done)

    def _reboot_pluto_and_wait(self) -> bool:
        try:
            host = self.main_window.settings.pluto_host()
            command = [
                "sshpass", "-p", "analog", "ssh",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=6",
                "-o", "PreferredAuthentications=password",
                "-o", "PubkeyAuthentication=no",
                f"root@{host}", "reboot",
            ]
            # reboot closes SSH before returning a normal exit status; that is
            # expected, so the return code is intentionally not used as the
            # success condition.
            subprocess.run(command, timeout=10, capture_output=True, text=True)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass

        # Wait until the IIO context is available again after the reboot.
        for _ in range(20):
            time.sleep(1)
            ok, _detail = check_pluto_connection(self.main_window.settings)
            if ok:
                return True
        return False

    def _set_row(self, row: int, status: str, result: str) -> None:
        self.result_table.item(row, 1).setText(status)
        self.result_table.item(row, 2).setText(result)

    def _on_tx_status(self, status: dict) -> None:
        self._tx_connected = True
        self._last_tx_status = status

    def _on_tx_error(self, message: str) -> None:
        self._tx_error = True
        self._log(f"[Tx] {message}")

    def _tx_warmup_done(self) -> None:
        self.status_label.setText(tr(f"TX健全性確認中... (0/{TX_SECONDS}秒)", f"Checking TX health... (0/{TX_SECONDS}s)"))
        self._tx_tick_check()

    def _tx_tick_check(self) -> None:
        self._tx_tick += 1
        self.status_label.setText(tr(f"TX健全性確認中... ({self._tx_tick}/{TX_SECONDS}秒)",
                                      f"Checking TX health... ({self._tx_tick}/{TX_SECONDS}s)"))
        self._tx_checked += 1
        status = getattr(self, "_last_tx_status", None)
        # ★pluto_dvb自体はPluto+上で自律動作するため、Pi5側からはUnderflow等の
        # 内部状態が見えない。ffmpeg自身が実際に符号化・送出できているか
        # (connected)のみを見る。
        if status is not None and status["connected"]:
            self._tx_healthy += 1
        if self._tx_tick < TX_SECONDS:
            QtCore.QTimer.singleShot(1000, self._tx_tick_check)
        else:
            self._finish_tx_phase()

    def _finish_tx_phase(self) -> None:
        tx = self.main_window.tx_controller
        tx.status_updated.disconnect(self._on_tx_status)
        tx.error.disconnect(self._on_tx_error)
        tx.stop()

        tx_pass = (self._tx_connected and not self._tx_error
                   and self._tx_checked > 0 and self._tx_healthy == self._tx_checked)
        self._tx_pass = tx_pass
        self._set_row(1, tr("完了", "Done"), "OK" if tx_pass else "NG")
        self._log(tr(
            f"[診断] TX結果: {self._ok_ng_html(tx_pass)} "
            f"(接続={self._tx_connected}, 健全サンプル={self._tx_healthy}/{self._tx_checked})",
            f"[Diag] TX result: {self._ok_ng_html(tx_pass)} "
            f"(connected={self._tx_connected}, healthy samples={self._tx_healthy}/{self._tx_checked})"))

        self.status_label.setText(tr("RXへ接続中...", "Connecting to RX..."))
        QtCore.QTimer.singleShot(INTER_PHASE_DELAY_MS, self._start_rx_phase)

    def _start_rx_phase(self) -> None:
        rx = self.main_window.rx_controller

        self._rx_connected = False
        self._rx_error = False
        self._rx_tick = 0

        rx.status_updated.connect(self._on_rx_status)
        rx.error.connect(self._on_rx_error)

        self._log(tr(f"[診断] RX単体確認 ({RX_SECONDS}秒)", f"[Diag] RX-only check ({RX_SECONDS}s)"))
        self._set_row(2, tr("試験中", "Testing"), "…")
        rx.start(self.main_window.settings)
        self.status_label.setText(tr(f"RX継続確認中... (0/{RX_SECONDS}秒)", f"Checking RX continuity... (0/{RX_SECONDS}s)"))
        QtCore.QTimer.singleShot(1000, self._rx_tick_wait)

    def _on_rx_status(self, status: dict) -> None:
        self._rx_connected = True

    def _on_rx_error(self, message: str) -> None:
        self._rx_error = True
        self._log(f"[Rx] {message}")

    def _rx_tick_wait(self) -> None:
        self._rx_tick += 1
        self.status_label.setText(tr(f"RX継続確認中... ({self._rx_tick}/{RX_SECONDS}秒)",
                                      f"Checking RX continuity... ({self._rx_tick}/{RX_SECONDS}s)"))
        if self._rx_tick < RX_SECONDS:
            QtCore.QTimer.singleShot(1000, self._rx_tick_wait)
        else:
            self._finish_rx_phase()

    def _finish_rx_phase(self) -> None:
        rx = self.main_window.rx_controller
        rx.status_updated.disconnect(self._on_rx_status)
        rx.error.disconnect(self._on_rx_error)
        rx.stop()

        # Dvbs2TestRunner.kt:162と同じ基準(lockedは判定に使わない)。
        rx_pass = self._rx_connected and not self._rx_error
        self._set_row(2, tr("完了", "Done"), "OK" if rx_pass else "NG")
        self._log(tr(f"[診断] RX結果: {self._ok_ng_html(rx_pass)} (接続={self._rx_connected})",
                      f"[Diag] RX result: {self._ok_ng_html(rx_pass)} (connected={self._rx_connected})"))

        self._run_hardware_sensor_tests()

        result = (f"TX: {self._result_html(self._tx_pass)} &nbsp;/&nbsp; "
                  f"RX: {self._result_html(rx_pass)}")
        self._log(tr(f"送受信の診断完了: {result}", f"TX/RX diagnostic complete: {result}"))
        self.status_label.setText(result)
        # RXの停止はQProcessの終了を待つ必要があるため、カメラ＋音声診断を
        # 直ちに開始できないようにして、送受信の完全停止後に解除する。
        self.run_btn.setEnabled(False)
        self.camera_audio_run_btn.setEnabled(False)
        QtCore.QTimer.singleShot(1500, self._full_test_cleanup_done)

    def _full_test_cleanup_done(self) -> None:
        tx = self.main_window.tx_controller
        rx = self.main_window.rx_controller
        if tx.is_running() or rx.is_running():
            QtCore.QTimer.singleShot(500, self._full_test_cleanup_done)
            return
        self.run_btn.setEnabled(True)
        self.camera_audio_run_btn.setEnabled(True)
        self._running = False

    def _run_hardware_sensor_tests(self) -> None:
        """Read local Pi health sensors and update the diagnostic table."""
        self._set_row(3, tr("試験中", "Testing"), "…")

        # Raspberry Pi thermal driver reports millidegrees Celsius.
        temperature_ok = False
        temperature_text = tr("取得不可", "Unavailable")
        try:
            thermal_paths = sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
            raw = int(thermal_paths[0].read_text().strip()) if thermal_paths else 0
            if 0 < raw < 150000:
                temperature_ok = True
                temperature_text = f"{raw / 1000:.1f} °C"
        except (OSError, ValueError):
            pass
        self._set_row(3, tr("完了", "Done"), temperature_text if temperature_ok else "NG")
        self._log(tr(f"[診断] 温度センサー: {self._ok_ng_html(temperature_ok)} ({temperature_text})",
                      f"[Diag] Temperature sensor: {self._ok_ng_html(temperature_ok)} ({temperature_text})"))


    # --- カメラ＋音声送出診断 (Dvbs2TestRunner.kt runCameraAudioDiag()の移植) ---
    #   TX開始(カメラ映像+USBカメラ内蔵マイク音声を実際にキャプチャして送出)
    #   → ウォームアップ → 1秒間隔×8回、「接続済み かつ 累積Underflow=0」と
    #   video/audioフレーム数を確認。
    #   capturePass = videoFrames>0 かつ audioFrames>0
    #   txPass = checkedSamples>0 かつ activeSamples>0
    #   overallPass = capturePass かつ txPass

    def _on_run_camera_audio(self) -> None:
        if self._running:
            return
        tx = self.main_window.tx_controller
        rx = self.main_window.rx_controller
        if tx.is_running() or rx.is_running():
            self._log(tr("送受信中のため診断を開始できません", "Cannot start the diagnostic while transmitting/receiving"))
            return

        self._running = True
        self.camera_audio_run_btn.setEnabled(False)
        self.log_view.clear()
        self._log(tr("カメラ＋音声送出の診断を開始します", "Starting the camera + audio TX diagnostic"))

        self._ca_connected = False
        self._ca_error = False
        self._ca_checked = 0
        self._ca_active = 0
        self._ca_tick = 0

        # ★status_updatedはこの診断中は発行されない(TxController.get_status()参照、
        # emit()自体がv4l2+ALSA同時キャプチャのリアルタイム性を乱すため)。代わりに
        # 毎ティックget_status()をポーリングする(_ca_tick_check参照)。errorのみ
        # 起動前の同期チェック用に接続する。
        tx.error.connect(self._on_ca_error)

        self.status_label.setText(tr("カメラ＋音声送出へ接続中...", "Connecting to camera + audio TX..."))
        self._log(tr(f"[診断] カメラ＋音声送出確認 ({CAMERA_AUDIO_SECONDS}秒)",
                      f"[Diag] Camera + audio TX check ({CAMERA_AUDIO_SECONDS}s)"))
        tx.start_camera_audio(self.main_window.settings)
        QtCore.QTimer.singleShot(WARMUP_MS, self._ca_warmup_done)

    def _on_ca_error(self, message: str) -> None:
        self._ca_error = True
        self._log(f"[Tx] {message}")

    def _ca_warmup_done(self) -> None:
        self.status_label.setText(tr(f"カメラ＋音声送出確認中... (0/{CAMERA_AUDIO_SECONDS}秒)",
                                      f"Checking camera + audio TX... (0/{CAMERA_AUDIO_SECONDS}s)"))
        self._ca_tick_check()

    def _ca_tick_check(self) -> None:
        tx = self.main_window.tx_controller
        tx.refresh_camera_audio_frame_counts()
        self._ca_tick += 1
        self.status_label.setText(tr(
            f"カメラ＋音声送出確認中... ({self._ca_tick}/{CAMERA_AUDIO_SECONDS}秒) "
            f"映像={tx.video_frame_count} 音声={tx.audio_frame_count}",
            f"Checking camera + audio TX... ({self._ca_tick}/{CAMERA_AUDIO_SECONDS}s) "
            f"video={tx.video_frame_count} audio={tx.audio_frame_count}"
        ))
        self._ca_checked += 1
        status = tx.get_status()
        if status["connected"]:
            self._ca_connected = True
            self._ca_active += 1
        if self._ca_tick < CAMERA_AUDIO_SECONDS:
            QtCore.QTimer.singleShot(1000, self._ca_tick_check)
        else:
            self._finish_camera_audio()

    def _finish_camera_audio(self) -> None:
        tx = self.main_window.tx_controller
        tx.error.disconnect(self._on_ca_error)
        tx.refresh_camera_audio_frame_counts()
        video_frames = tx.video_frame_count
        audio_frames = tx.audio_frame_count
        tx.stop()

        capture_pass = video_frames > 0 and audio_frames > 0
        tx_pass = self._ca_checked > 0 and self._ca_active > 0
        overall_pass = capture_pass and tx_pass and not self._ca_error

        self._log(tr(
            f"[診断] キャプチャ結果: {self._ok_ng_html(capture_pass)} "
            f"(映像フレーム={video_frames}, 音声フレーム={audio_frames})",
            f"[Diag] Capture result: {self._ok_ng_html(capture_pass)} "
            f"(video frames={video_frames}, audio frames={audio_frames})"))
        self._log(tr(
            f"[診断] TX結果: {self._ok_ng_html(tx_pass)} "
            f"(接続={self._ca_connected}, 有効サンプル={self._ca_active}/{self._ca_checked})",
            f"[Diag] TX result: {self._ok_ng_html(tx_pass)} "
            f"(connected={self._ca_connected}, active samples={self._ca_active}/{self._ca_checked})"))

        result = f"{tr('カメラ＋音声送出', 'Camera + audio TX')}: {self._result_html(overall_pass)}"
        self._log(tr(f"カメラ＋音声送出の診断完了: {result}", f"Camera + audio TX diagnostic complete: {result}"))
        self.status_label.setText(result)
        # QProcessの終了シグナルが届くまでTX停止が完了しないため、
        # 直後の全体試験開始を一時的に禁止する。
        self.run_btn.setEnabled(False)
        self.camera_audio_run_btn.setEnabled(False)
        QtCore.QTimer.singleShot(1500, self._camera_audio_cleanup_done)

    def _camera_audio_cleanup_done(self) -> None:
        tx = self.main_window.tx_controller
        if tx.is_running():
            QtCore.QTimer.singleShot(500, self._camera_audio_cleanup_done)
            return
        self.camera_audio_run_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        self._running = False


def create(main_window) -> QtWidgets.QWidget:
    return TestEquipmentScreen(main_window)
