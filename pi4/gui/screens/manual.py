"""目次ジャンプと全文検索を備えた操作説明Help画面。"""
from __future__ import annotations

from PyQt5 import QtWidgets

from i18n import is_english
from manual_content import MANUAL_SECTIONS, MANUAL_SECTIONS_EN
from widgets import SettingsSubScreen


class ManualScreen(SettingsSubScreen):
    def __init__(self, main_window):
        super().__init__("操作説明 / Help", lambda: main_window.navigate_to("home"))
        sections = MANUAL_SECTIONS_EN if is_english(main_window.settings) else MANUAL_SECTIONS

        self.body_layout.addWidget(QtWidgets.QLabel("目次 / Table of Contents"))
        self.toc_combo = QtWidgets.QComboBox()
        self.toc_combo.setMinimumHeight(48)
        self.toc_combo.addItem("章を選択してください")
        for title, _items in sections:
            self.toc_combo.addItem(title)
        self.toc_combo.currentIndexChanged.connect(self._jump_to_section)
        self.body_layout.addWidget(self.toc_combo)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("操作・設定・エラーを検索...")
        self.search_edit.setMinimumHeight(48)
        self.search_edit.textChanged.connect(self._on_search)
        self.body_layout.addWidget(self.search_edit)

        self._section_widgets = []
        for title, items in sections:
            box = QtWidgets.QGroupBox(title)
            layout = QtWidgets.QVBoxLayout(box)
            searchable = [title]
            for subtitle, text in items:
                heading = QtWidgets.QLabel(subtitle)
                heading.setStyleSheet("font-weight: bold; color: #8fb3ff;")
                detail = QtWidgets.QLabel(text)
                detail.setWordWrap(True)
                detail.setTextInteractionFlags(detail.textInteractionFlags())
                layout.addWidget(heading)
                layout.addWidget(detail)
                searchable.extend((subtitle, text))
            self.body_layout.addWidget(box)
            self._section_widgets.append((" ".join(searchable).lower(), box))

    def _jump_to_section(self, index: int) -> None:
        if index <= 0:
            return
        widget = self._section_widgets[index - 1][1]
        widget.setVisible(True)
        self.scroll_area.ensureWidgetVisible(widget, 0, 8)

    def _on_search(self, text: str) -> None:
        needle = text.strip().lower()
        for haystack, widget in self._section_widgets:
            widget.setVisible(not needle or needle in haystack)


def create(main_window) -> QtWidgets.QWidget:
    return ManualScreen(main_window)
