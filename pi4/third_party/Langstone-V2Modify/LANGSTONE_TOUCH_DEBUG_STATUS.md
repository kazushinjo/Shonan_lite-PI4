# Langstone-V2 タッチパネル調査メモ

更新日: 2026-08-16

## 環境

- Raspberry Pi: `192.168.0.146`
- 接続ディスプレイ: DFRobot DFR0550 5インチ、DSI/FPC接続
- OS: Raspberry Pi OS Trixie、arm64
- カーネル: `6.18.39+rpt-rpi-v8`
- 画面: 800x480、DSI表示は現在正常

## 現在の状態

- `GUI_Pluto`と`Lang_TRX_Pluto.py`は起動している
- GUIは`/dev/input/event2`を開いている
- `/sys/class/input/event2/device/name`は`raspberrypi-ts`
- 合成したLinux入力イベントでは、Langstoneのタッチ処理が正常に座標取得・押下判定できた
- 実機タッチを20秒監視したがイベントは0件
- 実機タッチを60秒監視したがイベントは0件
- よって、現時点ではGUIの座標基準や`Touch.h`の押下判定より前に、物理タッチ入力がLinuxへ届いていない可能性が高い

## 設定

Piの現在の主要設定（最後に確認した状態）:

```text
display_auto_detect=1
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dsi-7inch,disable_touch
dtoverlay=rpi-ft5406
```

`rpi-ft5406`により`raspberrypi-ts`デバイスは生成されているが、実イベントは未確認。

## 実施済みの変更

- `install_dfr0550.sh`: DSI/FPCディスプレイ向けに更新、古いBuster依存を削除、再実行可能化
- `Lang_TRX_Pluto.py`: GNU Radio 3.10対応、ウォーターフォールのvector-to-stream経路を修正
- `Graphics.h`: 16-bit RGB565 KMS framebuffer対応
- `run_pluto`: framebufferのblank解除、16-bit画面でのスプラッシュ処理を修正
- `LangstoneGUI_Pluto.c`: タッチデバイス名`raspberrypi-ts`を検出対象に追加、ウォーターフォール色を調整
- 変更はPiへデプロイ済み。ローカル作業ツリーには既存変更を含むため、リセットや上書きは禁止

## 次に行う調査

1. 古いアプリを起動し、古いアプリでタッチが動作するか確認する
2. 古いアプリ動作中に、`/proc/bus/input/devices`、`/dev/input/event*`、`dmesg`、入力イベントを比較する
3. 旧アプリで別のタッチドライバ・デバイス・座標範囲を使っている場合、Langstoneへ反映する
4. 旧アプリでも同じ`raspberrypi-ts`からイベントが出ない場合は、DSIタッチ用オーバーレイまたはFPC接続・電源を再確認する

## 旧バージョン接続時の追加確認

- 旧バージョンへ切替後もIPは`192.168.0.146`、パスワードは`raspberry`
- 旧アプリは`GUI_Pluto`/`Lang_TRX_Pluto.py`として起動
- タッチデバイスは同じ`raspberrypi-ts`、`/dev/input/event2`
- 旧環境のframebufferは`BCM2708 FB`（800x480）
- 旧環境の`/boot/config.txt`にはKMS/DSI overlay設定がなく、`vc4-fkms-v3d`もコメントアウト
- 旧環境のdmesgでは`input: raspberrypi-ts`が正常生成
- 旧環境ではユーザー操作上、タッチパネルが正常動作
- 旧環境での30秒イベント採取は操作タイミングの問題で0バイトだったが、動作確認結果を優先する
- その後、旧版動作中に60秒監視を実施し、4096バイトの実イベントを取得
- 旧版イベントには`ABS_X` code 0、`ABS_Y` code 1、`BTN_TOUCH` code 330、`EV_SYN`が含まれる
- 現行`Touch.h`が期待するイベント形式と旧版の実イベント形式は一致

### 現時点の有力な差分

現行版で追加した`vc4-kms-v3d`および`vc4-kms-dsi-7inch,disable_touch`によるKMS/DSI構成が、旧版のlegacy framebuffer構成と異なる。タッチ処理コードの座標基準より、表示スタック・firmwareタッチ初期化の差分を優先して比較する。

旧版で実イベントが確認できたため、物理パネル、FPC接続、`raspberrypi-ts`、座標形式は正常。現行版でイベントが0件になる原因は、現行のKMS/DSI overlay構成またはその初期化順序に限定される。

## 新版交換後の再確認

- 新版起動後も画面は800x480で正常表示
- framebufferは`vc4drmfb`
- GUIは`/dev/input/event2`を開いている
- タッチデバイスは`raspberrypi-ts`
- ユーザーがタップ・スワイプを実施した状態で60秒監視したが、イベントは0バイト
- 旧版では同様の監視で4096バイトのイベントを取得済み
- 同一実機で旧版のみイベントが出るため、問題は新版のKMS/DSI構成に確定

## 重要な制約

Codexから画面表示、プロセス、デバイス、入力イベントは遠隔確認できるが、物理パネルを実際に押す操作そのものは実行できない。物理タッチの検証時は、Pi上でイベント監視を開始してからユーザーが画面をタップする必要がある。
