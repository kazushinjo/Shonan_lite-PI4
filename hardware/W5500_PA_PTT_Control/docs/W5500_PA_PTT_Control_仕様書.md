---
title: ESP32+W5500 PA/PTT/LNA シーケンス制御 開発仕様書
---

# ESP32+W5500 PA/PTT/LNA シーケンス制御 開発仕様書

| 項目 | 内容 |
|---|---|
| 版数 | Rev.1.0 |
| 作成日 | 2026-08-07 |
| 対象ボード | ESP32 (WROVER系、無印ESP32) + W5500 イーサネットモジュール |
| 対象スケッチ | `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino` |
| 連携先 | shonan-android（DATV送信アプリ） |
| ステータス | ソフトウェア実装・コンパイル確認済み。実機書き込み・実地テストは未実施 |

---

## 1. 目的・スコープ

shonan-android の送信ボタン操作に連動して、無線機側の **LNA（受信プリアンプ）・PTT・PA（電力増幅器）電源** を、イーサネット経由で安全な順序で自動切替する。

**スコープに含むもの**
- ESP32 + W5500 によるLNA/PTT/PA 3チャンネルのON/OFF制御
- shonan-androidからのHTTPリクエストによるTX/RX切替
- ブラウザによる手動確認・デバッグ用UI

**スコープに含まないもの**
- shonan-androidアプリ側での送信ボタン実装・HTTPリクエスト送出処理（別途アプリ側での対応が必要）
- PA・LNA自体の回路設計（電源系統の実装は利用者の無線機構成に依存）

---

## 2. ハードウェア構成

### 2.1 使用部品

| 部品 | 備考 |
|---|---|
| ESP32 (WROVERモジュール等) | 無印ESP32。ESP32-C3等のネイティブUSBチップとは別物 |
| W5500 イーサネットモジュール | SPI接続。MACアドレス内蔵なしのためスケッチ内で任意設定 |
| 出力段（3ch） | LNA・PTT・PA各系統の電源スイッチング（リレー or SSR、利用者の系統に依存） |

### 2.2 SPI配線（ESP32 ⇔ W5500）

| W5500 | ESP32 GPIO |
|---|---|
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| CS (SS) | GPIO 5 |
| RST | 未使用（3.3VまたはENに接続、または未接続可） |
| VCC | 3.3V |
| GND | GND |

### 2.3 出力ピン割り当て

| チャンネル | ESP32 GPIO | 論理 | 起動時状態 |
|---|---|---|---|
| LNA | GPIO 25 | active-HIGH | **ON**（受信状態） |
| PTT | GPIO 26 | active-HIGH | OFF |
| PA | GPIO 27 | active-HIGH | OFF |

> GPIO出力は3.3Vロジックのため、リレー／SSRを直接駆動できない場合はトランジスタ等で駆動段を追加すること（本書はロジック層の仕様のみを規定し、駆動回路は概略構成を回路図に示す）。

---

## 3. 動作シーケンス

### 3.1 送信開始（RX → TX）

shonan-androidの送信ボタンが押された際、以下の順序で切り替える。

```
[受信状態]  LNA=ON, PTT=OFF, PA=OFF
     │
     │ ① LNA OFF
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ② 100ms 待機
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ③ PTT・PA を同時にON
     ▼
[送信状態]  LNA=OFF, PTT=ON, PA=ON
```

### 3.2 送信終了（TX → RX）

```
[送信状態]  LNA=OFF, PTT=ON, PA=ON
     │
     │ ① PTT・PA を同時にOFF
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ② 100ms 待機
     ▼
   LNA=OFF, PTT=OFF, PA=OFF
     │
     │ ③ LNA ON
     ▼
[受信状態]  LNA=ON, PTT=OFF, PA=OFF
```

### 3.3 設計意図

- 送信開始時：LNAを先に切り離してからPTT/PAを立ち上げることで、送信高出力によるLNA破損を防止する。
- 送信終了時：PA/PTTを先に落としてからLNAを戻すことで、送信の残留出力がLNAに回り込むことを防止する。
- 待機時間100msは実機の系統切替に応じて `W5500_PA_PTT_Control.ino` 内の `delay(100)` を調整可能。

---

## 4. ネットワーク・HTTP API仕様

### 4.1 ネットワーク設定

- DHCPでIPアドレスを取得（固定IPは未使用。現行構成のため）
- MACアドレスはスケッチ内で固定値を指定（同一LAN内で重複しないこと）

### 4.2 API一覧

| エンドポイント | メソッド | 説明 | レスポンス |
|---|---|---|---|
| `/` | GET | ステータス確認用HTML（手動ON/OFFボタン付き） | HTML |
| `/tx?state=on` | GET | **送信開始**（shonan-androidから呼び出し） | `TX`（プレーンテキスト） |
| `/tx?state=off` | GET | **送信終了**（shonan-androidから呼び出し） | `RX`（プレーンテキスト） |
| `/toggle?ch=0..2` | GET | 個別チャンネル手動トグル（配線確認用デバッグ機能） | `/` へリダイレクト |
| `/api/status` | GET | 現在状態をJSONで取得 | `{"out1":bool,"out2":bool,"out3":bool,"tx_active":bool}` |

`out1`=LNA、`out2`=PTT、`out3`=PA に対応する。

### 4.3 shonan-android側の呼び出し例

```
送信ボタン押下時: GET http://<ESP32のIPアドレス>/tx?state=on
送信ボタン解放時: GET http://<ESP32のIPアドレス>/tx?state=off
```

ESP32のIPアドレスはDHCP割当のため、shonan-android側の設定画面等で利用者がIPを入力・保持する運用を想定する（★DDNS/mDNS等による自動検出は本版では未実装）。

---

## 5. 未確定・今後の課題

- ★ PA/PTT/LNAの実際の駆動回路（リレー/SSR種別、電流容量）は利用者の無線機構成に依存するため、回路図は概略構成として提示（5節参照）。回路図.svg 参照。
- ★ IPアドレス固定化またはmDNS対応（`http://shonan-ptt.local/` 等）は未実装。運用上必要であれば追加検討。
- ★ shonan-androidアプリ側でのHTTPリクエスト送出実装は本スケッチのスコープ外。アプリ側の送信ボタンハンドラに追加が必要。
- 実機での書き込み・動作テストは未実施（2026-08-07時点）。

---

## 6. 関連ファイル

- スケッチ本体: `hardware/W5500_PA_PTT_Control/W5500_PA_PTT_Control.ino`
- 回路図: `hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_回路図.svg`
