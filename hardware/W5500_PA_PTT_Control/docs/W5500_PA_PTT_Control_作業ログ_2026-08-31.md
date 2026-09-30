---
title: W5500_PA_PTT_Control 作業ログ（2026-08-31）
---

# W5500_PA_PTT_Control 作業ログ（2026-08-31）

本書は2026-08-31のセッションで行った作業内容の記録である。恒久的な仕様は
`W5500_PA_PTT_Control_仕様書.md`（Rev.2.2、本書作成時点）を正とし、本書は
その後の変更点と作業経緯のログとして扱う。仕様書側は本書の内容を踏まえて
別途Rev.3として改訂予定。

---

## 1. 経緯・調査

### 1.1 raspi5側の設定画面調査

「raspi5の設定画面にPAのIPアドレスを設定する項目を追加してほしい」という
依頼を受けて調査した結果、**既に実装済み**であることが判明した。

- `pi5/gui/screens/settings.py`（91〜101行目）に「PA_Power/PTTコントローラ
  (ESP32)」セクションがあり、`ptt_controller_ip_edit`（QLineEdit）でIPを
  入力・保存できる。
- 保存先は `~/.config/shonan-pi5/settings.json` の `ptt_controller_host`
  キー（`pi5/gui/settings_store.py`）。空欄なら連携無効。

→ 追加作業は不要と判断し、この件はクローズ。

### 1.2 ファームウェアの不整合の発覚

作業開始時点で使っていた独立検証用ディレクトリ
`/Users/kazuichishinjo/AppDev/W5500_PA_PTT_Control/`（本リポジトリ外）と、
本リポジトリの本番ファームウェア `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
とでGPIOピン配置・HTTP API名が食い違っていることが判明した。

| | 独立検証版（リポジトリ外） | 本番版（本リポジトリ） |
|---|---|---|
| GPIO25 | LNA（受信プリアンプ） | 未接続・廃止 |
| GPIO26 | PTT | POWER（12V電源） |
| GPIO27 | 12V電源 | PTT |
| API | `/power`, `/ptt`（新設） | `/tx`, `/ch`（既存仕様） |
| IP | 固定IP化 | DHCP（当時） |

**方針決定：本番版（本リポジトリのファイル）を正とし、以後の作業は本番版に対して行う。**
独立検証版ディレクトリには以後手を加えない。

---

## 2. 本番ファームウェアへの機能追加

`hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino` に対し、以下の機能を追加した。

### 2.1 12V電源 / PTT の遅延ON機能

- `GET /ch?idx=0&state=on`（12V電源ON要求）を受信してから、設定した秒数
  （既定 **3秒**）待ってから実際にGPIO26をONにする。
- `GET /tx?state=on` および `GET /ch?idx=1&state=on`（PTT ON要求）を受信
  してから、設定したミリ秒（既定 **50ms**）待ってから実際にGPIO27をONにする。
- OFF要求（`state=off`）は安全のため**常に即時反映**し、保留中のON要求は
  キャンセルする。
- 実装は `delay()` によるブロッキングではなく、`millis()` を使った
  非ブロッキングのタイマー予約方式（`servicePendingOutputs()` を `loop()`
  内で毎回呼び出す）。HTTPサーバーは遅延待ち中も他のリクエストに応答できる。

### 2.2 遅延時間の設定機能（Web UI / HTTP API）

- `GET /config` … 遅延時間・IPアドレス設定用のHTML設定画面。
- `GET /config/delay?power_delay_sec=<秒>&ptt_delay_ms=<ms>` … 遅延時間を
  変更しNVS(Preferences、namespace `w5500cfg`)に保存。以後はNVSの値が
  優先され、電源断・再起動後も保持される。

### 2.3 IPアドレス変更機能（DHCP廃止・固定IP化）

- 従来のDHCP方式を廃止し、**固定IP方式**に変更した。初期値は
  `IP=192.168.0.100` / `Gateway=192.168.0.1` / `Subnet=255.255.255.0`。
- `GET /config/network?ip=<IP>&gateway=<GW>&subnet=<MASK>` でIP設定を
  変更しNVSに保存。保存後は `ESP.restart()` で自動再起動し新しいIPで
  起動し直す（Ethernetライブラリの制約上、動的な再初期化ではなく再起動で
  反映する方式とした）。
- MACアドレスは変更していない（`02:AA:BB:CC:DE:01`のまま。既存仕様書
  2.1節参照）。

### 2.4 `/api/status` の拡張

JSONレスポンスに以下のキーを追加した。

```json
{
  "power": true,
  "power_pending": false,
  "ptt": false,
  "ptt_pending": false,
  "tx_active": false,
  "power_delay_ms": 3000,
  "ptt_delay_ms": 50,
  "ip": "192.168.0.100"
}
```

`*_pending` は遅延ON待ち中（要求は受けたがまだGPIOに反映していない状態）
であることを示す。ステータスページ（`/`）の表示にも「ON待ち」状態を
反映済み。

---

## 3. WiFiテスト版の新規追加

W5500（イーサネットモジュール）が未実装の段階でもHTTPロジック
（GPIO制御・遅延処理・設定画面）だけを実機で検証できるよう、通信層のみ
ESP32内蔵WiFi（APモード）に置き換えたテスト用スケッチを新規に追加した。

- 配置場所: `hardware/W5500_PA_PTT_Control_WiFiTest/W5500_PA_PTT_Control_WiFiTest.ino`
- GPIO制御・HTTPハンドラ・遅延設定・NVS保存のロジックは本番版と完全に同一。
  Ethernet(W5500) → WiFi(ESP32内蔵AP) の置き換えのみ。
- 接続情報:
  - SSID: `PA-PTT-Test`
  - パスワード: `ptttest123`
  - 既定IP: `192.168.4.1`（`/config`から変更可、`WiFi.softAPConfig()`使用）
- W5500実装後は本番版に書き込み直すこと。本ディレクトリは削除して構わない。

### 3.1 動作確認結果

MacをSSID `PA-PTT-Test` に接続し、`http://192.168.4.1/` へのアクセスに
成功。ステータス画面・`/config`設定画面・`/api/status`のJSON取得を確認済み。

---

## 4. 実機書き込み作業

使用ツール: `arduino-cli`（`esp32:esp32:esp32` ボード、ESP32-D0WD-V3、
MAC(Wi-Fi/BT側チップMAC): `70:4b:ca:7b:eb:94`）。

### 4.1 転送速度のトラブルシューティング

初回、既定の転送速度（921600bps）で書き込みを試みたところ、
`A fatal error occurred: The chip stopped responding.` で失敗した。
`UploadSpeed=115200` を明示指定して再試行したところ成功した。以後の
書き込みはすべて115200bpsで実施している。

```
arduino-cli upload -p /dev/cu.usbserial-110 \
  --fqbn "esp32:esp32:esp32:UploadSpeed=115200" \
  <スケッチディレクトリ>
```

### 4.2 書き込み履歴

1. 本番版（旧・遅延/IP変更機能追加前）を書き込み、動作確認。
2. 遅延設定・IP変更機能を追加したWiFiテスト版を書き込み、
   `http://192.168.4.1/` にアクセスして動作確認（3節参照）。
3. 遅延設定・IP変更機能を追加した**本番版**を書き込み。起動ログは以下の通り
   （W5500未接続のため想定通りリンクアップに失敗している）。

```
=== W5500_PA_PTT_Control 起動 ===
[CFG] 12V電源ON遅延=3000ms, PTT ON遅延=50ms
[OUT] POWER 12V (GPIO26) -> OFF
[OUT] PTT (GPIO27) -> OFF
固定IPで初期化中... IP=192.168.0.100 GW=192.168.0.1 MASK=255.255.255.0
W5500が検出できません。配線を確認してください。
IPアドレス: 0.0.0.0
Webサーバー起動 (port 80)
```

設定値（遅延3000ms/50ms、固定IP 192.168.0.100/24）は正しく読み込まれて
いる。W5500配線完了後、同一LAN上のPCから `http://192.168.0.100/` への
アクセスで動作確認を行う必要がある（本書作成時点で未実施）。

---

## 5. Git操作

以下の変更をコミット・pushした（リポジトリ: `kazushinjo/Shonan_Lite-RasPI5`、
ブランチ: `main`）。

- コミット: `26137ba`
  - `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`（変更）
  - `hardware/W5500_PA_PTT_Control_WiFiTest/W5500_PA_PTT_Control_WiFiTest.ino`（新規）
- push: `8dada17..26137ba main -> main`

---

## 6. 現状と今後の課題

- 本番ファームウェアはESP32実機に書き込み済み。ただしW5500ハードウェアの
  配線が未完了のため、実際のEthernet通信（`http://192.168.0.100/`への
  アクセス）は本書作成時点でまだ確認できていない。
- W5500配線完了後にやるべきこと:
  1. Macを192.168.0.0/24のLAN（ESP32と同一LAN）に接続。
  2. `http://192.168.0.100/` にアクセスし、ステータス画面・`/config`・
     `/api/status`が本番仕様書通りに動作することを確認。
  3. 12V電源／PTTの実駆動回路（Q1/Q3/Q5）との結合試験（仕様書5節の
     既存の未確定事項）。
- `W5500_PA_PTT_Control_仕様書.md`（Rev.2.2）は本書の変更内容
  （DHCP→固定IP化、遅延設定機能、`/config`系API追加）を反映していない。
  次回改訂時にRev.3として統合することが望ましい。
- WiFiテスト版（`hardware/W5500_PA_PTT_Control_WiFiTest/`）はW5500実装・
  結合試験が完了した時点で削除して構わない。

---

## 7. 関連ファイル

- 本番スケッチ: `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
- WiFiテスト用スケッチ: `hardware/W5500_PA_PTT_Control_WiFiTest/W5500_PA_PTT_Control_WiFiTest.ino`
- 既存仕様書（Rev.2.2、本書作成時点で本番版と一部内容が乖離）:
  `hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_仕様書.md`
- raspi5側の連携設定: `pi5/gui/screens/settings.py`（IP入力欄）、
  `pi5/gui/backend.py`（`_send_ptt_request()`, `_send_ptt_channel_state()`）
