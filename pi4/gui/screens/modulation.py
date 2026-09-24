"""モック7番カードに合わせた変調方式画面。"""
from __future__ import annotations

import math

from PyQt5 import QtCore, QtGui, QtWidgets

from settings_store import MODULATION_SCHEMES
from widgets import SettingsSubScreen


_MOCK_SCHEMES = ("QPSK", "8PSK")


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

        scheme = self.screen.main_window.settings.modulation_scheme
        if scheme == "BPSK":
            points = [(-1, 0), (1, 0)]
        elif scheme == "QPSK":
            points = [(-.72, -.72), (.72, -.72), (-.72, .72), (.72, .72)]
        else:
            count = {"8PSK": 8, "16APSK": 16, "32APSK": 32, "64APSK": 64}.get(scheme, 4)
            points = [(math.cos(2 * math.pi * i / count),
                       math.sin(2 * math.pi * i / count)) for i in range(count)]

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
        left.setStyleSheet("QFrame { background: #191d1f; border: 1px solid #34434b; border-radius: 10px; }")
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(10, 8, 10, 8)
        left_layout.setSpacing(1)
        label = QtWidgets.QLabel("変調方式選択")
        label.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        left_layout.addWidget(label)
        self._group = QtWidgets.QButtonGroup(self)
        for scheme in _MOCK_SCHEMES:
            button = QtWidgets.QPushButton(scheme)
            button.setCheckable(True)
            button.setMinimumHeight(28)
            button.setStyleSheet(
                "QPushButton { background-color: #303538; color: white; border: none;"
                " border-radius: 8px; padding: 4px 12px; text-align: left;"
                " font-size: 14px; font-weight: bold; min-height: 20px; }"
                "QPushButton:checked { background-color: #1677ff; }"
                "QPushButton:pressed { background-color: #222222; }"
                "QPushButton:disabled { color: #777777; background-color: #252a2d; }"
            )
            button.setChecked(main_window.settings.modulation_scheme == scheme)
            if scheme not in MODULATION_SCHEMES:
                button.setEnabled(False)
                button.setToolTip("現在の送受信経路では未対応")
            else:
                button.toggled.connect(lambda checked, s=scheme: checked and self._select(s))
            self._group.addButton(button)
            left_layout.addWidget(button)
        left_layout.addStretch(1)
        columns.addWidget(left, 1)

        right = QtWidgets.QFrame()
        right.setStyleSheet("QFrame { background: #191d1f; border: 1px solid #34434b; border-radius: 10px; }")
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(4)
        title = QtWidgets.QLabel("コンステレーション")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #54bce0;")
        right_layout.addWidget(title)
        self.constellation = ConstellationWidget(self)
        right_layout.addWidget(self.constellation, 1)
        columns.addWidget(right, 2)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(QtWidgets.QLabel("ビット/シンボル："))
        self.bits_label = QtWidgets.QLabel()
        self.bits_label.setStyleSheet("font-weight: bold;")
        bottom.addWidget(self.bits_label)
        bottom.addStretch(1)
        self.scheme_label = QtWidgets.QLabel()
        self.scheme_label.setStyleSheet("font-weight: bold; color: #54bce0;")
        bottom.addWidget(self.scheme_label)
        home_btn = QtWidgets.QPushButton("ホームに戻る")
        home_btn.setFixedHeight(34)
        home_btn.clicked.connect(lambda: self.main_window.navigate_to("home"))
        bottom.addWidget(home_btn)
        outer.addLayout(bottom)
        self._update_view()

    def _select(self, scheme: str) -> None:
        self.main_window.settings.modulation_scheme = scheme
        self.main_window.save_settings()
        self._update_view()

    def _update_view(self) -> None:
        scheme = self.main_window.settings.modulation_scheme
        bits = {"BPSK": 1, "QPSK": 2, "8PSK": 3, "16APSK": 4, "32APSK": 5, "64APSK": 6}.get(scheme, 0)
        self.bits_label.setText(str(bits))
        self.scheme_label.setText(scheme)
        self.constellation.update()


def create(main_window) -> QtWidgets.QWidget:
    return ModulationScreen(main_window)
