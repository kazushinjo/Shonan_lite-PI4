"""モック8番カードに合わせた映像ソース画面(Shonan_Lite-RasPI5のvideosource.pyからの移植)。

★Pi4(linuxfb)では独立ウィンドウのダイアログが表示されないため、警告・案内・ファイル選択は
widgetsの重ね表示(error_dialog/info_dialog/open_file_dialog)を使う。"""
from __future__ import annotations

import glob
from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from i18n import tr
from widgets import SettingsSubScreen, confirm_dialog, error_dialog, info_dialog, open_file_dialog

# オーバーレイ文字サイズの選択肢(px、1920x1080の送信映像上での大きさ)。
_CALLSIGN_FONT_SIZES = (36, 48, 68, 96, 128, 192, 256)
_NOTE_FONT_SIZES = (16, 24, 32, 48, 64)
# コールサイン・備考の文字色の選択肢(表示名, "#RRGGBB")。
_OVERLAY_COLORS = (
    (("白", "White"), "#FFFFFF"),
    (("黄", "Yellow"), "#FFFF00"),
    (("赤", "Red"), "#FF3030"),
    (("緑", "Green"), "#00E000"),
    (("青", "Blue"), "#3080FF"),
    (("水色", "Cyan"), "#00FFFF"),
    (("橙", "Orange"), "#FF9900"),
    (("黒", "Black"), "#000000"),
)
# 「撮影」ボタンで撮ったカメラ静止画(JPG)の保存先。「ファイル選択」はここから開く。
# ★アプリ本体のフォルダ(~/shonan-pi5)には置かない。install.shがrsync --deleteで
# 丸ごと置き換えるため、再インストールで撮影画像が消えてしまう。
CAPTURE_DIR = Path.home() / "Pictures" / "Shonan_Lite"
# 撮影解像度。送信映像(フルHD固定)と同じにする。C920はMJPEGで1920x1080を出せる。
CAPTURE_SIZE = "1920x1080"
# 撮影開始直後のフレームは露出・ホワイトバランスが落ち着いていないため捨てる枚数。
CAPTURE_SKIP_FRAMES = 10


class VideoSourceScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("映像ソース / Video Source", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self._camera_process = None
        self._camera_buffer = bytearray()
        self.header_bar.hide()
        self.body_layout.setContentsMargins(10, 8, 10, 10)
        self.body_layout.setSpacing(6)

        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame { background: #0a0c0d; border: 1px solid #34434b; border-radius: 14px; }"
            "QLabel { color: #eeeeee; background: transparent; }"
            "QComboBox { background: #0f1214; color: #eeeeee; border: 1px solid #46545b; border-radius: 6px; padding: 5px; }"
            "QLineEdit { background: #0f1214; color: #eeeeee; border: 1px solid #46545b;"
            " border-radius: 6px; padding: 4px 8px; font-size: 14px; }"
            # ★祖先(SettingsSubScreen)のQSSがボタン・入力欄に大きいmin-heightを全体適用しており、
            # そのままでは800x480に収まらずスクロールが出た(Pi4実機で確認)。この画面では高さを抑える。
            "QPushButton { min-height: 28px; max-height: 34px; }"
            "QLineEdit, QComboBox { min-height: 28px; max-height: 32px; }"
        )
        self.body_layout.addWidget(card, 1)
        outer = QtWidgets.QVBoxLayout(card)
        outer.setContentsMargins(12, 10, 12, 8)
        outer.setSpacing(6)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(10)
        outer.addLayout(columns, 1)

        left = QtWidgets.QFrame()
        left.setStyleSheet("QFrame { background: #0f1214; border: 1px solid #34434b; border-radius: 10px; }")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(10, 8, 10, 8)
        left_layout.setSpacing(2)
        title = QtWidgets.QLabel(tr("映像ソース選択", "Video Source Selection"))
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        left_layout.addWidget(title)

        self._group = QtWidgets.QButtonGroup(self)
        self._source_buttons = {}
        cameras = sorted(glob.glob("/dev/video[0-9]")) or ["/dev/video0"]
        settings = main_window.settings
        current_source = settings.video_source
        if settings.use_color_bar_source:
            current_source = "colorbar"
        self._add_source(left_layout, tr("カメラ", "Camera"), "camera", enabled=True,
                         checked=(current_source == "camera"))
        self._add_source(left_layout, tr("ファイル選択", "File"), "file", enabled=True,
                         checked=(current_source == "file"))
        self._add_source(left_layout, tr("テストパターン", "Test Pattern"), "colorbar",
                         enabled=True, checked=(current_source == "colorbar"))
        audio_title = QtWidgets.QLabel(tr("音声設定", "Audio"))
        audio_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        left_layout.addWidget(audio_title)
        self.audio_none_button = QtWidgets.QPushButton(tr("音声なし", "No Audio"))
        self.audio_none_button.setCheckable(True)
        self.audio_none_button.setChecked(not settings.audio_enabled)
        self.audio_none_button.setMinimumHeight(30)
        self.audio_none_button.setStyleSheet(
            "QPushButton { background-color: #303538; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; text-align: left;"
            " font-size: 13px; font-weight: bold; }"
            "QPushButton:checked { background-color: #1677ff; }"
            "QPushButton:pressed { background-color: #222222; }")
        self.audio_none_button.toggled.connect(self._select_audio_none)
        left_layout.addWidget(self.audio_none_button)
        left_layout.addStretch(1)
        # カメラ映像を静止画(JPG)として撮影・保存する。保存した画像は「ファイル選択」で
        # 送信画像として選べる。映像ソースが「カメラ」のときだけ表示する。
        self._capture_process = None
        self._capture_path = None
        self.capture_btn = QtWidgets.QPushButton(tr("撮影", "Capture"))
        self.capture_btn.setMinimumHeight(30)
        self.capture_btn.setStyleSheet(
            "QPushButton { background-color: #1677ff; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; font-size: 13px; font-weight: bold; }"
            "QPushButton:pressed { background-color: #102a5c; }"
            "QPushButton:disabled { color: #777777; background-color: #171a1c; }"
        )
        self.capture_btn.clicked.connect(self._capture_still)
        # 撮影した画像(CAPTURE_DIRのcapture_*.jpg)をまとめて削除する。撮影ボタンと
        # 半分ずつの幅で横に並べ、誤操作と区別できるよう赤系の色にする。
        self.delete_captures_btn = QtWidgets.QPushButton(tr("全削除", "Delete All"))
        self.delete_captures_btn.setMinimumHeight(30)
        self.delete_captures_btn.setStyleSheet(
            "QPushButton { background-color: #c62828; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; font-size: 13px; font-weight: bold; }"
            "QPushButton:pressed { background-color: #7f1a1a; }"
            "QPushButton:disabled { color: #777777; background-color: #171a1c; }"
        )
        self.delete_captures_btn.clicked.connect(self._delete_all_captures)
        # ★撮影中は撮影ボタンを無効にするが、押した直後のボタンがフォーカスを持っていると
        # Qtがフォーカスを次の部品(コールサイン入力欄)へ移し、オンスクリーンキーボードが
        # 出て撮影完了の案内(OKボタン)を隠してしまう(Pi4実機で確認)。フォーカスを持たせない。
        self.capture_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.delete_captures_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        capture_row = QtWidgets.QHBoxLayout()
        capture_row.setSpacing(8)
        capture_row.addWidget(self.capture_btn, 1)
        capture_row.addWidget(self.delete_captures_btn, 1)
        left_layout.addLayout(capture_row)
        columns.addWidget(left, 1)

        right = QtWidgets.QFrame()
        right.setStyleSheet("QFrame { background: #0f1214; border: 1px solid #34434b; border-radius: 10px; }")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(4)
        preview_title = QtWidgets.QLabel(tr("プレビュー", "Preview"))
        preview_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        right_layout.addWidget(preview_title)
        self.preview = QtWidgets.QLabel()
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setScaledContents(False)
        self.preview.setMinimumSize(300, 150)
        # ★既定のサイズポリシーでは表示した画像の大きさに合わせて枠が広がり、見えている
        # 範囲より大きく拡大されてテストパターンの四隅が切れる。枠の大きさは画像に左右
        # させず、枠の大きさが確定・変化した時点で縮小し直す(eventFilter参照)。
        self.preview.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.preview.installEventFilter(self)
        self.preview.setStyleSheet("background: #050607; border: 1px solid #46545b; border-radius: 6px; color: #aab7bd;")
        right_layout.addWidget(self.preview, 1)
        columns.addWidget(right, 2)

        # 映像へ焼き込むコールサイン・備考(カメラ・画像ファイルに適用、テストパターンには
        # 元々コールサインが描かれているため適用しない)。送信解像度はフルHD(1920x1080)固定のため、
        # 解像度・フレームレートの選択欄は置かない。
        callsign_row = QtWidgets.QHBoxLayout()
        callsign_row.setSpacing(10)
        callsign_row.addWidget(self._overlay_label(tr("コールサイン", "Callsign")))
        self.overlay_callsign_edit = QtWidgets.QLineEdit()
        self.overlay_callsign_edit.setMinimumHeight(36)
        self.overlay_callsign_edit.setPlaceholderText(tr("例: JA1XXX", "e.g. JA1XXX"))
        self.overlay_callsign_edit.setText(settings.overlay_callsign)
        self.overlay_callsign_edit.editingFinished.connect(self._save_overlay_callsign)
        callsign_row.addWidget(self.overlay_callsign_edit, 1)
        self.overlay_callsign_size = self._font_size_combo(_CALLSIGN_FONT_SIZES)
        self.overlay_callsign_size.activated.connect(self._save_overlay_callsign_size)
        callsign_row.addWidget(self.overlay_callsign_size)
        self.overlay_callsign_color = self._color_combo(tr("コールサインの文字色", "Callsign color"))
        self.overlay_callsign_color.activated.connect(self._save_overlay_callsign_color)
        callsign_row.addWidget(self.overlay_callsign_color)
        outer.addLayout(callsign_row)

        note_row = QtWidgets.QHBoxLayout()
        note_row.setSpacing(10)
        note_row.addWidget(self._overlay_label(tr("備考", "Note")))
        self.overlay_note_edit = QtWidgets.QLineEdit()
        self.overlay_note_edit.setMinimumHeight(36)
        self.overlay_note_edit.setPlaceholderText(tr("任意", "Optional"))
        self.overlay_note_edit.setText(settings.overlay_note)
        self.overlay_note_edit.editingFinished.connect(self._save_overlay_note)
        note_row.addWidget(self.overlay_note_edit, 1)
        self.overlay_note_size = self._font_size_combo(_NOTE_FONT_SIZES)
        self.overlay_note_size.activated.connect(self._save_overlay_note_size)
        note_row.addWidget(self.overlay_note_size)
        self.overlay_note_color = self._color_combo(tr("備考の文字色", "Note color"))
        self.overlay_note_color.activated.connect(self._save_overlay_note_color)
        note_row.addWidget(self.overlay_note_color)
        back_btn = QtWidgets.QPushButton(tr("ホームへ戻る", "Back to Home"))
        back_btn.setFixedHeight(36)
        back_btn.clicked.connect(lambda: self.main_window.navigate_to("home"))
        note_row.addWidget(back_btn)
        outer.addLayout(note_row)
        self._load_overlay_sizes()

        self._camera_device = cameras[0]
        # ★settings.camera_device(TX開始時にbackend.pyが実際に使う値)へも書き戻す。
        # この画面のプレビュー用ローカル変数self._camera_deviceだけが検出済みデバイス名を
        # 持ち、settings側が別の(存在しない)デバイスを指したままになるのを防ぐ。
        if settings.camera_device != self._camera_device:
            settings.camera_device = self._camera_device
            self.main_window.save_settings()
        self._update_capture_button()
        # ★ここで_update_preview()を呼ぶと(video_source=="camera"のとき)
        # _start_camera_preview()が無条件に実行される。main.py _build_screens()は
        # 全画面のウィジェットを起動時に一括構築するため、ユーザーが映像ソース画面を
        # 一度も開いていなくても、アプリ起動と同時にこのプレビュー用ffmpegがバック
        # グラウンドで動き続けてしまい、後から送信開始してもTX用ffmpegが同じカメラを
        # 取得できずに失敗する(on_hide()は一度も表示していない画面には呼ばれないため、
        # このプレビューは誰にも止められない。Windows版で実機確認済み)。
        # 実際の表示時はon_show()が_update_preview()を呼ぶので、ここでは呼ばない。
        self.preview.setText(tr("カメラ (USB)\nプレビュー待機中", "Camera (USB)\nWaiting for preview"))

    def on_show(self) -> None:
        # プリセット読込等で設定が変わっている場合に備え、表示のたびに入力欄を読み直す。
        settings = self.main_window.settings
        self.overlay_callsign_edit.setText(settings.overlay_callsign)
        self.overlay_note_edit.setText(settings.overlay_note)
        self._load_overlay_sizes()
        # レイアウト確定後の実サイズでプレビュー枠へ描画する。
        self._update_preview()
        QtCore.QTimer.singleShot(0, self._refresh_still_preview)

    def on_hide(self) -> None:
        self._stop_camera_preview()

    def _add_source(self, layout, label: str, source: str, *, enabled: bool,
                    checked: bool = False) -> None:
        radio = QtWidgets.QPushButton(label)
        radio.setCheckable(True)
        radio.setMinimumHeight(30)
        radio.setChecked(checked)
        radio.setEnabled(enabled)
        radio.setStyleSheet(
            "QPushButton { background-color: #303538; color: white; border: none;"
            " border-radius: 8px; padding: 4px 10px; text-align: left;"
            " font-size: 13px; font-weight: bold; }"
            "QPushButton:checked { background-color: #1677ff; }"
            "QPushButton:pressed { background-color: #102a5c; }"
            "QPushButton:disabled { color: #777777; background-color: #171a1c; }"
        )
        if enabled:
            radio.toggled.connect(lambda active, s=source: active and self._select(s))
        self._group.addButton(radio)
        self._source_buttons[source] = radio
        layout.addWidget(radio)

    @staticmethod
    def _overlay_label(text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("font-size: 14px;")
        return label

    @staticmethod
    def _font_size_combo(sizes) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.setMinimumHeight(36)
        combo.setToolTip(tr("文字サイズ", "Font size"))
        for size in sizes:
            combo.addItem(f"{size}px", size)
        return combo

    @staticmethod
    def _select_font_size(combo: QtWidgets.QComboBox, size: int) -> None:
        index = combo.findData(size)
        if index < 0:
            # 設定ファイルに選択肢外の値がある場合もその値を表示・維持する。
            combo.addItem(f"{size}px", size)
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    def _load_overlay_sizes(self) -> None:
        settings = self.main_window.settings
        self._select_font_size(self.overlay_callsign_size, settings.overlay_callsign_font_size)
        self._select_font_size(self.overlay_note_size, settings.overlay_note_font_size)
        self._select_color(self.overlay_callsign_color, settings.overlay_callsign_color)
        self._select_color(self.overlay_note_color, settings.overlay_note_color)

    def _select_color(self, combo: QtWidgets.QComboBox, color: str) -> None:
        color = color.upper()
        index = combo.findData(color)
        if index < 0:
            # 設定ファイルに選択肢外の色がある場合もその色を表示・維持する。
            combo.addItem(self._color_icon(color), color, color)
            index = combo.count() - 1
        combo.setCurrentIndex(index)

    @staticmethod
    def _color_icon(color: str) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(20, 20)
        pixmap.fill(QtGui.QColor(color))
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QColor("#888888"))
        painter.drawRect(0, 0, 19, 19)
        painter.end()
        return QtGui.QIcon(pixmap)

    def _color_combo(self, tooltip: str) -> QtWidgets.QComboBox:
        combo = QtWidgets.QComboBox()
        combo.setMinimumHeight(36)
        combo.setIconSize(QtCore.QSize(20, 20))
        combo.setToolTip(tooltip)
        for (ja, en), color in _OVERLAY_COLORS:
            combo.addItem(self._color_icon(color), tr(ja, en), color)
        return combo

    def _save_overlay_callsign_color(self, _index: int) -> None:
        self.main_window.settings.overlay_callsign_color = str(self.overlay_callsign_color.currentData())
        self.main_window.save_settings()

    def _save_overlay_note_color(self, _index: int) -> None:
        self.main_window.settings.overlay_note_color = str(self.overlay_note_color.currentData())
        self.main_window.save_settings()

    def _save_overlay_callsign_size(self, _index: int) -> None:
        self.main_window.settings.overlay_callsign_font_size = int(self.overlay_callsign_size.currentData())
        self.main_window.save_settings()

    def _save_overlay_note_size(self, _index: int) -> None:
        self.main_window.settings.overlay_note_font_size = int(self.overlay_note_size.currentData())
        self.main_window.save_settings()

    def _save_overlay_callsign(self) -> None:
        self.main_window.settings.overlay_callsign = self.overlay_callsign_edit.text().strip()
        self.main_window.save_settings()

    def _save_overlay_note(self) -> None:
        self.main_window.settings.overlay_note = self.overlay_note_edit.text().strip()
        self.main_window.save_settings()

    def _select(self, source: str) -> None:
        settings = self.main_window.settings
        if source == "camera":
            settings.video_source = "camera"
            settings.use_color_bar_source = False
        elif source == "file":
            # 「撮影」で保存した画像をすぐ選べるよう、撮影フォルダから開く。
            start_dir = str(CAPTURE_DIR) if CAPTURE_DIR.is_dir() else ""
            path = open_file_dialog(
                self, tr("画像ファイルを選択", "Select Image File"), start_dir,
                tr("画像ファイル (*.png *.jpg *.jpeg *.bmp)",
                   "Image files (*.png *.jpg *.jpeg *.bmp)"))
            if not path:
                file_button = self._source_buttons["file"]
                file_button.blockSignals(True)
                file_button.setChecked(False)
                file_button.blockSignals(False)
                previous = "colorbar" if settings.use_color_bar_source else settings.video_source
                previous_button = self._source_buttons.get(previous)
                if previous_button is not None:
                    previous_button.blockSignals(True)
                    previous_button.setChecked(True)
                    previous_button.blockSignals(False)
                return
            settings.video_source = "file"
            settings.video_file_path = path
            settings.use_color_bar_source = False
        elif source == "colorbar":
            settings.video_source = "colorbar"
            settings.use_color_bar_source = True
        else:
            return
        self.main_window.save_settings()
        self._update_preview()

    def _select_audio_none(self, checked: bool) -> None:
        if not checked:
            self.audio_none_button.setChecked(True)
            return
        self.main_window.settings.audio_enabled = False
        self.main_window.save_settings()

    def _update_capture_button(self) -> None:
        settings = self.main_window.settings
        is_camera = settings.video_source == "camera" and not settings.use_color_bar_source
        # カメラ選択時だけ表示する(ファイル選択/テストパターンでは撮影できないため)。
        self.capture_btn.setVisible(is_camera)
        self.capture_btn.setEnabled(is_camera and self._capture_process is None)
        self.delete_captures_btn.setVisible(is_camera)
        self.delete_captures_btn.setEnabled(is_camera and self._capture_process is None)

    def _delete_all_captures(self) -> None:
        captures = sorted(CAPTURE_DIR.glob("capture_*.jpg")) if CAPTURE_DIR.is_dir() else []
        if not captures:
            info_dialog(
                self, tr("全削除", "Delete All"),
                tr("削除する撮影画像はありません。", "There are no captured images to delete."))
            return
        if not confirm_dialog(
                self, tr("全削除", "Delete All"),
                tr(f"撮影した画像 {len(captures)} 枚をすべて削除します。よろしいですか？",
                   f"Delete all {len(captures)} captured images?")):
            return
        failed = []
        for path in captures:
            try:
                path.unlink()
            except OSError:
                failed.append(path.name)
        # 削除した撮影画像が送信画像(ファイル選択)に選ばれていたら選択を解除する。
        settings = self.main_window.settings
        if settings.video_file_path and not Path(settings.video_file_path).exists():
            settings.video_file_path = ""
            self.main_window.save_settings()
        if failed:
            error_dialog(
                self, tr("全削除", "Delete All"),
                tr("削除できなかった画像があります:\n", "Some images could not be deleted:\n")
                + "\n".join(failed))

    def _capture_still(self) -> None:
        if self._capture_process is not None:
            return
        # ★送信中はTX側のffmpegがカメラを使っているため、同じカメラを開けない。
        if self.main_window.tx_controller.is_running():
            error_dialog(
                self, tr("撮影できません", "Cannot Capture"),
                tr("送信中はカメラを使用しているため撮影できません。\n送信を停止してから撮影してください。",
                   "The camera is in use while transmitting.\nStop TX before capturing."))
            return
        try:
            CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            error_dialog(self, tr("撮影できません", "Cannot Capture"),
                                          tr(f"保存先を作成できません: {exc}", f"Cannot create the folder: {exc}"))
            return
        self._capture_path = CAPTURE_DIR / f"capture_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        # ★プレビュー用ffmpegがカメラを開いたままだと撮影用ffmpegが開けないため先に止める。
        self._stop_camera_preview()
        self.capture_btn.setText(tr("撮影中...", "Capturing..."))
        self.preview.setPixmap(QtGui.QPixmap())
        self.preview.setText(tr("撮影中...", "Capturing..."))
        process = QtCore.QProcess(self)
        process.finished.connect(self._capture_finished)
        process.errorOccurred.connect(self._capture_error)
        process.start("ffmpeg", [
            "-hide_banner", "-loglevel", "error", "-y",
            "-f", "v4l2", "-input_format", "mjpeg", "-video_size", CAPTURE_SIZE,
            "-i", self._camera_device,
            "-vf", f"select=gte(n\\,{CAPTURE_SKIP_FRAMES})", "-frames:v", "1", "-q:v", "2",
            # 連番でない1枚だけのファイル名に書くことを明示する(無いと無害な警告が出る)。
            "-update", "1",
            str(self._capture_path),
        ])
        self._capture_process = process
        self._update_capture_button()
        # 万一カメラが応答しない場合に備えて打ち切る。
        QtCore.QTimer.singleShot(15000, self._capture_timeout)

    def _capture_timeout(self) -> None:
        if self._capture_process is not None:
            self._capture_process.kill()

    def _capture_error(self, error) -> None:
        # 起動自体に失敗した場合(ffmpeg無し等)はfinishedが来ないのでここで後始末する。
        if error == QtCore.QProcess.FailedToStart:
            self._capture_finished(-1, QtCore.QProcess.CrashExit)

    def _capture_finished(self, exit_code, _status) -> None:
        process, self._capture_process = self._capture_process, None
        if process is None:
            return
        error_text = bytes(process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        process.deleteLater()
        self.capture_btn.setText(tr("撮影", "Capture"))
        self._update_capture_button()
        path = self._capture_path
        ok = exit_code == 0 and path is not None and path.is_file() and path.stat().st_size > 0
        # 撮影後はカメラプレビューを再開する(カメラ以外に切り替わっていればその表示になる)。
        # ★撮影中に別の画面へ移っていた場合は再開しない(非表示の画面でプレビュー用ffmpegが
        # カメラを掴んだままになり、送信用ffmpegがカメラを開けなくなるため)。
        if not self.isVisible():
            return
        self._update_preview()
        if ok:
            info_dialog(
                self, tr("撮影しました", "Captured"),
                tr(f"{path.name} を保存しました。\n「ファイル選択」で送信画像として選べます。",
                   f"Saved {path.name}.\nYou can choose it as the TX image with \"File\"."))
        else:
            error_dialog(
                self, tr("撮影できません", "Cannot Capture"),
                tr("カメラ映像を撮影できませんでした。", "Could not capture the camera image.")
                + (f"\n{error_text.splitlines()[-1]}" if error_text else ""))

    def _update_preview(self) -> None:
        settings = self.main_window.settings
        self._update_capture_button()
        if self._capture_process is not None:
            return      # 撮影中はカメラを撮影用ffmpegが使っているのでプレビューを起動しない
        if settings.use_color_bar_source or settings.video_source == "colorbar":
            self._stop_camera_preview()
            image = Path(__file__).resolve().parents[1] / "assets" / "test_pattern.png"
            pixmap = QtGui.QPixmap(str(image))
            self.preview.setPixmap(self._scaled_preview(pixmap))
        elif settings.video_source == "file" and settings.video_file_path:
            self._stop_camera_preview()
            pixmap = QtGui.QPixmap(settings.video_file_path)
            if pixmap.isNull():
                self.preview.setPixmap(QtGui.QPixmap())
                self.preview.setText(tr(f"ファイル選択済み\n{Path(settings.video_file_path).name}",
                                         f"File selected\n{Path(settings.video_file_path).name}"))
            else:
                self.preview.setPixmap(self._scaled_preview(pixmap))
        else:
            self._start_camera_preview()
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText(tr("カメラ (USB)\nプレビュー待機中", "Camera (USB)\nWaiting for preview"))

    def _start_camera_preview(self) -> None:
        if self._camera_process is not None:
            return
        self._camera_buffer.clear()
        process = QtCore.QProcess(self)
        process.readyReadStandardOutput.connect(self._read_camera_frame)
        process.errorOccurred.connect(self._camera_preview_error)
        process.start("ffmpeg", ["-hide_banner", "-loglevel", "error", "-f", "v4l2",
                                  "-video_size", "640x480", "-i", self._camera_device,
                                  # ★640x480に対応していないカメラでは、ドライバが近い別の
                                  # 解像度(640x360等)に変えて返す。下の_read_camera_frame()は
                                  # 640x480固定で切り出すため、出力を必ず640x480にそろえる
                                  # (縦横比は保ち、余白は黒で埋める)。
                                  "-vf", "scale=640:480:force_original_aspect_ratio=decrease,"
                                         "pad=640:480:(ow-iw)/2:(oh-ih)/2",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-r", "10", "-"])
        self._camera_process = process

    def _stop_camera_preview(self) -> None:
        if self._camera_process is not None:
            self._camera_process.kill()
            self._camera_process.deleteLater()
            self._camera_process = None
        self._camera_buffer.clear()

    def _read_camera_frame(self) -> None:
        if self._camera_process is None:
            return
        self._camera_buffer.extend(bytes(self._camera_process.readAllStandardOutput()))
        frame_size = 640 * 480 * 3
        while len(self._camera_buffer) >= frame_size:
            frame = bytes(self._camera_buffer[:frame_size])
            del self._camera_buffer[:frame_size]
            image = QtGui.QImage(frame, 640, 480, 640 * 3,
                                 QtGui.QImage.Format_RGB888).copy()
            self.preview.setPixmap(self._scaled_preview(QtGui.QPixmap.fromImage(image)))

    def _camera_preview_error(self, _error) -> None:
        if self.main_window.settings.video_source == "camera":
            self.preview.setText(tr("カメラ映像を取得できません", "Unable to get camera video"))

    def _scaled_preview(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        if pixmap.isNull():
            return pixmap
        # 枠線の内側(contentsRect)に収める。
        return pixmap.scaled(
            self.preview.contentsRect().size() - QtCore.QSize(4, 4), QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation)

    def _refresh_still_preview(self) -> None:
        """テストパターン・画像ファイルのプレビューを現在の枠の大きさで描き直す
        (カメラ映像はフレームごとに縮小しているので対象外)。"""
        if not self.isVisible() or self._capture_process is not None:
            return
        settings = self.main_window.settings
        if (settings.use_color_bar_source or settings.video_source == "colorbar"
                or (settings.video_source == "file" and settings.video_file_path)):
            self._update_preview()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "preview", None) and event.type() == QtCore.QEvent.Resize:
            self._refresh_still_preview()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # ★未表示時のresize(起動時の一括構築中)ではカメラプレビューを起動しない
        # (__init__で_update_preview()を呼ばない理由と同じ)。
        if hasattr(self, "preview") and self.isVisible():
            self._update_preview()

    def closeEvent(self, event) -> None:
        self._stop_camera_preview()
        super().closeEvent(event)


def create(main_window) -> QtWidgets.QWidget:
    return VideoSourceScreen(main_window)
