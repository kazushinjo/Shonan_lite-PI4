"""Boot-time application selector for the Raspberry Pi 4 touch display."""
from __future__ import annotations

import http.client
import os
import subprocess
import sys
import urllib.error
from pathlib import Path

def _configure_touch() -> None:
    """Bind Qt to the Raspberry Pi touchscreen without a fixed event number."""
    for name_file in sorted(Path("/sys/class/input").glob("event*/device/name")):
        try:
            device_name = name_file.read_text(encoding="utf-8").strip().lower()
            if device_name == "raspberrypi-ts" or "ft5x06" in device_name:
                event = name_file.parents[1].name
                os.environ["QT_QPA_EGLFS_DISABLE_INPUT"] = "1"
                os.environ["QT_QPA_GENERIC_PLUGINS"] = (
                    f"evdevtouch:/dev/input/{event}"
                )
                return
        except OSError:
            continue


_configure_touch()

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5 import QtCore, QtWidgets

import settings_store
from backend import PTT_CHANNEL_POWER, _send_ptt_channel_state
from widgets import _run_as_overlay


MARKER = Path.home() / ".pi4_boot_mode_langstone"
LANGSTONE_UNIT = Path("/etc/systemd/system/langstone.service")


class IPSettingDialog(QtWidgets.QDialog):
    """Touch-only numeric keypad for the Pluto IP address."""

    def __init__(self, current_ip: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pluto IP設定")
        self.setModal(True)
        self.setStyleSheet(
            "QDialog{background:#0a0c0d;color:white;}"
            "QLabel{color:white;}"
            "QPushButton{font-size:20px;min-height:56px;border-radius:8px;"
            "background:#1d4388;color:white;border:1px solid #2c5aa8;}"
            "QPushButton:pressed{background:#102a5c;}"
        )
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        label = QtWidgets.QLabel("PlutoのIPアドレス\nPluto IP address")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("font-size:18px;font-weight:bold;")
        layout.addWidget(label)

        self.edit = QtWidgets.QLineEdit(current_ip)
        self.edit.setAlignment(QtCore.Qt.AlignCenter)
        self.edit.setReadOnly(True)
        self.edit.setStyleSheet(
            "font-size:30px;font-weight:bold;padding:10px;"
            "background:#000000;color:#7fd4ff;border:1px solid #3b5159;"
            "border-radius:6px;"
        )
        layout.addWidget(self.edit)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        keys = ["7", "8", "9", "4", "5", "6", "1", "2", "3", "C", "0", "←"]
        for i, key in enumerate(keys):
            button = QtWidgets.QPushButton(key)
            button.setMinimumWidth(70)
            button.clicked.connect(lambda _checked=False, k=key: self._on_key(k))
            grid.addWidget(button, i // 3, i % 3)
        dot_button = QtWidgets.QPushButton(".")
        dot_button.setMinimumWidth(70)
        dot_button.clicked.connect(lambda: self._on_key("."))
        grid.addWidget(dot_button, 3, 3)
        layout.addLayout(grid)

        buttons = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("キャンセル / Cancel")
        ok = QtWidgets.QPushButton("保存 / Save")
        ok.setStyleSheet("background:#1677ff;font-weight:bold;")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _on_key(self, key: str) -> None:
        if key == "C":
            self.edit.setText("")
        elif key == "←":
            self.edit.setText(self.edit.text()[:-1])
        else:
            self.edit.setText(self.edit.text() + key)

    def value(self) -> str:
        return self.edit.text().strip()


class BootMenu(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._selected = False
        self.setWindowTitle("Shonan boot menu")
        self.setStyleSheet("background:#050505;color:white;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(45, 15, 45, 55)
        layout.setSpacing(24)

        title = QtWidgets.QLabel("起動するアプリを選択してください")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:28px;font-weight:bold;")
        layout.addWidget(title)

        shonan = QtWidgets.QPushButton("Shonan_Lite (DATV)\nDATV送受信")
        langstone = QtWidgets.QPushButton("Langstone V2Modify\nSDRトランシーバー")
        for button in (shonan, langstone):
            button.setMinimumHeight(115)
            button.setStyleSheet(
                "QPushButton{font-size:25px;font-weight:bold;background:#1677ff;"
                "border:3px solid white;border-radius:16px;}"
                "QPushButton:pressed{background:#102a5c;}"
                "QPushButton:disabled{background:#333;color:#888;}"
            )
            layout.addWidget(button)

        shonan.clicked.connect(lambda: self._launch(False))
        langstone.clicked.connect(lambda: self._launch(True))
        if not LANGSTONE_UNIT.exists():
            langstone.setEnabled(False)
            langstone.setText("Langstone V2Modify\nインストール未完了")

        self.ip_button = QtWidgets.QPushButton()
        self.ip_button.setMinimumHeight(64)
        self.ip_button.setStyleSheet(
            "QPushButton{font-size:16px;font-weight:bold;background:#1d4388;"
            "border:2px solid #2c5aa8;border-radius:12px;color:#7fd4ff;}"
            "QPushButton:pressed{background:#102a5c;color:white;}"
        )
        self.ip_button.clicked.connect(self._on_ip_setting)
        layout.addWidget(self.ip_button)
        self._refresh_ip_button()

    def _refresh_ip_button(self) -> None:
        try:
            current = settings_store.load().pluto_host()
        except Exception:
            current = "192.168.0.10"
        self.ip_button.setText(f"Pluto IP設定: {current}  /  Pluto IP Setting")

    def _on_ip_setting(self) -> None:
        settings = settings_store.load()
        dialog = IPSettingDialog(settings.pluto_host(), self)
        if _run_as_overlay(dialog) != QtWidgets.QDialog.Accepted:
            return
        try:
            host = settings_store.normalize_pluto_host(dialog.value())
        except ValueError as exc:
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Critical, "Pluto IP設定エラー", str(exc),
                QtWidgets.QMessageBox.Ok, self)
            _run_as_overlay(box)
            return
        settings.pluto_uri = f"ip:{host}"
        settings_store.save(settings)
        self._refresh_ip_button()

    def _launch(self, langstone: bool) -> None:
        if self._selected:
            return
        self._selected = True
        if langstone:
            # ★Langstone V2自身は12V電源(GPIO26)に触れないため、起動メニューから
            # 直接Langstoneを選んだ場合もHome画面の「Langstone V2Modify」ボタンと
            # 同様にここで明示的にONを送っておく(PA電源が入っていない状態で
            # Langstone側の送信が行われる事態を避ける)。
            host = settings_store.load().ptt_controller_host
            if host:
                try:
                    _send_ptt_channel_state(host, PTT_CHANNEL_POWER, "on")
                except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
                    print(f"[MCU1] GPIO26 ON通知に失敗しました(起動メニューLangstone選択): {exc}", flush=True)
            MARKER.touch()
            unit = "langstone.service"
        else:
            MARKER.unlink(missing_ok=True)
            unit = "shonan-gui.service"
        subprocess.run(["sudo", "/bin/systemctl", "start", "--no-block", unit], check=False)
        QtCore.QTimer.singleShot(300, QtWidgets.QApplication.quit)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    menu = BootMenu()
    menu.showFullScreen()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
