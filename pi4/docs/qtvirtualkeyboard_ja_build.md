# Qt Virtual Keyboard 日本語(OpenWnn)対応ビルド手順

Raspberry Pi OS(Debian trixie)の`apt`版`qtvirtualkeyboard-plugin`には
日本語入力エンジンが同梱されていない(確認できたエンジンはHangul/Hunspell/Thaiのみ)。
`pi4/gui/main.py`のオンスクリーンキーボード(コールサイン・備考欄などのテキスト入力用)
で日本語入力を使うには、Qt公式ソースをOpenWnnエンジン有効でビルドし、
apt版のファイルを差し替える必要がある。

## 前提

- Pi4実機のQtバージョンと完全一致するタグでビルドすること(ズレるとABI不整合でクラッシュする)。
  ```
  qmake -query QT_VERSION   # 例: 5.15.15
  ```

## 手順

```sh
# 1. Qt5開発パッケージ(ビルドに必要。svgのdev版が抜けやすいので注意)
sudo apt-get install -y \
  qtbase5-dev qtbase5-private-dev qtdeclarative5-dev qtdeclarative5-private-dev \
  qtquickcontrols2-5-dev qt5-qmake build-essential libqt5svg5-dev \
  qml-module-qt-labs-folderlistmodel qml-module-qtquick-window2 \
  qml-module-qtquick-layouts qml-module-qtquick-controls2 qml-module-qtquick2

# 2. ソース取得(インストール済みQtバージョンと同じタグ)
git clone --depth 1 --branch v5.15.15-lts-lgpl \
  https://github.com/qt/qtvirtualkeyboard.git qtvirtualkeyboard-src
cd qtvirtualkeyboard-src

# 3. ビルド設定。CONFIG+=openwnnが日本語エンジンを有効化する
#    (src/config.priの`contains(CONFIG, lang-ja.*)|lang-all: CONFIG += openwnn`)。
#    requires(qtHaveModule(svg))を満たさないと全体が無言でSkippedになるので注意。
qmake CONFIG+=openwnn CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US \
  qtvirtualkeyboard.pro

# 4. ビルド(examplesも一緒にビルドされるが本体には不要、examples関連の
#    ビルドだけ後でCtrl-Cしても問題ない)
make -j$(nproc)

# 5. apt版ファイルをバックアップしてから差し替え
BK=~/qtvk_backup_$(date +%Y%m%d%H%M%S)
mkdir -p $BK
sudo cp -a /usr/lib/aarch64-linux-gnu/libQt5VirtualKeyboard.so* $BK/
sudo cp -a /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard $BK/VirtualKeyboard_qml
sudo cp -a /usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so $BK/
mkdir -p $BK/virtualkeyboard_plugins
sudo cp -a /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard/. $BK/virtualkeyboard_plugins/

SRC=$(pwd)
sudo cp -a $SRC/lib/libQt5VirtualKeyboard.so.5.15.15 /usr/lib/aarch64-linux-gnu/
sudo cp -a $SRC/qml/QtQuick/VirtualKeyboard/libqtquickvirtualkeyboardplugin.so \
  /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/
sudo cp -a $SRC/qml/QtQuick/VirtualKeyboard/plugins.qmltypes \
  /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/
sudo cp -a $SRC/qml/QtQuick/VirtualKeyboard/Settings/libqtquickvirtualkeyboardsettingsplugin.so \
  /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/Settings/
sudo cp -a $SRC/qml/QtQuick/VirtualKeyboard/Styles/libqtquickvirtualkeyboardstylesplugin.so \
  /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/Styles/
sudo cp -a $SRC/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so \
  /usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/
sudo mkdir -p /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard
sudo cp -a $SRC/plugins/virtualkeyboard/libqtvirtualkeyboard_openwnn.so \
  /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard/
sudo ldconfig

sudo systemctl restart shonan-gui.service
```

## 復元(切り戻し)

```sh
sudo cp -a $BK/libQt5VirtualKeyboard.so* /usr/lib/aarch64-linux-gnu/
sudo cp -a $BK/VirtualKeyboard_qml/. /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/
sudo cp -a $BK/libqtvirtualkeyboardplugin.so /usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/
sudo cp -a $BK/virtualkeyboard_plugins/. /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard/
sudo ldconfig
sudo systemctl restart shonan-gui.service
```
または `sudo apt-get install --reinstall qtvirtualkeyboard-plugin qml-module-qtquick-virtualkeyboard libqt5virtualkeyboard5` でも同等。

## ハマりどころ

- **eglfsは複数トップレベルウィンドウを扱えない**: `QT_IM_MODULE=qtvirtualkeyboard`だけを
  設定してGUI本体を起動すると、キーボードが独立したQML/Quickウィンドウとして表示されようと
  し、`EGLFS: OpenGL windows cannot be mixed with others`でクラッシュする。
  `pi4/gui/main.py`では`QQuickWidget`+`InputPanel.qml`を`QMainWindow`に埋め込む方式で回避した
  (`MainWindow._build_keyboard_panel()`参照)。
- **`requires(qtHaveModule(svg))`**: `libqt5svg5-dev`が無いとqmakeが警告なしに
  ビルド全体をスキップする(`Some of the required modules (qtHaveModule(svg)) are not
  available. Skipped.`とだけ出て`make`が即0で終わる)。
- **日本語は既定の選択言語にならない**: `layoutsModel`(`en_GB,en_US,fallback,ja_JP,ko_KR,th_TH`)
  には正しく含まれるが、`Keyboard.qml`の`updateDefaultLocale()`の優先順位により起動直後は
  英語が選ばれる。キーボード左下のglobeアイコンをタップすれば日本語配列に切り替わる
  (`VirtualKeyboardSettings.activeLocales`/`.locale`をコード側で明示指定しても、
  タイミングの都合で既定選択には反映されなかった)。
- **`strings`でリソースが見えない**: Qtのコンパイル済みリソース内のパス名はUTF-16LEで
  格納されるため、`strings`で確認するときは`strings -e l`を使う(通常の`strings`では
  何も出ずヒットしない)。
- **言語切替ポップアップと単語予測ポップアップは別スタイルプロパティ**: globeアイコンで
  開く言語一覧は`style.qml`の`languageListDelegate`/`languageListBackground`
  (`Keyboard.qml`の`languagePopupList`が使用)が担当する。似た名前の
  `popupListDelegate`/`popupListBackground`は単語補完等の別ポップアップ用で、
  こちらを変更しても言語一覧の見た目は変わらない(実機で誤って前者を変更し、
  反映されず気づいた)。配色変更は`src/virtualkeyboard/content/styles/default/style.qml`の
  該当箇所(`languageListDelegate`のTextの`color`、`languageListBackground`の
  `Rectangle`の`color`、`states: State { name: "current" ... }`の選択中の色)を編集し、
  `cd src/virtualkeyboard && make`でコアライブラリだけ再ビルドすれば十分
  (openwnnプラグイン等は再ビルド不要)。
