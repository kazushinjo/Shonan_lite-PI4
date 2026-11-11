"""モック7番カードに合わせた変調方式画面。"""
from __future__ import annotations

import math

from PyQt5 import QtCore, QtGui, QtWidgets

from settings_store import MODULATION_SCHEMES, supported_fec_rates
from i18n import tr
from widgets import SettingsSubScreen


# APSKのリング半径比(ETSI EN 302 307-1)。FEC画面の符号化率に合わせて描く。
# 16APSK: 外側/内側、32APSK: (中間/内側, 外側/内側)。
_APSK16_GAMMA = {"2/3": 3.15, "3/4": 2.85, "4/5": 2.75, "5/6": 2.70, "8/9": 2.60, "9/10": 2.57}
_APSK32_GAMMA = {"3/4": (2.84, 5.27), "4/5": (2.72, 4.87), "5/6": (2.64, 4.64),
                 "8/9": (2.54, 4.33), "9/10": (2.53, 4.30)}


def _ring(count: int, radius: float, offset: float) -> list[tuple[float, float]]:
    return [(radius * math.cos(offset + 2 * math.pi * i / count),
             radius * math.sin(offset + 2 * math.pi * i / count)) for i in range(count)]


def constellation_points(scheme: str, fec_rate: str) -> list[tuple[float, float]]:
    """コンステレーション図の点(最外周を半径1とする)。"""
    if scheme == "QPSK":
        return _ring(4, 1.0, math.pi / 4)
    if scheme == "16APSK":
        gamma = _APSK16_GAMMA.get(fec_rate, 2.85)
        return _ring(4, 1 / gamma, math.pi / 4) + _ring(12, 1.0, math.pi / 12)
    if scheme == "32APSK":
        gamma1, gamma2 = _APSK32_GAMMA.get(fec_rate, (2.84, 5.27))
        return (_ring(4, 1 / gamma2, math.pi / 4) + _ring(12, gamma1 / gamma2, math.pi / 12)
                + _ring(16, 1.0, 0.0))
    return _ring(8, 1.0, 0.0)


class ConstellationWidget(QtWidgets.QWidget):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.setMinimumSize(300, 190)
        self.setStyleSheet("background: #050607; border: 1px solid #46545b; border-radius: 8px;")

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(18, 12, -18, -14)
        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.34
        painter.setPen(QtGui.QPen(QtGui.QColor("#8397a0"), 1))
        painter.drawLine(rect.left(), center.y(), rect.right(), center.y())
        painter.drawLine(center.x(), rect.top(), center.x(), rect.bottom())
        painter.drawLine(rect.right() - 6, center.y(), rect.right(), center.y())
        painter.drawLine(center.x(), rect.top() + 6, center.x(), rect.top())
        painter.drawLine(center.x(), rect.bottom() - 6, center.x(), rect.bottom())

        settings = self.screen.main_window.settings
        points = constellation_points(settings.modulation_scheme, settings.fec_rate)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor("#38b8e3"))
        point_radius = 4 if len(points) <= 16 else 3
        for x, y in points:
            painter.drawEllipse(QtCore.QPointF(center.x() + x * radius,
                                                center.y() - y * radius),
                                point_radius, point_radius)


class ModulationScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("変調方式 / Modulation", lambda: main_window.navigate_to("home"))
        self.main_window = main_window
        self.header_bar.hide()
        self.body_layout.setContentsMargins(10, 8, 10, 10)
        self.body_layout.setSpacing(6)

        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame { background: #0a0c0d; border: 1px solid #34434b; border-radius: 14px; }"
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
        left.setStyleSheet("QFrame { background: #0f1214; border: 1px solid #34434b; border-radius: 10px; }")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(10, 8, 10, 8)
        left_layout.setSpacing(1)
        label = QtWidgets.QLabel(tr("変調方式選択", "Modulation Selection"))
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        left_layout.addWidget(label)
        self._group = QtWidgets.QButtonGroup(self)
        for scheme in MODULATION_SCHEMES:
            button = QtWidgets.QPushButton(scheme)
            button.setCheckable(True)
            button.setMinimumHeight(28)
            button.setStyleSheet(
                "QPushButton { background-color: #303538; color: white; border: none;"
                " border-radius: 8px; padding: 4px 12px; text-align: left;"
                " font-size: 14px; font-weight: bold; min-height: 20px; }"
                "QPushButton:checked { background-color: #1677ff; }"
                "QPushButton:pressed { background-color: #102a5c; }"
                "QPushButton:disabled { color: #777777; background-color: #171a1c; }"
            )
            button.setChecked(main_window.settings.modulation_scheme == scheme)
            button.toggled.connect(lambda checked, s=scheme: checked and self._select(s))
            self._group.addButton(button)
            left_layout.addWidget(button)
        left_layout.addStretch(1)
        columns.addWidget(left, 1)

        right = QtWidgets.QFrame()
        right.setStyleSheet("QFrame { background: #0f1214; border: 1px solid #34434b; border-radius: 10px; }")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(4)
        title = QtWidgets.QLabel(tr("コンステレーション", "Constellation"))
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        right_layout.addWidget(title)
        self.constellation = ConstellationWidget(self)
        right_layout.addWidget(self.constellation, 1)
        columns.addWidget(right, 2)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(QtWidgets.QLabel(tr("ビット/シンボル：", "Bits/Symbol:")))
        self.bits_label = QtWidgets.QLabel()
        self.bits_label.setStyleSheet("font-weight: bold;")
        bottom.addWidget(self.bits_label)
        bottom.addStretch(1)
        self.scheme_label = QtWidgets.QLabel()
        self.scheme_label.setStyleSheet("font-weight: bold; color: #54bce0;")
        bottom.addWidget(self.scheme_label)
        home_btn = QtWidgets.QPushButton(tr("ホームに戻る", "Back to Home"))
        home_btn.setFixedHeight(34)
        home_btn.clicked.connect(lambda: self.main_window.navigate_to("home"))
        bottom.addWidget(home_btn)
        outer.addLayout(bottom)
        self._update_view()

    def _select(self, scheme: str) -> None:
        settings = self.main_window.settings
        settings.modulation_scheme = scheme
        rates = supported_fec_rates(scheme)
        if settings.fec_auto:
            settings.apply_auto_fec()
        elif settings.fec_rate not in rates:
            # その変調方式に無いFECのままだと送受信開始時に拒否されるため、
            # 最も誤りに強い(先頭の)符号化率へ合わせる。
            settings.fec_rate = rates[0]
        self.main_window.save_settings()
        self._update_view()

    def _update_view(self) -> None:
        scheme = self.main_window.settings.modulation_scheme
        bits = {"QPSK": 2, "8PSK": 3, "16APSK": 4, "32APSK": 5}.get(scheme, 0)
        self.bits_label.setText(str(bits))
        self.scheme_label.setText(scheme)
        self.constellation.update()


def create(main_window) -> QtWidgets.QWidget:
    return ModulationScreen(main_window)
