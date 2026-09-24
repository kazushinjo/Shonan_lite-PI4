# pi4/scripts/install.sh 詳細ガイド

`install.sh`は、まっさらなRaspberry Pi OS(Debian trixie系)にshonan-pi4一式を
セットアップするための単一スクリプトである。本ドキュメントは各処理の内容と、
なぜその手順が必要かを詳しく説明する。手順そのものの一次情報は
`docs/qtvirtualkeyboard_ja_build.md`(Qt Virtual Keyboardのビルド部分)も参照。

## 想定環境

- Raspberry Pi 4 + Raspberry Pi OS(Debian trixie相当、apt/systemd/eglfs前提)
- ADALM-Pluto+(DATVファームウェア)がEthernet同一ネットワークに接続済み
- `pi`ユーザーなど、`sudo`が使えるユーザーで実行する(スクリプト自体は`sudo`を
  個別コマンドの前に付けて実行するので、スクリプト自体をrootで起動する必要はない)

## 実行条件(前提条件)

一般ユーザーが実行して`install.sh`が正常完了するには、以下がすべて揃っている必要がある。

**必須**

1. **Raspberry Pi OS 64bit(aarch64)であること** — スクリプト内でQtライブラリの
   差し替え先を`/usr/lib/aarch64-linux-gnu/`に決め打ちしているため、32bit
   (armhf)版OSでは動作しない。
2. **`git`が事前にインストール済み** — 1/6のソース取得(`git clone`/`git pull`)
   自体が`git`コマンドに依存しており、これは2/6のapt導入対象に含まれていない
   (導入前に使うため)。無ければ先に`sudo apt-get install -y git`が必要。
3. **インターネット到達性** — GitHub(ソース取得・Qt Virtual Keyboardのclone)と
   Debianのapt配布ミラー両方に到達できること。
4. **sudoが使える対話的な実行** — apt/tee/systemctl等で何度も`sudo`を呼ぶため、
   パスワード入力を求められた際に応答できるttyでの実行が前提(SSH経由でも
   対話ttyがあれば問題ない)。完全無人実行にしたい場合は事前に
   `/etc/sudoers.d/`へNOPASSWDルールを用意しておく必要がある
   (スクリプト自体はsudoers設定を変更しない)。
5. **`patch`コマンドが使えること** — ダークテーマパッチ適用に使用する。
   Raspberry Pi OSには通常プリインストールされているが、最小構成イメージでは
   無い場合がある。

**時間・リソース**

6. 日本語入力ビルド(既定、`SKIP_JA_KEYBOARD=1`未指定時)は実測10〜20分程度
   かかるため、途中で通信・電源が切れない環境であること。

**不要な条件**

- 実行時点でPluto+実機がネットワーク上にある必要はない(あくまでソフトウェア
  導入のみ。実運用時に別途必要)。
- USBカメラ・オーディオ機器も導入時点では不要。

## 実行方法

```sh
./pi4/scripts/install.sh          # HTTPSでclone/pull(既定)
./pi4/scripts/install_ssh.sh      # SSHでclone/pull(GitHubにSSH鍵を登録済みの場合)
```

`install_ssh.sh`は`REPO_URL`を`git@github.com:kazushinjo/Shonan_lite-PI4.git`に
設定してから`install.sh`を呼び出すだけの薄いラッパーで、それ以外の処理は
完全に同一である。

環境変数で挙動を変更できる。

| 変数 | 既定値 | 効果 |
| --- | --- | --- |
| `SHONAN_INSTALL_DIR` | `$HOME/shonan-pi4` | リポジトリのclone/pull先ディレクトリ |
| `QTVK_BUILD_DIR` | `/tmp/qtvirtualkeyboard-src` | Qt Virtual Keyboardのビルド作業ディレクトリ |
| `GR_DVBS2RX_BUILD_DIR` | `$HOME/gr-dvbs2rx` | gr-dvbs2rxのビルド作業ディレクトリ |
| `SKIP_JA_KEYBOARD` | `0` | `1`にすると日本語入力ビルド(3/6)を丸ごとスキップする |
| `SKIP_GNURADIO_BUILD` | `0` | `1`にすると受信(RX)用GNU Radio/gr-dvbs2rxビルド(4/6)を丸ごとスキップする(受信機能は動作しなくなる) |

`set -euo pipefail`が先頭にあるため、いずれかのコマンドが失敗した時点でスクリプトは
即座に停止する(中途半端な状態のまま先へ進まない)。

---

## 0/6 Raspberry Pi OSのインストール

`install.sh`実行対象のPi4に、あらかじめRaspberry Pi OSをインストールしておく
必要がある(このインストール自体は`install.sh`の範囲外)。

### 準備するもの

- Raspberry Pi 4本体
- microSDカードまたはNVMe SSD(Pi4の起動ストレージ)
- 書き込み用PC(Windows/Mac/Linuxいずれか)とmicroSDカードリーダー等
- Raspberry Pi Imager(公式書き込みツール、
  https://www.raspberrypi.com/software/ から入手)

### 手順

1. PCでRaspberry Pi Imagerを起動する。
2. 「デバイスを選択」で **Raspberry Pi 4** を選ぶ。
3. 「OSを選択」で **Raspberry Pi OS (64-bit)** を選ぶ(★32bit版は不可。
   「実行条件(前提条件)」参照)。OS名に必ず"64-bit"と表示されているものを
   選ぶこと(一覧に32bit/64bit両方が並ぶ場合があるため)。
4. 「ストレージを選択」で書き込み先のmicroSD/NVMeを選ぶ。
5. 歯車アイコン(詳細設定)を開き、以下を事前設定しておくと、初回起動後すぐ
   SSH接続して`install.sh`を実行できる。
   - ホスト名
   - ユーザー名・パスワード
   - Wi-Fi(有線LANのみで運用する場合は不要)
   - SSHを有効化(公開鍵認証 or パスワード認証)
6. 「書き込む」を実行し、完了を待つ。
7. microSD/NVMeをPi4に取り付け、電源を入れる。初回起動は数分かかる。
8. PCから`ssh <ユーザー名>@<ホスト名>.local`(またはPi4に割り当てられた
   IPアドレス)で接続できることを確認する。

以降の手順(1/6〜6/6)は、この時点でSSH接続できているPi4上で実行する。

## 1/6 ソース取得

```sh
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
```

- `$INSTALL_DIR/.git`が既に存在するか(＝既にcloneされているか)で分岐する。
  - 存在しない場合: GitHub(`kazushinjo/Shonan_lite-PI4`)から新規clone。これにより、
    このスクリプト単体を(まだリポジトリを持っていない)新品のPi4へ`curl`等で
    転送して実行するだけでセットアップを開始できる。
  - 存在する場合: `git pull --ff-only`で最新化する。`--ff-only`はfast-forward
    できない(ローカルに独自コミットがある等の)場合にエラーで止まり、意図せず
    ローカルの変更を上書き・マージしてしまうことを防ぐ安全策。

## 2/6 実行時依存パッケージ

GUI本体(`pi4/gui/main.py`)を動かすために必要な、Debianパッケージ一式を`apt`で
導入する。

| パッケージ | 用途 |
| --- | --- |
| `git`, `curl` | ソース取得・HTTP通信(Pluto+への設定送信等)に使用 |
| `python3-pyqt5` | GUI本体のQtバインディング |
| `python3-pyqt5.qtquick` | `QQuickWidget`(オンスクリーンキーボードの埋め込みに使用) |
| `python3-pyqt5.sip` | PyQt5の内部依存 |
| `python3-pil` | Pillow。カメラ映像へのコールサイン・備考オーバーレイ合成に使用 |
| `ffmpeg` | 映像/音声のエンコード・多重化・オーバーレイ合成・受信映像デコード全般 |
| `v4l-utils` | USBカメラの解像度・フォーマット確認(`v4l2-ctl`) |
| `alsa-utils` | 音声デバイス列挙・音量調整(`aplay`/`arecord`/`amixer`) |
| `sshpass` | Home画面の「Pluto再起動」ボタンがPluto+へパスワード付きSSHするために使用 |
| `fonts-droid-fallback` | オーバーレイの日本語グリフ描画用フォント(DroidSansFallbackFull) |
| `fonts-dejavu-core` | オーバーレイの英数字グリフ描画用フォント(DejaVuSans-Bold) |
| `qtvirtualkeyboard-plugin`, `qml-module-qtquick-virtualkeyboard` | オンスクリーンキーボード本体(apt版。3/6で日本語対応版に差し替える) |
| `qml-module-qt-labs-folderlistmodel`, `qml-module-qtquick-window2`, `qml-module-qtquick-layouts`, `qml-module-qtquick-controls2`, `qml-module-qtquick2` | オンスクリーンキーボードのQML実装が依存する補助モジュール群(不足しているとキーボードパネルのQML読み込みに失敗する) |

★`SKIP_JA_KEYBOARD=1`でも2/6は必ず実行される(英語キーボード自体はここで
入るapt版で動作するため)。

## 3/6 日本語入力(OpenWnn)対応版Qt Virtual Keyboardのビルド

`SKIP_JA_KEYBOARD=1`の場合はこのブロック全体をスキップし、「英語配列のみ利用可」
というメッセージだけ表示して5/6へ進む。

### なぜソースからビルドする必要があるのか

Debian(Raspberry Pi OS)がapt配布している`qtvirtualkeyboard-plugin`には、
日本語入力エンジンが同梱されていない(実機で確認できたエンジンはHangul/
Hunspell(欧文系)/Thaiのみ)。Qt Virtual KeyboardはOSS版でもOpenWnn
(Android由来のオープンソースかな漢字変換エンジン、Apacheライセンス)を
ビルドに含めることができるが、Debianのパッケージビルドではこれが有効化
されていない。そのためQt公式ソースを取得し、`CONFIG+=openwnn`を指定して
自前でビルドし、apt版のファイルを差し替える。

### ビルド用開発パッケージの追加導入

```sh
sudo apt-get install -y \
  qtbase5-dev qtbase5-private-dev qtdeclarative5-dev qtdeclarative5-private-dev \
  qtquickcontrols2-5-dev qt5-qmake build-essential libqt5svg5-dev
```

`libqt5svg5-dev`が特に重要。Qt Virtual Keyboardのトップレベル`.pro`ファイルは
`requires(qtHaveModule(svg))`を宣言しており、これが満たされないと**エラーメッセージ
すら出さずに**ビルド全体が空振りする(`qmake`は`Some of the required modules
(qtHaveModule(svg)) are not available. Skipped.`とだけ出力し、続く`make`は
一瞬で正常終了してしまう)。実機で一度ハマった問題なので、パッケージリストから
外さないこと。

### Qtバージョンの一致

```sh
QT_VERSION="$(qmake -query QT_VERSION)"
QT_TAG="v${QT_VERSION}-lts-lgpl"
```

Pi4にインストール済みのQt本体(`libQt5Core`等)とQt Virtual Keyboardのビルドは
**ABIレベルで完全に一致するバージョン**でなければならない。バージョンがずれると
実行時にクラッシュする、または起動すらしない。そのため、決め打ちのタグではなく
`qmake -query QT_VERSION`で実機のQtバージョンを動的に取得し、対応する
`v<バージョン>-lts-lgpl`タグ(Qt公式リポジトリのLTS/LGPLライセンスブランチの
命名規則)でcloneする。

### ダークテーマパッチの適用

```sh
STYLE_PATCH="$INSTALL_DIR/pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch"
if [ -f "$STYLE_PATCH" ]; then
  patch -p1 -d "$QTVK_BUILD_DIR" < "$STYLE_PATCH"
fi
```

Qt Virtual Keyboードのオンスクリーンキーボードで、globeアイコンをタップすると
出る言語切替ポップアップ(既定ではBritish English / American English / 日本語 /
한글 / ไทย等がビルドに含まれるフォールバックレイアウトの数だけ並ぶ。実際に
アプリで表示される一覧は`pi4/gui/qml/InputPanelWrapper.qml`で
English GB/US・日本語の3つに絞り込んでいる。後述「言語一覧の絞り込み」参照)は、
既定では**白背景+緑文字**で、shonan-pi4アプリ全体の黒背景+白文字のダーク
テーマと見た目が合わない。`pi4/docs/patches/
qtvirtualkeyboard_style_dark_language_popup.patch`は、Qt Virtual Keyboardの
`src/virtualkeyboard/content/styles/default/style.qml`内の
`languageListDelegate`(文字色)・`languageListBackground`(背景色)・選択中の
アイテムの強調色を、アプリと同じダーク配色に書き換える差分である。
`patch`コマンドが利用できない/パッチファイルが見当たらない場合は単にスキップし、
既定配色のままビルドを継続する(致命的な問題ではない)。

★このパッチファイルがリポジトリに存在しない状態(=手元でcloneしたばかりの
古いコミット等)でも、`if [ -f ... ]`のガードにより安全にスキップされる。

### ビルド本体

```sh
(
  cd "$QTVK_BUILD_DIR"
  qmake CONFIG+=openwnn CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US \
    qtvirtualkeyboard.pro
  make -j"$(nproc)"
)
```

- `CONFIG+=openwnn`: 日本語かな漢字変換エンジン(OpenWnn)を含める。
  `src/config.pri`の`contains(CONFIG, lang-ja.*)|lang-all: CONFIG += openwnn`
  というルールにより、`lang-ja_JP`を指定すれば暗黙的にも有効化されるが、
  明示しておくことで意図を明確にしている。
- `CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US`: ビルドに含める
  キーボード配列を絞り込む(指定しない場合は既定で全言語=`lang-all`が
  ビルドされ、時間もリソースも余分にかかる)。
- サブシェル`( ... )`で囲んでいるのは、`cd`によるスクリプトのカレント
  ディレクトリ変化を、この処理の外へ漏らさないため。
- `make -j"$(nproc)"`は搭載コア数ぶん並列ビルドする。Pi4(4コア)で
  examplesも含めて概ね10〜20分程度かかる(実機での実測ベース)。

★日本語がキーボードの既定選択言語にはならない(起動直後は英語)点は既知の
挙動で、`docs/qtvirtualkeyboard_ja_build.md`の「ハマりどころ」に詳細がある。
globeアイコンで手動切替が必要。

### 言語一覧の絞り込み

`CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US`を指定しても、
ビルドには韓国語(한글)・タイ語(ไทย)向けのフォールバックレイアウトが
含まれてしまい、globeアイコンの言語切替ポップアップにこの2つが不要に
表示される。これはビルド設定では除外できないため、実行時に
`QtQuick.VirtualKeyboard.Settings`の`VirtualKeyboardSettings.activeLocales`
プロパティで表示対象を絞り込む。

`pi4/gui/main.py`は素の`InputPanel.qml`ではなく`pi4/gui/qml/
InputPanelWrapper.qml`をキーボードパネルとして読み込む。このQMLは
`InputPanel`を継承し、`Component.onCompleted`で
`VirtualKeyboardSettings.activeLocales = ["en_GB", "en_US", "ja_JP"]`を
設定することで、言語切替ポップアップの一覧をEnglish GB/US・日本語の3つに
限定する。

★この絞り込みは`install.sh`側の処理ではなく、リポジトリに含まれる
`pi4/gui/qml/InputPanelWrapper.qml`と`pi4/gui/main.py`のコード側の対応であり、
`install.sh`はリポジトリを`git clone`/`pull`するだけなのでそのまま反映される
(`install.sh`自体の変更は不要)。

### apt版ファイルのバックアップと差し替え

```sh
BACKUP_DIR="$HOME/qtvk_backup_$(date +%Y%m%d%H%M%S)"
...
sudo cp -a "$QT5_LIB_DIR"/libQt5VirtualKeyboard.so* "$BACKUP_DIR/" 2>/dev/null || true
...
```

差し替え前に、2/6でaptインストールされた既存ファイル一式を
`~/qtvk_backup_<タイムスタンプ>/`へコピーしておく。`|| true`が付いているのは、
(通常発生しないはずだが)コピー元ファイルが万一存在しない場合でも
`set -e`によってスクリプト全体が止まらないようにするため。

差し替え対象は次の5系統:

1. `libQt5VirtualKeyboard.so.<バージョン>` — コア共有ライブラリ本体
   (キーボードのレイアウト・スタイルQMLもリソースとしてここにコンパイルされている)
2. `qml/QtQuick/VirtualKeyboard/libqtquickvirtualkeyboardplugin.so`
   および`plugins.qmltypes` — QMLモジュール`QtQuick.VirtualKeyboard`本体
3. `qml/QtQuick/VirtualKeyboard/Settings/libqtquickvirtualkeyboardsettingsplugin.so`
   — `QtQuick.VirtualKeyboard.Settings`(アクティブロケール等の設定用)
4. `qml/QtQuick/VirtualKeyboard/Styles/libqtquickvirtualkeyboardstylesplugin.so`
   — `QtQuick.VirtualKeyboard.Styles`
5. `plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so` —
   `QT_IM_MODULE=qtvirtualkeyboard`で読み込まれるプラットフォーム入力
   コンテキストプラグイン本体
6. `plugins/virtualkeyboard/libqtvirtualkeyboard_openwnn.so` — 今回の主目的である
   日本語入力エンジン本体(apt版には存在しないため`mkdir -p`してから新規配置)

最後に`sudo ldconfig`で共有ライブラリキャッシュを更新し、変更を即座に
反映させる。

### 復元(切り戻し)したい場合

```sh
BK=~/qtvk_backup_<タイムスタンプ>   # 実際のディレクトリ名に置き換える
sudo cp -a $BK/libQt5VirtualKeyboard.so* /usr/lib/aarch64-linux-gnu/
sudo cp -a $BK/VirtualKeyboard_qml/. /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/
sudo cp -a $BK/libqtvirtualkeyboardplugin.so /usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/
sudo cp -a $BK/virtualkeyboard_plugins/. /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard/
sudo ldconfig
sudo systemctl restart shonan-gui.service
```

または単純に`sudo apt-get install --reinstall qtvirtualkeyboard-plugin
qml-module-qtquick-virtualkeyboard libqt5virtualkeyboard5`でもapt版へ戻せる
(この場合は日本語入力ができなくなる)。

## 4/6 受信(RX)用GNU Radio + gr-dvbs2rxの導入

`SKIP_GNURADIO_BUILD=1`の場合はこのブロック全体をスキップする(受信機能は動作しない)。

```sh
sudo apt-get install -y gnuradio gnuradio-dev cmake pkg-config
git clone https://github.com/igorauad/gr-dvbs2rx.git "$GR_DVBS2RX_BUILD_DIR"
git -C "$GR_DVBS2RX_BUILD_DIR" submodule update --init --recursive
git -C "$GR_DVBS2RX_BUILD_DIR" apply "$RX_PATCH"   # 存在し未適用の場合のみ
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)" && sudo make install
```

`pi4/rx/shonan_rx.py`は`from gnuradio import gr, analog, blocks, iio, dvbs2rx`を
実行時に必要とする。`gnuradio`本体(gr-iio機能を含む`libgnuradio-iio*`も同梱)は
Debianのaptで導入できるが、`dvbs2rx`(DVB-S2復調のOOT module、
[igorauad/gr-dvbs2rx](https://github.com/igorauad/gr-dvbs2rx))はapt未配布のため、
ソースを取得しビルド・インストールする。実機での受信安定化のために加えた修正は
`pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch`として適用する(既に適用済みなら
自動でスキップされる)。参考実装として`pi4/third_party/rpi-dvbs2-receiver-gui/`
(kazushinjo/rpi-dvbs2-receiver-guiより取り込み)も参照。

★これがないとRX開始時に`ModuleNotFoundError: No module named 'gnuradio'`または
`ImportError: cannot import name 'dvbs2rx'`で受信が失敗する(実機の新規インストール
で発見・修正)。

## 5/6 電源電圧警告(稲妻アイコン)表示の抑制

```sh
if [ -f "$BOOT_CONFIG" ] && ! grep -q '^avoid_warnings=' "$BOOT_CONFIG"; then
  echo "avoid_warnings=1" | sudo tee -a "$BOOT_CONFIG" > /dev/null
fi
```

`/boot/firmware/config.txt`に`avoid_warnings=1`が無ければ追記する(既にあれば
何もしない、冪等)。反映には`sudo reboot`が必要。これは画面上の稲妻アイコン・
ログ警告の表示を抑制するだけで、実際の電圧不足自体を解消するものではない
(恒久対策は正規の27W USB-C PD電源・良質なUSBケーブルの使用。
`vcgencmd get_throttled`で実際のスロットリング有無を確認できる)。

## 6/6 systemdサービス登録

```sh
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Shonan Pi4 Touch GUI
...
User=${USER}
WorkingDirectory=${GUI_DIR}
Environment=QT_QPA_PLATFORM=eglfs
ExecStart=/usr/bin/python3 ${GUI_DIR}/main.py
Restart=on-failure
RestartSec=3
...
EOF
```

`/etc/systemd/system/shonan-gui.service`をヒアドキュメントで生成する
(`sudo tee`を使うのは、リダイレクト`>`自体は`sudo`の権限を引き継がない
ため。`sudo bash -c "... > file"`と同様の目的)。

- `User=${USER}`: スクリプトを実行したユーザー名をそのまま使う(決め打ちで
  `pi`等にしていない)。
- `Environment=QT_QPA_PLATFORM=eglfs`: X11/Waylandなしで、Pi4のDSI接続LCDへ
  直接描画するQtプラットフォームプラグインを指定する。
- `Restart=on-failure` / `RestartSec=3`: GUIプロセスが異常終了した場合、
  3秒後に自動再起動する。

続けて`daemon-reload`(新規/変更されたユニットファイルをsystemdに認識させる)
→`enable`(次回起動時の自動起動を有効化)→`restart`(今すぐ反映)を実行する。

## 完了後の表示

```sh
sudo systemctl status "$SERVICE_NAME" --no-pager || true
```

でサービスの起動状態を表示する(失敗してもスクリプト自体は正常終了として
扱うよう`|| true`を付けている、ステータス表示はあくまで確認用のため)。

続けて次の2点を注意書きとして表示する。

1. **パスワードなしsudo/sshの前提**: Home画面の「Pluto再起動」ボタン
   (`sshpass`でPluto+へSSH)、設定画面の「システム日時」設定
   (`timedatectl`)、および開発時に使う`kmsgrab`による実機画面キャプチャ等は、
   `sudo`をパスワードなしで実行できることを前提にしている。このスクリプトは
   `/etc/sudoers.d/`への変更は一切行わない(セキュリティに関わる設定を
   スクリプトが無断で行うべきではないため)。必要であれば運用者が判断して
   個別に設定する。
2. **日本語入力の既定言語**: オンスクリーンキーボードは起動直後は英語配列で、
   globeアイコンをタップすることで日本語(ローマ字入力)へ切り替えられる
   (自動では切り替わらない、既知の仕様)。

## 関連ドキュメント

- `pi4/docs/qtvirtualkeyboard_ja_build.md` — 3/6のビルド手順の一次情報、
  実機で遭遇したハマりどころの詳細
- `pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch` —
  3/6で適用されるダークテーマパッチの実体(unified diff形式、`git diff`相当)
- `pi4/docs/shonan_pi4_operation_manual.docx` / `pi4/gui/manual_content.py` —
  GUIの操作方法そのもの(インストール後の使い方)
- `pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch` — 4/6で適用される受信安定化
  パッチの実体
- `pi4/third_party/rpi-dvbs2-receiver-gui/` — GNU Radio/gr-dvbs2rx受信フロー
  グラフの参考実装(kazushinjo/rpi-dvbs2-receiver-guiより取り込み)
