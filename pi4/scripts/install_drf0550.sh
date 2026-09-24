#!/usr/bin/env bash
# 新規Pi4(Raspberry Pi OS 64-bit / Debian trixie系)にshonan-pi4一式をセットアップする。
# 単体で(curlで直接)実行しても、既にcloneした状態のrepo内から実行しても動くように、
# 未clone時はGitHubからcloneし、既にcloneされていればgit pullで最新化する。
#
# 実行内容:
#   1. GitHubからソース一式を取得(clone/pull)
#   2. 実行時依存パッケージ(PyQt5、ffmpeg、ALSA/V4L2ツール、日本語/DejaVuフォント等)
#   3. 日本語入力(OpenWnn)対応版Qt Virtual Keyboardをソースからビルド・差し替え
#      (apt版には日本語入力エンジンが同梱されていないため。docs/qtvirtualkeyboard_ja_build.md参照)
#   4. 受信(RX)に必要なGNU Radio + gr-dvbs2rxを導入(gr-dvbs2rxはapt未配布のためソースビルド)
#   5. Langstone V2Modify(SDRトランシーバー、kazushinjo/Langstone-V2Modify)を
#      Pi 4/DFR0550向けインストーラでビルドする
#   6. 起動時コンソール表示の抑制(tty1のgetty無効化、カーネルquiet起動)
#   7. reboot/shutdownのパスワード無し実行を許可(sudoers.d、TTY無しのsystemd
#      サービスからのsudo reboot/shutdownがPAM認証で失敗する不具合の対策)
#   8. 電源電圧警告(稲妻アイコン)表示の抑制(/boot/firmware/config.txtにavoid_warnings=1追記)
#   9. shonan-gui.service / langstone.service(systemd)を作成・有効化
#      (Home画面の「Langstone V2Modify」ボタンでの切替はreboot方式。両サービスとも
#      マーカーファイル~/.pi4_boot_mode_langstoneの有無をConditionPathExistsで見て
#      片方だけが起動する)
#
# 使い方:
#   ./pi4/scripts/install.sh            # 通常インストール(HTTPSでclone)
#   ./pi4/scripts/install_ssh.sh        # SSHでclone(SSH鍵をGitHubに登録済みの場合)
#   SKIP_JA_KEYBOARD=1 ./pi4/scripts/install.sh     # 日本語入力ビルドを省略(時間短縮)
#   SKIP_GNURADIO_BUILD=1 ./pi4/scripts/install.sh  # RX用GNU Radio/gr-dvbs2rxビルドを省略
#   SKIP_LANGSTONE_BUILD=1 ./pi4/scripts/install.sh # Langstone V2Modifyビルドを省略
#
# 前提条件(詳細はdocs/install_script_guide.md「実行条件(前提条件)」参照):
#   - Raspberry Pi OS 64bit(aarch64)。32bit(armhf)では動作しない
#   - gitが事前にインストール済み(1/9のソース取得自体がgitに依存するため)
#   - GitHub / apt配布ミラーへのインターネット到達性
#   - sudoが使える対話的な実行(パスワード入力に応答できるtty)
#   - patchコマンドが使えること(3/9のダークテーマパッチ、4/9の受信安定化パッチ適用に使用)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/kazushinjo/Shonan_lite-PI4.git}"
SCRIPT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INSTALL_DIR="${SHONAN_INSTALL_DIR:-$SCRIPT_ROOT}"
QTVK_BUILD_DIR="${QTVK_BUILD_DIR:-/tmp/qtvirtualkeyboard-src}"
GR_DVBS2RX_BUILD_DIR="${GR_DVBS2RX_BUILD_DIR:-$HOME/gr-dvbs2rx}"
SERVICE_NAME="shonan-gui.service"

log() { echo -e "\n=== $* ===\n"; }

log "1/9 ソース取得 (${REPO_URL})"
if [ -f "$INSTALL_DIR/pi4/gui/main.py" ]; then
  echo "ローカル転送済みソースを使用します: $INSTALL_DIR"
elif [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
GUI_DIR="$INSTALL_DIR/pi4/gui"

log "2/9 実行時依存パッケージ"
sudo apt-get update
sudo apt-get install -y \
  git curl \
  python3-pyqt5 python3-pyqt5.qtquick python3-pyqt5.sip python3-pil \
  ffmpeg v4l-utils alsa-utils sshpass \
  fonts-droid-fallback fonts-dejavu-core \
  qtvirtualkeyboard-plugin qml-module-qtquick-virtualkeyboard \
  qml-module-qt-labs-folderlistmodel qml-module-qtquick-window2 \
  qml-module-qtquick-layouts qml-module-qtquick-controls2 qml-module-qtquick2

if [ "${SKIP_JA_KEYBOARD:-0}" = "1" ]; then
  echo "SKIP_JA_KEYBOARD=1のため日本語入力ビルドを省略します(英語配列のみ利用可)。"
else
  log "3/9 日本語入力(OpenWnn)対応版Qt Virtual Keyboardをビルド"
  sudo apt-get install -y \
    qtbase5-dev qtbase5-private-dev qtdeclarative5-dev qtdeclarative5-private-dev \
    qtquickcontrols2-5-dev qt5-qmake build-essential libqt5svg5-dev

  QT_VERSION="$(qmake -query QT_VERSION)"
  QT_TAG="v${QT_VERSION}-lts-lgpl"
  echo "Qtバージョン: ${QT_VERSION} (タグ ${QT_TAG} を使用)"

  rm -rf "$QTVK_BUILD_DIR"
  git clone --depth 1 --branch "$QT_TAG" \
    https://github.com/qt/qtvirtualkeyboard.git "$QTVK_BUILD_DIR"

  # ★言語切替ポップアップ(globeアイコン)の既定配色(白背景+緑文字)はこのアプリの
  # 全体ダークテーマと合わないため、ダーク背景+白文字に変更するパッチを当てる
  # (qtvirtualkeyboard_ja_build.mdの「言語切替ポップアップと単語予測ポップアップは
  # 別スタイルプロパティ」参照)。
  STYLE_PATCH="$INSTALL_DIR/pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch"
  if [ -f "$STYLE_PATCH" ]; then
    patch -p1 -d "$QTVK_BUILD_DIR" < "$STYLE_PATCH"
  fi

  (
    cd "$QTVK_BUILD_DIR"
    qmake CONFIG+=openwnn CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US \
      qtvirtualkeyboard.pro
    make -j"$(nproc)"
  )

  # apt版ファイルをバックアップしてから自前ビルドで差し替える。
  QT5_LIB_DIR="/usr/lib/aarch64-linux-gnu"
  QT5_QML_DIR="$QT5_LIB_DIR/qt5/qml/QtQuick/VirtualKeyboard"
  QT5_PLUGIN_DIR="$QT5_LIB_DIR/qt5/plugins"
  BACKUP_DIR="$HOME/qtvk_backup_$(date +%Y%m%d%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  sudo cp -a "$QT5_LIB_DIR"/libQt5VirtualKeyboard.so* "$BACKUP_DIR/" 2>/dev/null || true
  sudo cp -a "$QT5_QML_DIR" "$BACKUP_DIR/VirtualKeyboard_qml" 2>/dev/null || true
  sudo cp -a "$QT5_PLUGIN_DIR/platforminputcontexts/libqtvirtualkeyboardplugin.so" \
    "$BACKUP_DIR/" 2>/dev/null || true
  mkdir -p "$BACKUP_DIR/virtualkeyboard_plugins"
  sudo cp -a "$QT5_PLUGIN_DIR/virtualkeyboard/." \
    "$BACKUP_DIR/virtualkeyboard_plugins/" 2>/dev/null || true
  echo "旧ファイルのバックアップ先: $BACKUP_DIR"

  sudo cp -a "$QTVK_BUILD_DIR/lib/libQt5VirtualKeyboard.so.${QT_VERSION}" "$QT5_LIB_DIR/"
  sudo cp -a "$QTVK_BUILD_DIR/qml/QtQuick/VirtualKeyboard/libqtquickvirtualkeyboardplugin.so" \
    "$QT5_QML_DIR/"
  sudo cp -a "$QTVK_BUILD_DIR/qml/QtQuick/VirtualKeyboard/plugins.qmltypes" "$QT5_QML_DIR/"
  sudo cp -a "$QTVK_BUILD_DIR/qml/QtQuick/VirtualKeyboard/Settings/libqtquickvirtualkeyboardsettingsplugin.so" \
    "$QT5_QML_DIR/Settings/"
  sudo cp -a "$QTVK_BUILD_DIR/qml/QtQuick/VirtualKeyboard/Styles/libqtquickvirtualkeyboardstylesplugin.so" \
    "$QT5_QML_DIR/Styles/"
  sudo cp -a "$QTVK_BUILD_DIR/plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so" \
    "$QT5_PLUGIN_DIR/platforminputcontexts/"
  sudo mkdir -p "$QT5_PLUGIN_DIR/virtualkeyboard"
  sudo cp -a "$QTVK_BUILD_DIR/plugins/virtualkeyboard/libqtvirtualkeyboard_openwnn.so" \
    "$QT5_PLUGIN_DIR/virtualkeyboard/"
  sudo ldconfig
fi

if [ "${SKIP_GNURADIO_BUILD:-0}" = "1" ]; then
  echo "SKIP_GNURADIO_BUILD=1のため受信(RX)用GNU Radio/gr-dvbs2rxのビルドを省略します(受信機能は動作しません)。"
else
  log "4/9 受信(RX)用GNU Radio + gr-dvbs2rxを導入"
  # ★gnuradio本体(gr-iio機能も含む。Debianではlibgnuradio-iio*として同梱)はaptで入るが、
  # gr-dvbs2rx(DVB-S2復調のOOT module、igorauad/gr-dvbs2rx)はapt未配布のため、
  # ソースを取得しビルド・インストールする(pi4/rx/shonan_rx.pyが`from gnuradio import
  # dvbs2rx`で必要とする)。
  sudo apt-get install -y gnuradio gnuradio-dev cmake pkg-config

  if [ -d "$GR_DVBS2RX_BUILD_DIR/.git" ]; then
    git -C "$GR_DVBS2RX_BUILD_DIR" pull --ff-only
  else
    git clone https://github.com/igorauad/gr-dvbs2rx.git "$GR_DVBS2RX_BUILD_DIR"
  fi
  git -C "$GR_DVBS2RX_BUILD_DIR" submodule update --init --recursive

  # ★実機での受信安定化のためにpl_frame_sync/symbol_sync_cc等へ加えた修正パッチ。
  # 既に適用済み(2回目以降の実行等)の場合はgit apply --checkが失敗するのでスキップする。
  RX_PATCH="$INSTALL_DIR/pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch"
  if [ -f "$RX_PATCH" ]; then
    if git -C "$GR_DVBS2RX_BUILD_DIR" apply --check "$RX_PATCH" 2>/dev/null; then
      git -C "$GR_DVBS2RX_BUILD_DIR" apply "$RX_PATCH"
    else
      echo "gr-dvbs2rx_pi4_bringup.patchは適用済みか対象外のためスキップします。"
    fi
  fi

  (
    mkdir -p "$GR_DVBS2RX_BUILD_DIR/build"
    cd "$GR_DVBS2RX_BUILD_DIR/build"
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j"$(nproc)"
    sudo make install
  )
  sudo ldconfig
fi

if [ "${SKIP_LANGSTONE_BUILD:-0}" = "1" ]; then
  echo "SKIP_LANGSTONE_BUILD=1のためLangstone V2Modifyのビルドを省略します(Home画面のLangstone V2Modifyボタンは動作しません)。"
else
  log "5/9 Langstone V2Modify(SDRトランシーバー)のビルド"
  # Pi 4/DFRobot DFR0550/ADALM-Pluto向けの依存関係とビルド手順は、
  # kazushinjo/Langstone-V2Modify側の保守済みインストーラを使用する。
  LANGSTONE_DIR="${LANGSTONE_INSTALL_DIR:-$HOME/Langstone}"
  mkdir -p "$LANGSTONE_DIR"
  cp -a "$INSTALL_DIR"/pi4/third_party/Langstone-V2Modify/. "$LANGSTONE_DIR/"
  chmod +x "$LANGSTONE_DIR"/install_dfr0550.sh
  SHONAN_INTEGRATION=1 "$LANGSTONE_DIR"/install_dfr0550.sh
  echo "Langstone V2Modifyをビルドしました: ${LANGSTONE_DIR}/GUI_Pluto"
fi

log "6/9 起動時コンソール表示の抑制"
# ★Home画面の「Langstone V2Modify」ボタン/Langstone側の「戻る」ボタンによる切替は
# 毎回Pi4をrebootする方式のため、素のRaspberry Pi OSのまま(getty@tty1が
# 有効)だと切替のたびにカーネル起動ログやログインプロンプト/シェルの
# コンソール出力が実機LCDに一瞬映り込み、Langstone/Shonan_Lite本来の画面と
# 無関係な文字が見えてしまう(実機で確認)。tty1のgettyを無効化し、
# カーネルの起動メッセージも抑制する。
sudo systemctl disable --now getty@tty1.service 2>/dev/null || true
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ -f "$CMDLINE_FILE" ] && ! grep -q 'quiet' "$CMDLINE_FILE"; then
  sudo sed -i '1s/$/ quiet loglevel=3 logo.nologo vt.global_cursor_default=0/' "$CMDLINE_FILE"
  echo "${CMDLINE_FILE}へquiet起動オプションを追記しました(反映には再起動が必要です)。"
else
  echo "${CMDLINE_FILE}は見つからないか、既にquiet設定済みのためスキップします。"
fi

log "7/9 reboot/shutdownのパスワード無し実行を許可"
# ★Home画面の「Langstone V2Modify」ボタン(shonan-gui.service)、Langstone側の
# 「戻る」ボタン(langstone.service)はいずれもTTYの無いsystemdサービスから
# sudo reboot/sudo shutdownを実行する。標準のsudo設定はパスワード入力を
# 要求するため、PAM会話が成立せず(pam_unix: conversation failed)rebootが
# 実行されないまま処理が先へ進んでしまう不具合を実機で確認した。pi
# ユーザーがreboot/shutdownをNOPASSWDで実行できるよう許可する。
SUDOERS_FILE="/etc/sudoers.d/shonan-pi4-reboot"
echo "$(whoami) ALL=(root) NOPASSWD: /sbin/reboot, /sbin/shutdown, /bin/systemctl start --no-block shonan-gui.service, /bin/systemctl start --no-block langstone.service, /bin/systemctl stop shonan-display-off.service" | sudo tee "$SUDOERS_FILE" > /dev/null
sudo chmod 440 "$SUDOERS_FILE"
sudo visudo -c
echo "${SUDOERS_FILE}を更新しました。"

log "8/9 電源電圧警告(稲妻アイコン)表示の抑制"
# ★正規の27W USB-C PD電源でも配線・ケーブル品質等でわずかな電圧降下により
# 稲妻アイコン/ログ警告が出ることがある。avoid_warnings=1は表示を抑制するのみで
# 実際のアンダーボルト自体は解消しないため、恒久対策としては正規電源・良質な
# USBケーブルの使用が前提(vcgencmd get_throttledで実際のスロットリング有無を確認可能)。
BOOT_CONFIG="/boot/firmware/config.txt"
if [ -f "$BOOT_CONFIG" ] && ! grep -q '^avoid_warnings=' "$BOOT_CONFIG"; then
  echo "avoid_warnings=1" | sudo tee -a "$BOOT_CONFIG" > /dev/null
  echo "${BOOT_CONFIG}にavoid_warnings=1を追記しました(反映には再起動が必要です)。"
else
  echo "${BOOT_CONFIG}は見つからないか、既にavoid_warnings設定済みのためスキップします。"
fi

log "9/9 systemdサービス登録"
# ★Langstone V2Modifyとshonan-gui.serviceは同じ画面(/dev/fb0とeglfs/DRM)を排他的に
# 使うため同時起動できない。Home画面の「Langstone V2Modify」ボタン、およびLangstone側の
# 「戻る」ボタンは、マーカーファイル(~/.pi4_boot_mode_langstone)を作成/削除して
# rebootする(pi4/gui/screens/home.py、LangstoneGUI_Pluto.c参照)。両サービスとも
# ConditionPathExistsでマーカーの有無を見て、起動すべきでない側は何もせず正常終了
# (skipped)扱いになるようにする。
LANGSTONE_BOOT_MARKER="${HOME}/.pi4_boot_mode_langstone"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Shonan Pi4 Touch GUI
After=multi-user.target
ConditionPathExists=!${LANGSTONE_BOOT_MARKER}

[Service]
Type=simple
User=${USER}
WorkingDirectory=${GUI_DIR}
Environment=QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0:nocursor
ExecStartPre=+/bin/sh -c 'if [ -e /sys/class/graphics/fb0/blank ]; then echo 0 > /sys/class/graphics/fb0/blank; fi'
ExecStart=/usr/bin/python3 ${GUI_DIR}/main.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

BOOT_MENU_SERVICE_FILE="/etc/systemd/system/shonan-boot-menu.service"
sudo tee "$BOOT_MENU_SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Shonan/Langstone Boot Menu
After=multi-user.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${GUI_DIR}
Environment=QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0:nocursor
ExecStartPre=+/bin/sh -c 'if [ -e /sys/class/graphics/fb0/blank ]; then echo 0 > /sys/class/graphics/fb0/blank; fi'
ExecStart=/usr/bin/python3 ${GUI_DIR}/boot_menu.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# DSI液晶はOS停止後も最後のフレームを保持するため、shutdown時に画面と
# バックライトを明示的に消灯する。
DISPLAY_OFF_SERVICE_FILE="/etc/systemd/system/shonan-display-off.service"
sudo tee "$DISPLAY_OFF_SERVICE_FILE" > /dev/null <<'EOF'
[Unit]
Description=Blank Shonan DSI display during shutdown
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for p in /sys/class/backlight/*/bl_power; do if [ -e "$p" ]; then echo 0 > "$p"; fi; done; for b in /sys/class/backlight/*/brightness; do if [ -e "$b" ]; then echo 255 > "$b"; fi; done; if [ -e /sys/class/graphics/fb0/blank ]; then echo 0 > /sys/class/graphics/fb0/blank; fi'
ExecStop=/bin/sh -c 'if [ -e /sys/class/graphics/fb0/blank ]; then echo 4 > /sys/class/graphics/fb0/blank; fi; for p in /sys/class/backlight/*/bl_power; do if [ -e "$p" ]; then echo 4 > "$p"; fi; done'
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

if [ "${SKIP_LANGSTONE_BUILD:-0}" != "1" ]; then
  LANGSTONE_SERVICE_FILE="/etc/systemd/system/langstone.service"
  sudo tee "$LANGSTONE_SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Langstone V2Modify SDR Transceiver
After=multi-user.target
ConditionPathExists=${LANGSTONE_BOOT_MARKER}

[Service]
Type=simple
User=${USER}
WorkingDirectory=${LANGSTONE_DIR:-$HOME/Langstone}
ExecStart=/bin/bash ${LANGSTONE_DIR:-$HOME/Langstone}/run_pluto
Restart=no
# ★run_pluto先頭行が(元々のupstreamソースのまま)"#"のみのコメント行で、
# 続く2行目が"#!/bin/bash"になっている。カーネルのシェバング認識は先頭行のみを
# 見るため、systemdが直接execすると"Exec format error"になる(実機で確認)。
# /bin/bash経由で明示的に起動することで回避する。

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl disable langstone.service 2>/dev/null || true
fi

sudo systemctl daemon-reload
sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
sudo systemctl enable shonan-boot-menu.service
sudo systemctl enable shonan-display-off.service
sudo systemctl restart shonan-boot-menu.service

log "完了"
sudo systemctl status shonan-boot-menu.service --no-pager || true
cat <<'NOTE'

注意:
- 「Pluto再起動」ボタン、「システム日時」設定、実機LCDスクリーンショット取得等の機能は
  sshおよびsudoをパスワードなしで実行できる権限が前提です。必要に応じて
  /etc/sudoers.d/ にNOPASSWDルールを追加してください(このスクリプトでは変更しません)。
- 日本語入力は既定では英語配列で開始します。オンスクリーンキーボード左下のglobeアイコンで
  日本語(ローマ字入力)へ切り替えられます。
- /boot/firmware/config.txtへavoid_warnings=1を新規追記した場合、反映には再起動が必要です
  (sudo reboot)。稲妻アイコン表示は抑制されますが、実際の電圧不足自体は解消されないため、
  正規の27W USB-C PD電源・良質なUSBケーブルの使用を推奨します
  (vcgencmd get_throttledで実際のスロットリング有無を確認できます)。
NOTE
