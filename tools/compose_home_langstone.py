from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets


root = Path(__file__).resolve().parents[1]
app = QtWidgets.QApplication([])
source_path = root / "pi4" / "docs" / "images" / "home_illustrated_mockup.png"
target_path = root / "pi4" / "docs" / "images" / "home_illustrated_langstone.png"

image = QtGui.QImage(str(source_path)).convertToFormat(QtGui.QImage.Format_ARGB32)

card_rect = QtCore.QRect(68, 183, 322, 129)
card = image.copy(card_rect).scaled(322, 107, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
painter = QtGui.QPainter(card)
painter.setRenderHint(QtGui.QPainter.Antialiasing)

inner = QtCore.QRectF(4, 4, 314, 99)
fill = QtGui.QLinearGradient(inner.topLeft(), inner.bottomLeft())
fill.setColorAt(0.0, QtGui.QColor("#071a2c"))
fill.setColorAt(1.0, QtGui.QColor("#030b16"))
painter.setBrush(QtGui.QBrush(fill))
painter.setPen(QtCore.Qt.NoPen)
painter.drawRoundedRect(inner, 12, 12)

icon_center = QtCore.QPointF(52, 52)
painter.setPen(QtGui.QPen(QtGui.QColor("white"), 3, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
for radius in (10, 18, 26):
    painter.drawArc(QtCore.QRectF(icon_center.x() - radius, icon_center.y() - radius,
                                  radius * 2, radius * 2), 35 * 16, 110 * 16)
painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))
painter.setPen(QtCore.Qt.NoPen)
painter.drawEllipse(icon_center, 3.5, 3.5)

font = QtGui.QFont("Noto Sans CJK JP", 26)
font.setWeight(QtGui.QFont.Thin)
font.setStyleStrategy(QtGui.QFont.PreferAntialias)
painter.setFont(font)
painter.setPen(QtGui.QColor("white"))
painter.drawText(QtCore.QRectF(108, 27, 205, 30), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Langstone")

small_font = QtGui.QFont("Noto Sans CJK JP", 16)
small_font.setWeight(QtGui.QFont.Thin)
small_font.setStyleStrategy(QtGui.QFont.PreferAntialias)
painter.setFont(small_font)
painter.drawText(QtCore.QRectF(108, 56, 205, 25), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "SDRトランシーバー")
painter.setBrush(QtCore.Qt.NoBrush)
painter.setPen(QtGui.QPen(QtGui.QColor("#247f9f"), 2))
painter.drawRoundedRect(QtCore.QRectF(1, 1, 320, 105), 15, 15)
painter.end()

image_copy_painter = QtGui.QPainter(image)
image_copy_painter.drawImage(QtCore.QPoint(68, 730), card)
image_copy_painter.end()

if not image.save(str(target_path), "PNG"):
    raise SystemExit("failed to save composed home image")
