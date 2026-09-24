"""Homeメニュー。Android版 ui/HomeScreen.kt の homeMenuButtons 相当。"""
from __future__ import annotations

import http.client
import subprocess
import urllib.error
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from backend import PTT_CHANNEL_POWER, _send_ptt_channel_state
from i18n import is_english
from widgets import NavButton, _run_as_overlay, confirm_dialog, error_dialog

_BUTTONS = [
    ("送信", "Transmit", "tx"),
    ("受信", "Receive", "rx"),
    ("周波数", "Frequency", "frequency"),
    ("RSSI測定", "RSSI Measurement", "rssi"),
    ("シンボルレート", "Symbol Rate", "symbolrate"),
    ("誤り訂正", "FEC", "fec"),
    ("変調方式", "Modulation", "modulation"),
    ("映像ソース", "Video Source", "videosource"),
    ("出力設定", "Stream Output", "streamoutput"),
    ("RXゲイン", "RX Gain", "rxgain"),
    ("TX出力", "TX Power", "txpower"),
    ("設定", "Config", "settings"),
    ("機器試験", "Diagnostic", "testequipment"),
    ("ヘルプ", "Help", "manual"),
    ("アプリ再起動", "App Restart", "pluto_reboot"),
    ("電源オフ", "Power Off", "shutdown"),
    ("Langstone", "SDR Transceiver", "langstone"),
    ("プリセット", "Presets", "presets"),
    ("Pluto電源", "Pluto Power", "pluto_power_cycle"),
]

# Pluto+のdatvplutofrmファームウェアの既定rootクレデンシャル(Dropbear SSH)。
_PLUTO_SSH_USER = "root"
_PLUTO_SSH_PASSWORD = "analog"


def _fec_icon() -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(44, 44)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor("white"), 3)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawEllipse(QtCore.QRectF(4, 4, 36, 36))
    check = QtGui.QPainterPath()
    check.moveTo(12, 22)
    check.lineTo(19, 29)
    check.lineTo(33, 14)
    painter.drawPath(check)
    painter.end()
    return QtGui.QIcon(pixmap)


def _restart_icon() -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(44, 44)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor("white"), 3)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawArc(QtCore.QRectF(5, 5, 34, 34), 35 * 16, 285 * 16)
    painter.setBrush(QtGui.QColor("white"))
    arrow = QtGui.QPolygonF([
        QtCore.QPointF(31, 5), QtCore.QPointF(40, 7), QtCore.QPointF(34, 14),
    ])
    painter.drawPolygon(arrow)
    painter.end()
    return QtGui.QIcon(pixmap)


def _style_special_card(button: NavButton, icon: QtGui.QIcon) -> None:
    button.setIcon(icon)
    button.setIconSize(QtCore.QSize(34, 34))
    button.setStyleSheet(
        "QPushButton {"
        "  font-size: 15px; font-weight: normal; padding: 2px;"
        "  background-color: #061526; color: white;"
        "  border: 2px solid #00a9c2; border-radius: 10px;"
        "  outline: none; text-align: left;"
        "}"
        "QPushButton:pressed { background-color: #0b3042; }"
        "QPushButton:focus { border: 2px solid #00a9c2; outline: none; }"
    )


class FecCheckIcon(QtWidgets.QWidget):
    """iPad/Pi5版と同じ円囲みチェックアイコン。"""

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        margin = max(1, min(self.width(), self.height()) * 0.08)
        circle = QtCore.QRectF(margin, margin, self.width() - margin * 2, self.height() - margin * 2)
        pen = QtGui.QPen(QtGui.QColor("white"), max(1.5, self.width() * 0.07))
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(circle)
        check = QtGui.QPainterPath()
        check.moveTo(self.width() * 0.28, self.height() * 0.52)
        check.lineTo(self.width() * 0.45, self.height() * 0.68)
        check.lineTo(self.width() * 0.74, self.height() * 0.34)
        painter.drawPath(check)
        painter.end()


class PresetCard(QtWidgets.QWidget):
    def __init__(self, parent=None, english: bool = False) -> None:
        super().__init__(parent)
        self._english = english

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.scale(self.width() / 322.0, self.height() / 107.0)
        inner = QtCore.QRectF(4, 4, 314, 99)
        fill = QtGui.QLinearGradient(inner.topLeft(), inner.bottomLeft())
        fill.setColorAt(0.0, QtGui.QColor("#071a2c"))
        fill.setColorAt(1.0, QtGui.QColor("#030b16"))
        painter.setBrush(QtGui.QBrush(fill))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(inner, 12, 12)

        icon_center = QtCore.QPointF(52, 52)
        painter.setPen(QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        for y, x in ((icon_center.y() - 12, 45), (icon_center.y(), 58), (icon_center.y() + 12, 49)):
            painter.drawLine(QtCore.QPointF(30, y), QtCore.QPointF(73, y))
            painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))
            painter.drawEllipse(QtCore.QPointF(x, y), 3.5, 3.5)

        # 通常カードの日本語タイトルと同じ見かけの大きさに合わせる。
        painter.setPen(QtGui.QColor("white"))
        if self._english:
            font = QtGui.QFont("Noto Sans CJK JP")
            font.setPixelSize(26)
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(font)
            painter.drawText(QtCore.QRectF(108, 27, 205, 55),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Presets")
        else:
            font = QtGui.QFont("Noto Sans CJK JP")
            font.setPixelSize(26)
            font.setWeight(QtGui.QFont.Thin)
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(font)
            painter.drawText(QtCore.QRectF(108, 27, 205, 30),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "プリセット")
            small_font = QtGui.QFont("Noto Sans CJK JP")
            small_font.setPixelSize(16)
            small_font.setWeight(QtGui.QFont.Thin)
            small_font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(small_font)
            painter.drawText(QtCore.QRectF(108, 56, 205, 25),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Presets")
        painter.end()


class PlutoPowerCard(QtWidgets.QWidget):
    """PresetCardと同様、モック画像上の空きスロットに描画する電源サイクルカード。"""

    def __init__(self, parent=None, english: bool = False) -> None:
        super().__init__(parent)
        self._english = english

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        # PresetCardと同じ322x107基準にし、カード枠・文字サイズを完全に揃える。
        painter.scale(self.width() / 322.0, self.height() / 107.0)
        inner = QtCore.QRectF(4, 4, 314, 99)
        fill = QtGui.QLinearGradient(inner.topLeft(), inner.bottomLeft())
        fill.setColorAt(0.0, QtGui.QColor("#071a2c"))
        fill.setColorAt(1.0, QtGui.QColor("#030b16"))
        painter.setBrush(QtGui.QBrush(fill))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(inner, 12, 12)

        # 電源アイコン(上部を開けた円弧+縦線。他画面の電源オフダイアログと同系統)。
        # PresetCardのアイコン(icon_center=52,52)と同じ位置に合わせる。
        icon_center = QtCore.QPointF(52, 52)
        radius = 18.0
        pen = QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        arc_rect = QtCore.QRectF(icon_center.x() - radius, icon_center.y() - radius,
                                  radius * 2, radius * 2)
        painter.drawArc(arc_rect, 100 * 16, 340 * 16)
        painter.drawLine(QtCore.QPointF(icon_center.x(), icon_center.y() - radius - 4),
                          QtCore.QPointF(icon_center.x(), icon_center.y() - 2))

        # 文字サイズ・位置はPresetCardと同一(タイトル26px/サブ16px、開始位置108,27/108,56)。
        painter.setPen(QtGui.QColor("white"))
        if self._english:
            font = QtGui.QFont("Noto Sans CJK JP")
            font.setPixelSize(26)
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(font)
            painter.drawText(QtCore.QRectF(108, 27, 205, 30),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Pluto Power")
            small_font = QtGui.QFont("Noto Sans CJK JP")
            small_font.setPixelSize(16)
            small_font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(small_font)
            painter.drawText(QtCore.QRectF(108, 56, 205, 25),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Power Cycle")
        else:
            font = QtGui.QFont("Noto Sans CJK JP")
            font.setPixelSize(26)
            font.setWeight(QtGui.QFont.Thin)
            font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(font)
            painter.drawText(QtCore.QRectF(108, 27, 205, 30),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Pluto電源")
            small_font = QtGui.QFont("Noto Sans CJK JP")
            small_font.setPixelSize(16)
            small_font.setWeight(QtGui.QFont.Thin)
            small_font.setStyleStrategy(QtGui.QFont.PreferAntialias)
            painter.setFont(small_font)
            painter.drawText(QtCore.QRectF(108, 56, 205, 25),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "OFF→ON")
        painter.end()


# ---- ホームのカード(全カード共通の描画) ----
# ★以前はカードの文字・アイコンを背景画像に焼き込んだものをそのまま使い、一部のカードだけ
# Qtで上書きしていたため、カードごとに文字の大きさ・アイコンの大きさと位置がばらばらだった。
# 全カードをこのHomeCardで描き直し、アイコン・日本語/英語の文字の大きさと位置を統一する。
# 座標は322x107基準(PresetCardと同じ)で、実際の大きさに合わせて拡大縮小する。
_CARD_BASE_W = 322.0
_CARD_BASE_H = 107.0
_CARD_ICON_CENTER = QtCore.QPointF(55, 53.5)
_CARD_ICON_BOX = 44.0          # アイコンの縦横の長い方をこの大きさに揃える
_CARD_TEXT_X = 104.0
_CARD_TEXT_W = 212.0
_CARD_TITLE_JA_PX = 26         # 日本語表示: タイトル(日本語)
_CARD_SUB_PX = 16              # 日本語表示: サブ(英語)、周波数の値
_CARD_TITLE_EN_PX = 24         # 英語表示: タイトル(英語1行)。幅に収まらないカードだけ縮める
_CARD_FONT = "Noto Sans CJK JP"
_HOME_ICON_DIR = Path(__file__).resolve().parents[1] / "assets" / "home_icons"


def _icon_fec(painter: QtGui.QPainter, box: QtCore.QRectF) -> None:
    """誤り訂正: 円囲みチェック(FecCheckIconと同じ形)。"""
    pen = QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.NoBrush)
    painter.drawEllipse(box.adjusted(2, 2, -2, -2))
    w, h, x, y = box.width(), box.height(), box.x(), box.y()
    check = QtGui.QPainterPath()
    check.moveTo(x + w * 0.28, y + h * 0.52)
    check.lineTo(x + w * 0.45, y + h * 0.68)
    check.lineTo(x + w * 0.74, y + h * 0.34)
    painter.drawPath(check)


def _icon_presets(painter: QtGui.QPainter, box: QtCore.QRectF) -> None:
    """プリセット: 3本のスライダー(PresetCardと同じ形)。"""
    painter.setPen(QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
    cx, cy, half = box.center().x(), box.center().y(), box.width() / 2
    for dy, knob in ((-13, -0.3), (0, 0.3), (13, -0.1)):
        painter.drawLine(QtCore.QPointF(cx - half + 1, cy + dy), QtCore.QPointF(cx + half - 1, cy + dy))
        painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        painter.drawEllipse(QtCore.QPointF(cx + knob * half, cy + dy), 3.8, 3.8)


def _icon_pluto_power(painter: QtGui.QPainter, box: QtCore.QRectF) -> None:
    """Pluto電源: 上部を開けた円弧+縦線(PlutoPowerCardと同じ形)。"""
    painter.setPen(QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
    painter.setBrush(QtCore.Qt.NoBrush)
    r = box.width() / 2 - 3
    c = box.center()
    painter.drawArc(QtCore.QRectF(c.x() - r, c.y() - r + 2, r * 2, r * 2), 115 * 16, 310 * 16)
    painter.drawLine(QtCore.QPointF(c.x(), c.y() - r - 1), QtCore.QPointF(c.x(), c.y() + 1))


class _PowerSymbol(QtWidgets.QWidget):
    """電源オフ確認ダイアログの電源マーク。★以前は文字"⏻"で表示していたが、Pi4のフォントに
    このグリフが無く四角(□)に化けていた(実機で確認)ため、Qtで描画する。"""

    def __init__(self, color: str = "#f05a45", size: int = 72, parent=None) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        pen = QtGui.QPen(self._color, w * 0.09, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap)
        painter.setPen(pen)
        r = w * 0.36
        c = QtCore.QPointF(w / 2, w / 2 + w * 0.04)
        painter.drawArc(QtCore.QRectF(c.x() - r, c.y() - r, r * 2, r * 2), 120 * 16, 300 * 16)
        painter.drawLine(QtCore.QPointF(c.x(), c.y() - r - w * 0.04), QtCore.QPointF(c.x(), c.y() - w * 0.02))
        painter.end()


_VECTOR_ICONS = {"fec": _icon_fec, "presets": _icon_presets, "pluto_power_cycle": _icon_pluto_power}


class HomeCard(QtWidgets.QWidget):
    """ホーム画面のカード1枚(背景・アイコン・日英タイトル)。クリックは上に重ねたボタンが受ける。"""

    def __init__(self, parent, route: str, title_ja: str, sub_ja: str, title_en: str,
                 english: bool, sub_en: str = "") -> None:
        super().__init__(parent)
        self._route = route
        self._title_ja, self._sub_ja = title_ja, sub_ja
        self._title_en, self._sub_en = title_en, sub_en
        self._english = english
        path = _HOME_ICON_DIR / f"{route}.png"
        self._pixmap = QtGui.QPixmap(str(path)) if path.exists() else None
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

    def setText(self, text: str) -> None:
        """周波数カードの値(サブ行)を更新する。"""
        self._sub_ja = text
        self._sub_en = text
        self.update()

    @staticmethod
    def _font(px: int) -> QtGui.QFont:
        font = QtGui.QFont(_CARD_FONT)
        font.setPixelSize(px)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        return font

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.scale(self.width() / _CARD_BASE_W, self.height() / _CARD_BASE_H)
        inner = QtCore.QRectF(2, 2, _CARD_BASE_W - 4, _CARD_BASE_H - 4)
        fill = QtGui.QLinearGradient(inner.topLeft(), inner.bottomLeft())
        fill.setColorAt(0.0, QtGui.QColor("#071a2c"))
        fill.setColorAt(1.0, QtGui.QColor("#030b16"))
        painter.setBrush(QtGui.QBrush(fill))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(inner, 12, 12)

        # アイコン: 全カードで同じ中心・同じ大きさ(縦横の長い方を_CARD_ICON_BOXに揃える)
        box = QtCore.QRectF(_CARD_ICON_CENTER.x() - _CARD_ICON_BOX / 2,
                            _CARD_ICON_CENTER.y() - _CARD_ICON_BOX / 2, _CARD_ICON_BOX, _CARD_ICON_BOX)
        if self._route in _VECTOR_ICONS:
            _VECTOR_ICONS[self._route](painter, box)
        elif self._pixmap is not None and not self._pixmap.isNull():
            pw, ph = self._pixmap.width(), self._pixmap.height()
            scale = _CARD_ICON_BOX / max(pw, ph)
            w, h = pw * scale, ph * scale
            painter.drawPixmap(QtCore.QRectF(_CARD_ICON_CENTER.x() - w / 2, _CARD_ICON_CENTER.y() - h / 2, w, h),
                               self._pixmap, QtCore.QRectF(0, 0, pw, ph))

        # 文字: 日本語表示は「日本語タイトル(大)+英語(小)」の2行、英語表示は英語1行
        # (周波数カードのように値を出すカードは英語表示でも2行)。
        painter.setPen(QtGui.QColor("white"))
        if self._english:
            title, sub, title_px = self._title_en, self._sub_en, _CARD_TITLE_EN_PX
        else:
            title, sub, title_px = self._title_ja, self._sub_ja, _CARD_TITLE_JA_PX
        if sub:
            painter.setFont(self._font(title_px))
            painter.drawText(QtCore.QRectF(_CARD_TEXT_X, 20, _CARD_TEXT_W, 36),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, title)
            painter.setPen(QtGui.QColor("#cfd9df"))
            painter.setFont(self._font(_CARD_SUB_PX))
            painter.drawText(QtCore.QRectF(_CARD_TEXT_X, 58, _CARD_TEXT_W, 26),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, sub)
        else:
            # 英語1行: カード幅に収まらない長い名称(RSSI Measurement等)だけ文字を縮める。
            px = title_px
            while px > 16 and QtGui.QFontMetricsF(self._font(px)).horizontalAdvance(title) > _CARD_TEXT_W - 4:
                px -= 1
            painter.setFont(self._font(px))
            painter.drawText(QtCore.QRectF(_CARD_TEXT_X, 20, _CARD_TEXT_W, 67),
                             QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, title)
        painter.end()


class HomeScreen(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setStyleSheet("background-color: black;")

        self._mock_mode = False
        self._mock_canvas = None
        if self._build_illustrated_home():
            return

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 24, 12, 12)
        outer.setSpacing(12)

        title = QtWidgets.QLabel(
            "Shonan_Lite <span style='font-size:9pt;'>for</span> RasPI4"
        )
        title.setStyleSheet(
            "color: white; font-size: 14pt; font-weight: bold; font-style: italic; "
            "font-family: 'DejaVu Serif', 'Times New Roman', serif;")
        title.setAlignment(QtCore.Qt.AlignLeft)
        outer.addWidget(title)

        main_menu_label = QtWidgets.QLabel("Main Menu")
        main_menu_label.setStyleSheet("color: white; font-size: 11pt; font-weight: bold;")
        main_menu_label.setAlignment(QtCore.Qt.AlignCenter)
        outer.addWidget(main_menu_label)

        grid_widget = QtWidgets.QWidget()
        grid_widget.setStyleSheet("background-color: black;")
        grid = QtWidgets.QGridLayout(grid_widget)
        grid.setSpacing(14)
        self._buttons = {}
        for i, (ja, en, route) in enumerate(_BUTTONS):
            btn = NavButton(ja, en)
            if route == "fec":
                _style_special_card(btn, _fec_icon())
            elif route == "pluto_reboot":
                _style_special_card(btn, _restart_icon())
            if route == "shutdown":
                btn.setStyleSheet(
                    btn.styleSheet() + "QPushButton { color: #ff4040; }"
                )
                btn.clicked.connect(self._on_shutdown_clicked)
            elif route == "pluto_reboot":
                btn.clicked.connect(self._on_app_restart_clicked)
            elif route == "pluto_power_cycle":
                btn.clicked.connect(self._on_pluto_power_cycle_clicked)
            else:
                btn.clicked.connect(lambda _, r=route: self.main_window.navigate_to(r))
            self._buttons[route] = btn
            grid.addWidget(btn, i // 5, i % 5, QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        outer.addWidget(grid_widget, 1)

        datv_label = QtWidgets.QLabel("Digital Amateur TV System (DATV)")
        datv_label.setStyleSheet("color: white; font-size: 8pt;")
        datv_label.setAlignment(QtCore.Qt.AlignRight)
        outer.addWidget(datv_label)

    def _on_shutdown_clicked(self) -> None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("電源オフ")
        dialog.setModal(True)
        dialog.setFixedSize(560, 320)
        dialog.setStyleSheet("QDialog { background: #101416; color: white; } QLabel { color: white; }")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)
        icon = _PowerSymbol("#f05a45", 72)
        layout.addWidget(icon, 0, QtCore.Qt.AlignCenter)
        message = QtWidgets.QLabel("システムの電源をオフにします。\nよろしいですか？")
        message.setAlignment(QtCore.Qt.AlignCenter)
        message.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(message)
        buttons = QtWidgets.QHBoxLayout()
        shutdown = QtWidgets.QPushButton("電源をオフにする")
        cancel = QtWidgets.QPushButton("キャンセル")
        shutdown.setMinimumHeight(44)
        cancel.setMinimumHeight(44)
        shutdown.setStyleSheet("QPushButton { background: #f05a45; color: white; border: none; border-radius: 6px; padding: 6px 18px; font-weight: bold; }")
        cancel.setStyleSheet("QPushButton { background-color: #14235c; color: white; border: 1px solid #3b5159; border-radius: 6px; padding: 6px 18px; font-weight: bold; } QPushButton:pressed { background-color: #0c1638; }")
        shutdown.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        buttons.addWidget(shutdown)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        if _run_as_overlay(dialog) != QtWidgets.QDialog.Accepted:
            return
        try:
            subprocess.Popen(["sudo", "shutdown", "-h", "now"])
        except OSError as exc:
            error_dialog(self, "シャットダウン失敗", str(exc))

    def _build_illustrated_home(self) -> bool:
        english = is_english(self.main_window.settings)
        images_dir = Path(__file__).resolve().parents[2] / "docs" / "images"
        image_path = images_dir / "home_illustrated_langstone_en.png" if english \
            else images_dir / "home_illustrated_langstone.png"
        if not image_path.exists():
            image_path = images_dir / "home_illustrated_langstone.png"
        if not image_path.exists():
            image_path = images_dir / "home_illustrated_mockup.png"
        if not image_path.exists():
            return False

        self._mock_mode = True
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        canvas = QtWidgets.QWidget(self)
        canvas.setStyleSheet("background-color: black;")
        self._mock_canvas = canvas

        background = QtWidgets.QLabel(canvas)
        background.setPixmap(QtGui.QPixmap(str(image_path)))
        background.setScaledContents(True)
        background.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._mock_background = background
        self._mock_overlays = []

        self._scaled_font_labels = []
        # 全カード共通: 幅310x高さ111(1600x1024基準)。列は68/386/704/1022
        # (列間隔318、カード同士は重ならない)。行は183/318/453/588/723
        # (行間隔24で統一。以前は39/27/22/15pxとばらばらだった)。
        # 5段目3枚目(Pluto電源)はタワーの絵に重なるが、ユーザー了承の上で
        # 許容している。
        card_rects = [
            (68, 183, 310, 111), (386, 183, 310, 111), (704, 183, 310, 111), (1022, 183, 310, 111),
            (68, 318, 310, 111), (386, 318, 310, 111), (704, 318, 310, 111), (1022, 318, 310, 111),
            (68, 453, 310, 111), (386, 453, 310, 111), (704, 453, 310, 111), (1022, 453, 310, 111),
            (68, 588, 310, 111), (386, 588, 310, 111), (704, 588, 310, 111), (1022, 588, 310, 111),
            (68, 723, 310, 111), (386, 723, 310, 111), (704, 723, 310, 111),
        ]
        # 全カードをHomeCardで描く(背景画像のカード部分は完全に覆う)。表示名は_BUTTONSのまま、
        # 一部のカードだけ日本語表示のサブ行を上書きする。周波数カードのサブ行は値(on_showで更新)。
        sub_ja_override = {"langstone": "SDRトランシーバー", "frequency": "", "pluto_power_cycle": "Pluto Power"}
        title_en_override = {"langstone": "Langstone"}
        for (ja, en, route), rect in zip(_BUTTONS, card_rects):
            card = HomeCard(canvas, route, ja, sub_ja_override.get(route, en),
                            title_en_override.get(route, en), english)
            card._mock_rect = rect
            self._mock_overlays.append(card)
            if route == "frequency":
                self._frequency_value = card

        self._buttons = {}
        for (ja, en, route), rect in zip(_BUTTONS, card_rects):
            button = QtWidgets.QPushButton(canvas)
            button.setFocusPolicy(QtCore.Qt.NoFocus)
            button.setToolTip(f"{ja} / {en}")
            button.setStyleSheet(
                "QPushButton { background: transparent; border: 2px solid #247f9f; border-radius: 12px; }"
                "QPushButton:pressed { background: rgba(50, 110, 220, 45); border: 2px solid #4d8dff; }")
            self._connect_home_action(button, route)
            self._buttons[route] = button
            button._mock_rect = rect

        outer.addWidget(canvas, 1)
        self._position_mock_home()
        return True

    def _connect_home_action(self, button: QtWidgets.QPushButton, route: str) -> None:
        if route == "shutdown":
            button.clicked.connect(self._on_shutdown_clicked)
        elif route == "pluto_reboot":
            button.clicked.connect(self._on_app_restart_clicked)
        elif route == "langstone":
            button.clicked.connect(self._on_langstone_clicked)
        elif route == "tx":
            button.clicked.connect(self._on_transmit_clicked)
        elif route == "pluto_power_cycle":
            button.clicked.connect(self._on_pluto_power_cycle_clicked)
        else:
            button.clicked.connect(lambda _, r=route: self.main_window.navigate_to(r))

    # モック画像の基準解像度(1600x1024)上でのカード全体の水平オフセット。
    # 負の値で左、正の値で右にずらす。ずらした分だけ幅を縮め、ずらした方向と
    # 反対側の端をキャンバス内(元の位置)に収めて外枠が欠けないようにする。
    _HOME_CARD_SHIFT_PX = 0

    def _mock_scale_rect(self, rect, content_x: int, content_width: int, height: int):
        """1600x1024基準の_mock_rectを、水平オフセット・縮小込みで実画面座標へ変換する。"""
        x, y, w, h = rect
        return (
            content_x + round(x * content_width / 1600),
            round(y * height / 1024),
            round(w * content_width / 1600),
            round(h * height / 1024),
        )

    def _position_mock_home(self) -> None:
        if self._mock_canvas is None:
            return
        width = max(1, self._mock_canvas.width())
        height = max(1, self._mock_canvas.height())
        shift_px = round(abs(self._HOME_CARD_SHIFT_PX) * width / 1600)
        content_x = shift_px if self._HOME_CARD_SHIFT_PX >= 0 else 0
        content_width = max(1, width - shift_px)
        self._mock_background.setGeometry(content_x, 0, content_width, height)
        for overlay in self._mock_overlays:
            overlay.setGeometry(*self._mock_scale_rect(overlay._mock_rect, content_x, content_width, height))
        for button in self._buttons.values():
            button.setGeometry(*self._mock_scale_rect(button._mock_rect, content_x, content_width, height))
        # 背景画像に焼き込んだタイトル文字も画面サイズに応じて拡大縮小されるため、
        # このオーバーレイの文字サイズもキャンバス幅に比例させて見かけを揃える。
        for label, base_px in getattr(self, "_scaled_font_labels", []):
            font = label.font()
            font.setPixelSize(max(10, round(base_px * content_width / 1600)))
            label.setFont(font)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_mock_home()

    def _on_transmit_clicked(self) -> None:
        self.main_window.navigate_to("tx")

    def _on_langstone_clicked(self) -> None:
        try:
            # ★Langstone V2自身は12V電源(GPIO26)に触れないため、切替時に
            # ここで明示的にONを送っておく(Langstone側の送信でPA電源が
            # 入っていない、という事態を避ける)。
            host = self.main_window.settings.ptt_controller_host
            if host:
                try:
                    _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "on")
                except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
                    print(f"[MCU1] GPIO26 ON通知に失敗しました(Langstone切替): {exc}", flush=True)
            Path.home().joinpath(".pi4_boot_mode_langstone").touch()
            subprocess.Popen(["sudo", "/bin/systemctl", "start", "--no-block", "langstone.service"])
        except OSError as exc:
            error_dialog(self, "Langstone起動失敗", str(exc))

    def _on_app_restart_clicked(self) -> None:
        if not confirm_dialog(
            self, "アプリ再起動", "アプリとPlutoを再起動しますか？(送受信中の場合は中断されます)"
        ):
            return
        self.main_window.restart_app()

    def _on_pluto_power_cycle_clicked(self) -> None:
        """PA_Power/PTTコントローラ(ESP32)のGPIO26(12V電源)をOFF→3秒待ち→ONする
        (Pluto+含む12V系統全体の電源サイクル)。"""
        host = self.main_window.settings.ptt_controller_host
        if not host:
            error_dialog(
                self, "PTTコントローラ未設定",
                "設定画面でPA_Power/PTTコントローラ(ESP32)のIPアドレスを設定してください。")
            return
        try:
            _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "off")
        except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
            error_dialog(self, "Pluto電源OFF失敗", str(exc))
            return
        QtCore.QTimer.singleShot(3000, lambda: self._pluto_power_on(host))

    def _pluto_power_on(self, host: str) -> None:
        try:
            _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "on")
        except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
            error_dialog(self, "Pluto電源ON失敗", str(exc))

    def on_show(self) -> None:
        settings = self.main_window.settings
        lo_hz = settings.effective_lo_hz()
        not_set = "Not Set" if is_english(settings) else "未設定"
        if self._mock_mode:
            self._frequency_value.setText(f"{lo_hz / 1000:.0f} kHz" if lo_hz else not_set)
            return
        if lo_hz is not None:
            self._buttons["frequency"].set_subtitle(f"{lo_hz / 1000:.0f} kHz")
        else:
            self._buttons["frequency"].set_subtitle(not_set)


def create(main_window) -> QtWidgets.QWidget:
    return HomeScreen(main_window)
