"""FEC符号化率画面。Android版 ui/FECSettingsScreen.kt 相当。

FEC+Modulationの組み合わせは実際にTX/RXへ渡る--mod-codを合成する
(settings_store.AppSettings.mod_cod())。対応外の組み合わせは開始時に拒否される。

レイアウトはモック(shonan-16screens-mock-v4.png)のFEC画面(3カラム構成: 左に
モード選択、中央に説明、右にDATA/FEC/PARITY表示)を踏襲する。配色は既存の
ダークテーマを維持する。
"""
from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from settings_store import supported_fec_rates
from widgets import MemoNote, SettingsSubScreen

# 丸いラジオボタンではなく、右カラムのDATA/FEC/PARITYバッジと揃えた
# 四角いチップボタンでFECモードを選択する(選択時は青地)。
_CHIP_STYLE = (
    "QPushButton { background-color: #303538; color: white; border: none;"
    " border-radius: 8px; padding: 4px; font-size: 14px; font-weight: bold;"
    " min-height: 20px; }"
    "QPushButton:checked { background-color: #1677ff; }"
    "QPushButton:pressed { background-color: #222222; }"
)


def _overhead_percent(rate: str) -> float:
    num, den = rate.split("/")
    return (1 - int(num) / int(den)) * 100


def _describe(rate: str) -> str:
    overhead = _overhead_percent(rate)
    if overhead >= 40:
        return "誤り訂正能力を重視した設定です。C/Nが低い環境でも安定して復調しやすくなります。"
    if overhead >= 15:
        return "誤り訂正能力とスループットのバランスが取れた設定です。"
    return "スループットを重視した設定です。良好なC/N環境で高い伝送効率を得られます。"


class FecScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("FEC符号化率 / FEC Rate", lambda: main_window.navigate_to("home"))
        self.main_window = main_window

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.body_layout.setContentsMargins(14, 10, 14, 10)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(12)
        self.body_layout.addLayout(columns, 1)

        # --- 左カラム: FECモード選択(2列グリッドでスクロール不要にする) ---
        mode_card = QtWidgets.QFrame()
        mode_card.setFixedWidth(220)
        mode_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        mode_outer = QtWidgets.QVBoxLayout(mode_card)
        mode_outer.setContentsMargins(12, 10, 12, 10)
        mode_outer.setSpacing(6)
        mode_title = QtWidgets.QLabel("FECモード選択")
        mode_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        mode_outer.addWidget(mode_title)

        mode_grid = QtWidgets.QGridLayout()
        mode_grid.setHorizontalSpacing(8)
        mode_grid.setVerticalSpacing(4)
        self._group = QtWidgets.QButtonGroup(self)
        rates = supported_fec_rates(main_window.settings.modulation_scheme)
        if main_window.settings.fec_rate not in rates:
            # ★変調方式を切り替えた後など、現在のFEC設定がその変調方式では
            # 未対応になっている場合はここで対応済みの値へ補正して保存する。
            main_window.settings.fec_rate = rates[0]
            main_window.save_settings()
        rows_per_col = (len(rates) + 1) // 2
        for index, rate in enumerate(rates):
            chip = QtWidgets.QPushButton(rate)
            chip.setCheckable(True)
            chip.setMinimumHeight(28)
            chip.setStyleSheet(_CHIP_STYLE)
            chip.setChecked(main_window.settings.fec_rate == rate)
            chip.toggled.connect(lambda checked, r=rate: self._select(r) if checked else None)
            self._group.addButton(chip)
            mode_grid.addWidget(chip, index % rows_per_col, index // rows_per_col)
        mode_outer.addLayout(mode_grid)
        mode_outer.addStretch(1)
        columns.addWidget(mode_card)

        # --- 中央カラム: 説明 ---
        info_card = QtWidgets.QFrame()
        info_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        info_layout = QtWidgets.QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(8)

        self.current_label = QtWidgets.QLabel()
        self.current_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addWidget(self.current_label)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #cccccc; font-size: 13px;")
        info_layout.addWidget(self.description_label)

        self.overhead_label = QtWidgets.QLabel()
        self.overhead_label.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        info_layout.addWidget(self.overhead_label)

        self.overhead_bar = QtWidgets.QWidget()
        self.overhead_bar.setFixedHeight(14)
        bar_layout = QtWidgets.QHBoxLayout(self.overhead_bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(2)
        self._data_segment = QtWidgets.QLabel()
        self._data_segment.setStyleSheet("background-color: #1677ff; border-radius: 4px;")
        self._fec_segment = QtWidgets.QLabel()
        self._fec_segment.setStyleSheet("background-color: #d08a20; border-radius: 4px;")
        bar_layout.addWidget(self._data_segment)
        bar_layout.addWidget(self._fec_segment)
        info_layout.addWidget(self.overhead_bar)

        legend_row = QtWidgets.QHBoxLayout()
        legend_row.addWidget(self._legend_dot("#1677ff", "DATA"))
        legend_row.addSpacing(16)
        legend_row.addWidget(self._legend_dot("#d08a20", "FEC(パリティ)"))
        legend_row.addStretch(1)
        info_layout.addLayout(legend_row)
        info_layout.addStretch(1)

        note = MemoNote(
            "変調方式(Modulation画面)と組み合わせてMod-Codを構成します。"
            "対応組み合わせ以外を選ぶと送受信開始時にエラーになります。"
        )
        note.setStyleSheet("color: #999999; font-size: 14px; padding: 4px;")
        info_layout.addWidget(note)
        columns.addWidget(info_card, 1)

        # --- 右カラム: フレーム構成(DATA/FEC/PARITY) ---
        frame_card = QtWidgets.QFrame()
        frame_card.setFixedWidth(140)
        frame_card.setStyleSheet(
            "QFrame { background-color: #191d1f; border-radius: 12px; }"
            "QLabel { color: white; background: transparent; }")
        frame_layout = QtWidgets.QVBoxLayout(frame_card)
        frame_layout.setContentsMargins(12, 10, 12, 10)
        frame_layout.setSpacing(8)
        frame_title = QtWidgets.QLabel("フレーム構成")
        frame_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        frame_layout.addWidget(frame_title)
        frame_layout.addWidget(self._frame_badge("DATA", active=False))
        self._fec_badge = self._frame_badge("FEC", active=True)
        frame_layout.addWidget(self._fec_badge)
        frame_layout.addWidget(self._frame_badge("PARITY", active=False))
        frame_layout.addStretch(1)
        columns.addWidget(frame_card)

        self._update_info(main_window.settings.fec_rate)

    @staticmethod
    def _legend_dot(color: str, text: str) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        dot = QtWidgets.QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        layout.addWidget(dot)
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("color: #cccccc; font-size: 12px;")
        layout.addWidget(label)
        return widget

    @staticmethod
    def _frame_badge(text: str, *, active: bool) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setFixedHeight(36)
        color = "#1677ff" if active else "#303538"
        label.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 8px;"
            " font-size: 12px; font-weight: bold;")
        return label

    def _select(self, rate: str) -> None:
        self.main_window.settings.fec_rate = rate
        self.main_window.save_settings()
        self._update_info(rate)

    def _update_info(self, rate: str) -> None:
        overhead = _overhead_percent(rate)
        self.current_label.setText(f"現在の設定: {rate}")
        self.description_label.setText(_describe(rate))
        self.overhead_label.setText(f"オーバーヘッド: {overhead:.0f}%")
        fec_stretch = max(1, round(overhead))
        data_stretch = max(1, round(100 - overhead))
        bar_layout = self.overhead_bar.layout()
        bar_layout.setStretch(0, data_stretch)
        bar_layout.setStretch(1, fec_stretch)


def create(main_window) -> QtWidgets.QWidget:
    return FecScreen(main_window)
