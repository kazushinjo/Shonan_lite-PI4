"""Pi4 GUIの日本語/英語切替。"""
from __future__ import annotations

from PyQt5 import QtWidgets


_TRANSLATIONS = {
    "日本語": "Japanese",
    "ホームへ戻る": "Back to Home",
    "ホームに戻る": "Back to Home",
    "設定": "Settings",
    "設定画面": "Settings",
    "表示言語": "Display Language",
    "バンドプロファイル / Band Profile": "Band Profile",
    "送信先 (Pluto Tx)": "Transmit Destination (Pluto Tx)",
    "オンデバイス復調": "On-device Demodulation",
    "オンデバイス復調 (GNU Radio)": "On-device Demodulation (GNU Radio)",
    "受信診断 / RX Diagnostics": "RX Diagnostics",
    "システム日時 / System Date & Time": "System Date & Time",
    "この日時を設定 / Set": "Set Date and Time",
    "ホームに戻る": "Back to Home",
    "プリセット": "Presets",
    "プリセット選択・登録": "Preset Selection / Registration",
    "登録/変更": "Save / Edit",
    "削除": "Delete",
    "未登録": "Not Registered",
    "送信": "Transmit",
    "受信": "Receive",
    "周波数": "Frequency",
    "シンボルレート": "Symbol Rate",
    "誤り訂正": "FEC",
    "変調方式": "Modulation",
    "映像ソース": "Video Source",
    "出力設定": "Stream Output",
    "RXゲイン": "RX Gain",
    "TX出力": "TX Power",
    "相手局検索": "Find Station",
    "機器試験": "Diagnostic",
    "ヘルプ": "Help",
    "アプリ再起動": "App Restart",
    "電源オフ": "Power Off",
    "周波数入力": "Frequency Input",
    "バンド選択": "Band Selection",
    "周波数 / Frequency": "Frequency",
    "シンボルレート / Symbol Rate": "Symbol Rate",
    "誤り訂正 / FEC": "FEC",
    "変調方式 / Modulation": "Modulation",
    "映像ソース / Video Source": "Video Source",
    "出力設定 / Stream Output": "Stream Output",
    "RXゲイン / RX Gain": "RX Gain",
    "TX出力 / TX Power": "TX Power",
    "機器試験 / Diagnostic": "Diagnostic",
    "受信 / Receive": "Receive",
    "送信 / Transmit": "Transmit",
    "相手局検索 / Find Station": "Find Station",
    "出力先設定": "Stream Output Settings",
    "出力先": "Output Destination",
    "出力情報": "Output Information",
    "ステータス: 待機中": "Status: Standby",
    "送信開始前": "Before Transmit",
    "送信停止中": "Transmit Stopped",
    "送信開始": "Start Transmit",
    "受信停止中": "Receive Stopped",
    "受信開始": "Start Receive",
    "音量": "Volume",
    "映像ソース選択": "Video Source Selection",
    "音声設定": "Audio Settings",
    "プレビュー": "Preview",
    "解像度": "Resolution",
    "フレームレート": "Frame Rate",
    "検索範囲 / Search Range": "Search Range",
    "停止中": "Stopped",
    "現在: --": "Current: --",
    "最良: --": "Best: --",
    "検索開始 / Start": "Start Search",
    "プリセット選択": "Preset Selection",
    "カスタム設定": "Custom Settings",
    "シンボルレート (kS/s)": "Symbol Rate (kS/s)",
    "帯域幅の目安": "Estimated Bandwidth",
    "現在の設定": "Current Setting",
    "RXゲイン調整": "RX Gain Adjustment",
    "自動調整": "Automatic Adjustment",
    "信号レベル": "Signal Level",
    "出力減衰量設定": "TX Attenuation",
    "出力減衰": "TX Attenuation",
    "0 dB = 最大出力、値が小さいほど減衰します。": "0 dB = maximum output; higher values reduce output.",
    "変調方式選択": "Modulation Selection",
    "コンステレーション": "Constellation",
    "ビット/シンボル：": "Bits/Symbol: ",
    "待機中": "Standby",
    "全体試験": "Run All Tests",
    "カメラ＋音声診断": "Camera + Audio Diagnostic",
    "診断結果": "Diagnostic Results",
    "システム状態: 待機中": "System Status: Standby",
    "電源オフ": "Power Off",
    "システムの電源をオフにします。\nよろしいですか？": "The system will power off.\nAre you sure?",
    "シャットダウン失敗": "Shutdown Failed",
    "アプリ再起動\nApp Restart": "App Restart",
    "誤り訂正\nFEC": "FEC",
    "操作・設定・エラーを検索...": "Search operations, settings, and errors...",
    "未設定": "Not Set",
    "設定値": "Setting",
    "現在の周波数: ": "Current Frequency: ",
    "現在の設定: ": "Current Setting: ",
    "送信中": "Transmitting",
    "受信中": "Receiving",
    "未設定": "Not Set",
    "接続中": "Connected",
    "未接続": "Disconnected",
    "切断中": "Disconnected",
    "オーバーヘッド: ": "Overhead: ",
    "システム状態: ": "System Status: ",
    "Pluto再起動エラー": "Pluto Restart Error",
    "Pluto接続エラー": "Pluto Connection Error",
    "TXへ接続中...": "Connecting to TX...",
    "RXへ接続中...": "Connecting to RX...",
    "TX健全性確認中...": "Checking TX health...",
    "RX継続確認中...": "Checking RX continuity...",
    "ファイル選択済み": "File Selected",
    "プレビュー待機中": "Waiting for Preview",
    "カメラ映像を取得できません": "Unable to acquire camera video",
    "カメラ (USB)": "Camera (USB)",
    "出力": "Output",
    "パケット数": "Packets",
    "フレーム数": "Frames",
    "接続": "Connection",
    "Receive画面へ": "Go to Receive",
    "状態": "Status",
    "ビットレート": "Bitrate",
    "パケット/秒": "Packets/sec",
    "エラー": "Errors",
    "Transmit画面へ": "Go to Transmit",
    "FEC(パリティ)": "FEC (Parity)",
    "ファイル選択": "Select File",
    "Transmit先ポート": "Transmit Port",
    "ReceiveTSポート": "Receive TS Port",
    "ステータスポート": "Status Port",
    "プロトコル": "Protocol",
    "ポート": "Port",
    "項目                 ステータス    結果": "Item                 Status       Result",
    "推奨Wi-Fi帯: ": "Recommended Wi-Fi: ",
    "目安ビットレート: ": "Estimated Bitrate: ",
    "UDP-TSポート: ": "UDP-TS Port: ",
    "送受信中": "Transmitting/Receiving",
    "送受信は編集不可。": "Transmit/receive settings cannot be edited.",
    "各設定の現在値を": "Current settings are",
    "送信開始時": "when transmit starts",
    "Modulation(Modulation画面)": "Modulation (Modulation screen)",
    "と組み合わせてMod-Codを構成します。": " combines to form ModCod.",
    "対応組み合わせ以外を選ぶと": "Unsupported combinations cause an error when ",
    "時にErrorsになります。": ".",
    "送Start Receive": "Start Receive",
    "Transmitting先Port": "Transmit Port",
    "Transmit先Port": "Transmit Port",
    "いずれも可": "either is supported",
    "RF帯域と重複しないため直接干渉なし": "No direct interference with the RF band",
    "（Pluto側固定）": "(fixed on Pluto)",
    "ONのとき、Transmit画面に「Receive画面へ」ボタンを表示します。": "When ON, show a Go to Receive button on the Transmit screen.",
    "IIOプリフライト試験を実施する": "Run the IIO preflight test",
    "各Settingsの現在値をSave / Editで保存。選択時はPlutoにも反映します。": "Save current Settings values with Save / Edit. Selection also applies them to Pluto.",
    "RFループバックは TX → 40 dB以上 → RX。": "RF loopback is TX → at least 40 dB → RX.",
    "Transmitting/Receivingは編集不可。": "Transmitting/Receiving cannot be edited.",
    "現在の周波数": "Current Frequency",
    "FECモード選択": "FEC Mode Selection",
    "フレーム構成": "Frame Structure",
    "誤り訂正能力を重視した設定です。C/Nが低い環境でも安定して復調しやすくなります。": "Error correction is prioritized for stable demodulation under low C/N conditions.",
    "誤り訂正能力とスループットのバランスが取れた設定です。": "A balance between error correction and throughput.",
    "スループットを重視した設定です。良好なC/N環境で高い伝送効率を得られます。": "Throughput is prioritized for high efficiency under good C/N conditions.",
    "音声なし": "No Audio",
    "テストパターン": "Test Pattern",
    "カメラ": "Camera",
    "選択してください": "Please Select",
    "登録できません": "Cannot Register",
    "選択できません": "Cannot Select",
    "削除できません": "Cannot Delete",
    "送受信を停止してから実行してください。": "Stop transmit and receive before continuing.",
    "送信エラー": "Transmit Error",
    "受信エラー": "Receive Error",
    "Pluto設定エラー": "Pluto Settings Error",
    "Pluto接続先エラー": "Pluto Connection Error",
    "日時設定エラー": "Date and Time Error",
    "検索不可": "Search Unavailable",
    "送信中・受信中は開始できません": "Cannot start while transmitting or receiving.",
    "周波数が未設定です": "Frequency is not set.",
    "電源をオフにする": "Power Off",
    "キャンセル": "Cancel",
    "操作説明 / Help": "Operation Guide / Help",
    "目次 / Table of Contents": "Table of Contents",
    "章を選択してください": "Select a section",
}


# ---- Pi5版から移植した言語API ----
# 画面側で tr("日本語", "English") と両方を書く方式(Pi5版と共通)。現在の言語は
# モジュール変数で保持し、起動時と設定画面での切替時にmain.pyがset_language()で
# 更新する。既存の辞書方式(translate_text/apply_language)と併用できる
# (tr()で英語を選んだ文字列は辞書に日本語が無いので、apply_languageを通っても変わらない)。
JAPANESE = "JAPANESE"
ENGLISH = "ENGLISH"
_language = JAPANESE


def set_language(lang: str) -> None:
    global _language
    _language = ENGLISH if lang == ENGLISH else JAPANESE


def tr(ja: str, en: str) -> str:
    """現在の表示言語に応じてjaまたはenを返す。"""
    return en if _language == ENGLISH else ja


def is_english(settings=None) -> bool:
    """settingsを渡した場合はその言語設定、省略時は現在の表示言語(set_language)で判定する。"""
    if settings is None:
        return _language == ENGLISH
    return getattr(settings, "language", "JAPANESE") == "ENGLISH"


def translate_text(value: str, english: bool) -> str:
    if not english or not value:
        return value
    if value in _TRANSLATIONS:
        return _TRANSLATIONS[value]
    if " / " in value:
        return value.rsplit(" / ", 1)[1]
    if "\n" in value:
        parts = value.splitlines()
        if len(parts) == 2 and all(ord(c) < 128 for c in parts[1]):
            return parts[1]
    translated = value
    for _ in range(3):
        before = translated
        for source, target in sorted(_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
            translated = translated.replace(source, target)
        if translated == before:
            break
    return translated


def apply_language(root: QtWidgets.QWidget, english: bool) -> None:
    """Translate visible widget text; untranslated text remains unchanged."""
    for widget in root.findChildren(QtWidgets.QWidget) + [root]:
        if isinstance(widget, (QtWidgets.QPushButton, QtWidgets.QLabel,
                               QtWidgets.QCheckBox, QtWidgets.QRadioButton)):
            widget.setText(translate_text(widget.text(), english))
        if isinstance(widget, QtWidgets.QGroupBox):
            widget.setTitle(translate_text(widget.title(), english))
        if isinstance(widget, QtWidgets.QLineEdit):
            widget.setPlaceholderText(translate_text(widget.placeholderText(), english))
        if isinstance(widget, QtWidgets.QComboBox):
            for index in range(widget.count()):
                widget.setItemText(index, translate_text(widget.itemText(index), english))
