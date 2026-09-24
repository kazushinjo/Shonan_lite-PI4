import QtQuick 2.0
import QtQuick.VirtualKeyboard 2.0
import QtQuick.VirtualKeyboard.Settings 2.0

// 言語切替ポップアップに出す言語をアプリで使う3つ(英/日)に絞り込むための
// InputPanel.qmlラッパー。ビルドにはHangul/Thaiフォールバックレイアウトも
// 含まれており、素のInputPanel.qmlのままだと言語一覧に不要な項目が出てしまう
// (docs/qtvirtualkeyboard_ja_build.md参照)。
InputPanel {
    id: inputPanel

    Component.onCompleted: {
        VirtualKeyboardSettings.activeLocales = ["en_GB", "en_US", "ja_JP"]
    }
}
