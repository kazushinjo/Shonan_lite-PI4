"""共通UIウィジェット。Android版 ui/SettingsWidgets.kt のPyQt5移植。

タッチ操作前提(現状Pi4ではタッチデバイス`ft5x06`をevdev/libinput経由でQtが拾う想定、
未検出時はマウス/キーボードでも操作できるよう、ボタン等は十分大きいタッチターゲットにする)。
"""
from __future__ import annotations

from typing import Callable

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QScroller

from i18n import is_english, translate_text

TOUCH_MIN_HEIGHT = 56
FONT_SIZE_TITLE = 20
FONT_SIZE_BODY = 14


class NavButton(QtWidgets.QPushButton):
    """Home画面のメニューグリッド等で使う大型ボタン。"""

    def __init__(self, label_ja: str, label_en: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        # ★QGridLayoutはセル内でQPushButtonのsizeHintいっぱいまで場所を使うため、
        # setSpacing()でセル間隔を広げただけではボタン自体は縮まず隙間が見えなかった
        # (setMaximumHeight+AlignTopでも実機で変化なしを確認済み)。
        # font-size/paddingを縮小してsizeHint自体を小さくし、setFixedHeightで
        # 高さを確定させることで確実に隙間ができるようにする。
        self.setFixedHeight(58)
        self.setFixedWidth(172)
        # ★Qtの既定スタイルはQPushButtonにフォーカスリング(太い枠)を描画する。
        # border:noneだけでは消えないため、outline:noneと共にフォーカスポリシー自体を
        # 無効化する(タッチ操作のみのキオスク用途でキーボードフォーカス表示は不要)。
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet(
            "QPushButton {"
            "  font-size: 12px; font-weight: bold; padding: 2px;"
            "  background-color: #172758; color: white;"
            "  border: 1px solid #263b7e; border-radius: 10px; outline: none;"
            "}"
            "QPushButton:pressed { background-color: #0c1638; border-color: #4d7cff; }"
            "QPushButton:focus { border: 1px solid #263b7e; outline: none; }"
        )
        self._label_ja = label_ja
        self._label_en = label_en
        self.set_subtitle(subtitle)

    def set_subtitle(self, subtitle: str) -> None:
        text = f"{self._label_ja}\n{self._label_en}"
        if subtitle:
            text += f"\n{subtitle}"
        self.setText(text)


class RadioOptionRow(QtWidgets.QWidget):
    """1つのラジオボタン行。ui/SettingsWidgets.kt RadioOptionRow相当。

    compact=Trueで行間・高さを詰める(800x480の小画面で選択肢数が多く、
    既定サイズだとスクロールが必要になる画面向け)。
    """

    def __init__(self, label: str, checked: bool, on_select: Callable[[], None], parent=None,
                 compact: bool = False):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0) if compact else layout.setContentsMargins(4, 4, 4, 4)
        self.radio = QtWidgets.QRadioButton(label)
        self.radio.setMinimumHeight(52 if compact else TOUCH_MIN_HEIGHT)
        self.radio.setStyleSheet(f"font-size: {FONT_SIZE_BODY}px;")
        self.radio.setChecked(checked)
        self.radio.toggled.connect(lambda checked: on_select() if checked else None)
        layout.addWidget(self.radio)
        layout.addStretch(1)


class MemoNote(QtWidgets.QLabel):
    """記録専用(実機制御なし)であることを示す注記。ui/SettingsWidgets.kt OperationalMemoNote相当。"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setStyleSheet("color: #888888; font-size: 12px; padding: 4px;")


class SettingsSubScreen(QtWidgets.QWidget):
    """設定系サブ画面の共通スキャフォールド: タイトルバー+戻るボタン+スクロール可能な本体。

    ui/SettingsWidgets.kt SettingsSubScreen相当。サブクラスは self.body_layout に
    ウィジェットを追加する。
    """

    def __init__(self, title: str, on_back: Callable[[], None], parent=None):
        super().__init__(parent)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        bar = QtWidgets.QWidget()
        self.header_bar = bar
        bar.setObjectName("subScreenHeader")
        bar.setStyleSheet("QWidget#subScreenHeader { background-color: #0f1214; }")
        bar_layout = QtWidgets.QHBoxLayout(bar)
        back_btn = QtWidgets.QPushButton("ホームに戻る")
        back_btn.setMinimumSize(100, TOUCH_MIN_HEIGHT)
        back_btn.clicked.connect(on_back)
        bar_layout.addWidget(back_btn)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(f"color: white; background: transparent; font-size: {FONT_SIZE_TITLE}px; font-weight: bold;")
        bar_layout.addWidget(title_label, 1)
        outer.addWidget(bar)

        scroll = QtWidgets.QScrollArea()
        self.scroll_area = scroll
        scroll.setWidgetResizable(True)
        body = QtWidgets.QWidget()
        body.setObjectName("settingsBody")
        body.setStyleSheet(
            "QWidget#settingsBody { background: #000000; }"
            "QLabel { color: #eeeeee; font-size: 16px; }"
            "QPushButton { background-color: #1d4388; color: white;"
            " border: 1px solid #2c5aa8; border-radius: 8px;"
            " padding: 8px 12px; font-weight: bold; min-height: 52px; }"
            "QPushButton:pressed { background-color: #1677ff; }"
            "QLineEdit, QComboBox, QDateTimeEdit { background-color: #171a1c;"
            " color: white; border: 1px solid #4b5357; border-radius: 8px;"
            " padding: 8px; min-height: 42px; }"
            "QSlider { min-height: 40px; }"
            "QCheckBox { color: white; min-height: 52px; }")
        self.body_layout = QtWidgets.QVBoxLayout(body)
        self.body_layout.setContentsMargins(16, 16, 16, 16)
        self.body_layout.setSpacing(12)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ★QScrollAreaは既定ではタッチのドラッグスクロールに対応しない(スクロールバーの
        # 精密なタッチ操作が必要になってしまう)。QScrollerでタッチジェスチャーによる
        # ドラッグスクロール(慣性スクロール含む)を有効化する。
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)


def _run_as_overlay(dialog: QtWidgets.QDialog) -> int:
    """QDialog.exec_()の代替。

    ★QT_QPA_PLATFORM=linuxfb環境では、QDialogが別トップレベルウィンドウとして
    表示されると親ウィンドウの上に合成されず画面に一切表示されない不具合を
    実機で確認した(linuxfbはeglfs/KMSと違い複数トップレベルウィンドウの
    合成に対応しないため)。dialogのwindowFlagsをWidgetへ変更して独立ウィンドウ化を
    やめ、親の中に半透明オーバーレイとして埋め込んだうえで、QEventLoopで
    dialogのfinishedシグナル(accept()/reject()/done()で自動発火)を待つことで、
    QDialogのAPI(exec_の戻り値・NumericKeypadDialog.done()等)をそのまま使えるようにする。
    """
    parent = dialog.parentWidget()
    dialog.setWindowFlags(QtCore.Qt.Widget)
    overlay = QtWidgets.QWidget(parent)
    overlay.setStyleSheet("background: rgba(0, 0, 0, 200);")
    overlay.setGeometry(parent.rect())
    outer = QtWidgets.QVBoxLayout(overlay)
    outer.setContentsMargins(40, 40, 40, 40)
    row = QtWidgets.QHBoxLayout()
    row.addStretch(1)
    row.addWidget(dialog)
    row.addStretch(1)
    outer.addStretch(1)
    outer.addLayout(row)
    outer.addStretch(1)

    loop = QtCore.QEventLoop()
    result_code = {"value": QtWidgets.QDialog.Rejected}

    def _on_finished(code: int) -> None:
        result_code["value"] = code
        loop.quit()

    dialog.finished.connect(_on_finished)
    overlay.show()
    overlay.raise_()
    dialog.show()
    loop.exec_()
    # ★deleteLater()は入れ子のイベントループ内では外側のループへ戻るまで実行されない
    # (起動処理中に開いたダイアログ等)。暗い背景が画面に残らないよう先に隠す。
    overlay.hide()
    overlay.deleteLater()
    return result_code["value"]


class NumericKeypadDialog(QtWidgets.QDialog):
    """タッチ専用の数字入力ダイアログ。QT_QPA_PLATFORM=eglfs環境ではOSのソフトキーボードが
    出ないため、周波数入力等のフリーテキスト欄向けに自前で用意する。

    ダイアログ専用の表示欄は持たない。呼び出し元の実際の入力フィールド(target_edit)を
    一時的にこのダイアログのレイアウトへ移動して直接編集させ、閉じるときに元の位置へ
    戻す(キャンセル時は編集前の値へ復元してから戻す)。
    """

    def __init__(self, title: str, target_edit: QtWidgets.QLineEdit, parent=None,
                 allow_decimal: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        self._target = target_edit
        self._allow_decimal = allow_decimal
        self._original_text = target_edit.text()
        # ★このダイアログはQDialogとしてMainWindowとは別のトップレベルウィンドウになる。
        # QT_IM_MODULE=qtvirtualkeyboard指定下では、対象欄がフォーカスを得ると
        # プラットフォーム入力コンテキストがMainWindow側に手動埋め込み済みの
        # keyboard_panelとは別に、このウィンドウ用の(独立トップレベルの)入力パネルを
        # 生成しようとし、eglfsの「OpenGLウィンドウ1枚制限」に抵触してセグフォルトする
        # (実機で確認)。この欄はテンキーボタンでのみ入力するためIMEは不要であり、
        # setFocus()より前にWA_InputMethodEnabledを外して入力コンテキストの起動自体を防ぐ。
        self._target.setAttribute(QtCore.Qt.WA_InputMethodEnabled, False)
        self._original_stylesheet = target_edit.styleSheet()
        self._original_min_height = target_edit.minimumHeight()
        self._original_max_length = target_edit.maxLength()
        self._original_max_width = target_edit.maximumWidth()
        self._original_layout = target_edit.parentWidget().layout()
        self._original_index = self._original_layout.indexOf(target_edit)

        layout = QtWidgets.QVBoxLayout(self)

        # ★readOnlyのままだと物理/USBキーボードのBackspace等が一切効かない
        # (widgets.py冒頭の注記通りキーボードでの操作もサポートする)。数字専用バリデータ+
        # maxLengthで最大8桁に制限しつつ編集可能にし、オンスクリーンボタンとキーボード入力の
        # 両方を1文字単位でtarget_editへ直接・即座に反映させる。呼び出し元画面での
        # 幅制限(maximumWidth)はダイアログの大きい文字では窮屈なので編集中は解除する。
        self._target.setReadOnly(False)
        if allow_decimal:
            self._target.setValidator(QtGui.QDoubleValidator(0.0, 99_999_999.0, 6, self))
        else:
            self._target.setValidator(QtGui.QIntValidator(0, 99_999_999, self))
        self._target.setMaxLength(8)
        self._target.setMaximumWidth(QtWidgets.QWIDGETSIZE_MAX)
        self._target.setAlignment(QtCore.Qt.AlignRight)
        self._target.setMinimumHeight(TOUCH_MIN_HEIGHT)
        # ★呼び出し元画面(frequency.py)の表示フォント(24px)より小さくならないようにする。
        self._target.setStyleSheet(f"font-size: {max(FONT_SIZE_TITLE, 24)}px;")
        self._original_layout.removeWidget(self._target)
        layout.addWidget(self._target)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(4)
        positions = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2),
            ("C", 3, 0), ("0", 3, 1), ("←", 3, 2),
        ]
        if allow_decimal:
            positions = [item for item in positions if item[0] != "←"]
            positions.extend([(".", 3, 2), ("←", 3, 3)])
        for label, row, col in positions:
            btn = QtWidgets.QPushButton(label)
            btn.setMinimumSize(64, TOUCH_MIN_HEIGHT)
            btn.setStyleSheet(f"font-size: {FONT_SIZE_TITLE}px;")
            btn.clicked.connect(lambda _checked=False, label=label: self._on_key(label))
            grid.addWidget(btn, row, col)
        layout.addLayout(grid)

        buttons = QtWidgets.QHBoxLayout()
        cancel_btn = QtWidgets.QPushButton("キャンセル")
        cancel_btn.setMinimumHeight(TOUCH_MIN_HEIGHT)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.setMinimumHeight(TOUCH_MIN_HEIGHT)
        ok_btn.clicked.connect(self.accept)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._target.setFocus()
        self._target.end(False)

    def _on_key(self, label: str) -> None:
        self._target.setFocus()
        if label == "C":
            self._target.clear()
        elif label == "←":
            self._target.backspace()
        elif label == "." and "." in self._target.text():
            return
        else:
            self._target.insert(label)

    def done(self, result: int) -> None:
        if result == QtWidgets.QDialog.Rejected:
            self._target.setText(self._original_text)
        self._target.setAttribute(QtCore.Qt.WA_InputMethodEnabled, True)
        self._target.setReadOnly(True)
        self._target.setMaxLength(self._original_max_length)
        self._target.setMaximumWidth(self._original_max_width)
        self._target.setValidator(None)
        self._target.setStyleSheet(self._original_stylesheet)
        self._target.setMinimumHeight(self._original_min_height)
        self.layout().removeWidget(self._target)
        self._original_layout.insertWidget(self._original_index, self._target)
        super().done(result)

    @staticmethod
    def edit_in_place(parent: QtWidgets.QWidget, title: str, target_edit: QtWidgets.QLineEdit,
                      allow_decimal: bool = False) -> bool:
        dialog = NumericKeypadDialog(title, target_edit, parent, allow_decimal=allow_decimal)
        return _run_as_overlay(dialog) == QtWidgets.QDialog.Accepted


def confirm_dialog(parent: QtWidgets.QWidget, title: str, message: str) -> bool:
    """Yes/No確認ダイアログ。Android版RFループバック警告と同じ用途で使う。

    ★標準のQMessageBox.warning()はYes/Noボタンが既定の小さいデスクトップ
    サイズ(高さ約24px程度)のままで、タッチでは反応が悪い/押しにくいという
    指摘が実機で出た。他のUI部品と同じTOUCH_MIN_HEIGHT基準の大きい
    ボタンを持つカスタムダイアログに置き換える(戻り値の意味・呼び出し方は
    QMessageBox版と互換)。
    """
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(message)
    label.setWordWrap(True)
    label.setStyleSheet(f"font-size: {FONT_SIZE_BODY}px;")
    layout.addWidget(label)

    buttons = QtWidgets.QHBoxLayout()
    buttons.setSpacing(12)
    buttons.addStretch(1)
    yes_btn = QtWidgets.QPushButton("はい / Yes")
    yes_btn.setFixedSize(90, 32)
    yes_btn.setStyleSheet("font-size: 11px; background-color: #7a1414;")
    yes_btn.clicked.connect(dialog.accept)
    buttons.addWidget(yes_btn)
    no_btn = QtWidgets.QPushButton("いいえ / No")
    no_btn.setFixedSize(90, 32)
    no_btn.setStyleSheet("font-size: 11px;")
    no_btn.clicked.connect(dialog.reject)
    buttons.addWidget(no_btn)
    buttons.addStretch(1)
    layout.addLayout(buttons)

    no_btn.setDefault(True)
    no_btn.setFocus()
    return _run_as_overlay(dialog) == QtWidgets.QDialog.Accepted


def error_dialog(parent: QtWidgets.QWidget, title: str, message: str) -> None:
    main_window = parent.window()
    settings = getattr(main_window, "settings", None)
    if settings is not None and is_english(settings):
        title = translate_text(title, True)
        message = translate_text(message, True)
    box = QtWidgets.QMessageBox(
        QtWidgets.QMessageBox.Critical, title, message, QtWidgets.QMessageBox.Ok, parent
    )
    _run_as_overlay(box)


def info_dialog(parent: QtWidgets.QWidget, title: str, message: str) -> None:
    """案内(エラーではない)を表示する。error_dialogと同じく重ね表示(linuxfbでも表示される)。"""
    main_window = parent.window()
    settings = getattr(main_window, "settings", None)
    if settings is not None and is_english(settings):
        title = translate_text(title, True)
        message = translate_text(message, True)
    box = QtWidgets.QMessageBox(
        QtWidgets.QMessageBox.Information, title, message, QtWidgets.QMessageBox.Ok, parent
    )
    _run_as_overlay(box)


def open_file_dialog(parent: QtWidgets.QWidget, title: str, directory: str, name_filter: str) -> str:
    """ファイルを1つ選ぶ。選ばなかった場合は""を返す。

    ★QFileDialog.getOpenFileName()は独立したウィンドウとして開くため、linuxfbでは画面に
    表示されない。Qt自前のダイアログ(DontUseNativeDialog)を作り、重ね表示で出す。
    """
    dialog = QtWidgets.QFileDialog(parent, title, directory, name_filter)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
    top = parent.window()
    dialog.setFixedSize(max(400, top.width() - 60), max(300, top.height() - 60))
    if _run_as_overlay(dialog) != QtWidgets.QDialog.Accepted:
        return ""
    files = dialog.selectedFiles()
    return files[0] if files else ""
