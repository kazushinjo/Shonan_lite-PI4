# Tanzawa Pi4 DVB-S2 RF送受信評価レポート

作成日: 2026-08-11  
対象: `kazushinjo/tanzawa-pi4` Pi4送受信GUI、PlutoSDR `v0.32-dirty`

## 1. 目的

Pi4でH.264/AACを生成し、PlutoSDRでDVB-S2変調した信号を、40 dB外部アッテネータを介して同一PlutoSDRで受信する。シンボルレート、FEC、パイロット、RXゲインを変更し、DVB-S2ロック条件と映像受信可否を確認する。

## 2. 構成

```text
Raspberry Pi 4 (H.264/AACエンコード)
  -> RTMP
PlutoSDR TX (DVB-S2変調、TX出力 0 dB)
  -> 40 dB外部アッテネータ
PlutoSDR RX
  -> IIO/IP
Raspberry Pi 4 (dvbs2-rx、TS受信、映像デコード)
```

RF周波数は437 MHz。変調はQPSK、Normal FECFRAME、roll-off 0.35、2 samples/symbol、RXバッファ32768 samplesとした。

映像条件はH.264、1280×720、30 fps、400 kbps、GOP 30。音声はAAC、44.1 kHz、mono、Pi4入力16 kbps、Pluto側出力32 kbpsとした。

## 3. Pi4プログラムの修正内容

- 0.5 Msym/sを含むRXを2 samples/symbolへ統一
- Pluto RXバッファを32768 samplesに設定
- RXパイロット判定をAUTOに設定
- TSバイト数ではなく`dvbs2-rx`の`Lock=True/False`をGUIへ反映
- IIOタイムアウトをGUIログへ転送
- TSデータと診断ログを別FDへ分離
- 不足していた`udp_relay.py`をPi4へ配置
- H.264 GOPを30へ変更
- TX出力の既定値と保存設定を0 dBへ変更

Python構文確認、シェル構文確認、既存単体テスト5件はすべて成功した。

## 4. IIOタイムアウト調査

初期試験では、受信開始約3秒後に次のエラーが発生した。

```text
Unable to refill buffer: Connection timed out (110)
```

Pi4 GUI、`watchdog_rx.sh`、`dvbs2-rx`、Ethernet転送を外し、Pluto本体上で`iio_readdev`を実行しても0 byteで同じタイムアウトが再現した。このときRX DMA割り込みも増加しなかった。

Plutoを再起動した後、Pluto本体で8秒間に260,902,912 byteのIQデータを取得できた。以後の基準RF試験ではIIOタイムアウトは解消した。このことから、当該IIO障害はPluto内部RX DMAの一時的な停止・固着と判断した。

IIOエラーが発生した測定値はRFのNO LOCKとして扱わず、Pluto再起動後に再測定する必要がある。

## 5. 基準RF・映像試験

| 項目 | 結果 |
|---|---:|
| シンボルレート | 0.5 Msym/s |
| FEC | 1/2 |
| TXパイロット | OFF |
| RXパイロット | AUTO |
| TX出力 | 0 dB |
| RX | `slow_attack` AGC |
| DVB-S2ロック | 成功 |
| SNR | 約13.9 dB |
| FER / PER | 0 / 0 |
| TSサイズ | 約3.67 MB |
| TS時間 | 約61.97秒 |
| 映像 | H.264 1280×720、30 fps |
| デコードフレーム数 | 1,831 |

受信開始がH.264 GOP途中だったため、冒頭にPPS未取得と一部マクロブロックエラーが記録されたが、次のキーフレーム以降はデコードできた。

## 6. 72条件試験

次の組み合わせを各条件60秒間測定した。

```text
4 symbol rates × 3 FEC × 2 pilot modes × 3 manual RX gains = 72条件
```

- シンボルレート: 0.5、1.0、1.5、2.0 Msym/s
- FEC: 1/2、3/5、2/3
- TXパイロット: OFF、ON
- RXゲイン: manual 40、50、60 dB

合格条件は、複数回の`Lock=True`、TSデータ増加、IIOエラーなしとした。正常にロックした条件は、60回のログ取得中59回で`Lock=True`を維持した。

### 6.1 シンボルレート別集計

| シンボルレート | PASS | NO LOCK | 備考 |
|---:|---:|---:|---|
| 0.5 Msym/s | 18 | 0 | 全条件成功、最大SNR約13.99 dB |
| 1.0 Msym/s | 18 | 0 | 全条件成功、最大SNR約18.02 dB |
| 1.5 Msym/s | 0 | 18 | 全条件で60/60回Lock=False |
| 2.0 Msym/s | 0 | 18 | 全条件で60/60回Lock=False |
| 合計 | 36 | 36 | 72条件すべて確定 |

### 6.2 0.5～2.0 Msym/s全条件一覧

記号: `PASS`=60秒間の継続ロックとTS受信を確認、`NO LOCK`=60回すべてLock=False

| FEC | Pilot | RX gain | 0.5M | 1.0M | 1.5M | 2.0M |
|---|---|---:|---:|---:|---:|---:|
| 1/2 | OFF | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 1/2 | OFF | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 1/2 | OFF | 60 dB | PASS | PASS | NO LOCK | NO LOCK |
| 1/2 | ON | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 1/2 | ON | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 1/2 | ON | 60 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | OFF | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | OFF | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | OFF | 60 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | ON | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | ON | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 3/5 | ON | 60 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | OFF | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | OFF | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | OFF | 60 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | ON | 40 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | ON | 50 dB | PASS | PASS | NO LOCK | NO LOCK |
| 2/3 | ON | 60 dB | PASS | PASS | NO LOCK | NO LOCK |

### 6.3 0.5 Msym/s再測定結果

初回にIIOエラー、パイロット不一致、またはロックログ未取得だった8条件を、IIOプリフライトと実パイロット確認後に再測定した。全条件が1回目の再測定でPASSした。

| 元条件 | FEC | Pilot | Gain | Lock | 最大SNR | TS byte | 結果 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | 1/2 | OFF | 40 | 59/60 | 13.84 dB | 3,574,068 | PASS |
| 2 | 1/2 | OFF | 50 | 59/60 | 13.98 dB | 3,594,184 | PASS |
| 3 | 1/2 | OFF | 60 | 59/60 | 13.97 dB | 3,598,320 | PASS |
| 4 | 1/2 | ON | 40 | 59/60 | 13.97 dB | 3,509,772 | PASS |
| 5 | 1/2 | ON | 50 | 59/60 | 13.99 dB | 3,533,836 | PASS |
| 6 | 1/2 | ON | 60 | 59/60 | 13.98 dB | 3,529,888 | PASS |
| 7 | 3/5 | OFF | 40 | 59/60 | 13.99 dB | 4,290,160 | PASS |
| 8 | 3/5 | OFF | 50 | 59/60 | 13.97 dB | 4,319,112 | PASS |

### 6.4 1.0 Msym/s結果

FEC 1/2・3/5・2/3、パイロットON/OFF、RXゲイン40/50/60 dBの18条件すべてでPASSした。

- Lock: 各条件59/60
- 最大SNR: 17.47～18.02 dB
- TSサイズ: 約7.04～9.62 MB/60秒
- PER: 多くの条件で0、一部最大約2.2e-4

今回の72条件範囲では、1.0 Msym/sが最も広い条件で安定してロックした。

### 6.5 1.5および2.0 Msym/s結果

1.5 Msym/sと2.0 Msym/sは、それぞれ18条件すべてで60回のログが取得されたが、全回`Lock=False`、FECFRAME 0、TS 0 byteだった。RXゲイン、FEC、パイロットのいずれを変更してもロックしなかった。

これはIIOタイムアウトではなく、IQ受信は動作している状態でのDVB-S2 NO LOCKである。高シンボルレート時の送受信サンプルレート、Pluto FIR/帯域、`dvbs2-rx`同期条件を追加調査する必要がある。

## 7. 結論

1. Pluto RX DMA固着を再起動で解消後、0.5 Msym/s・QPSK 1/2・TX 0 dB・40 dB外部アッテネータでRFロックし、HD映像1,831フレームをデコードできた。
2. 1.0 Msym/sはFEC、パイロット、RXゲインの全18条件で安定してロックした。
3. 0.5 Msym/sは再測定を含む全18条件で安定してロックした。
4. 1.5および2.0 Msym/sは全36条件で正常な60秒測定を行ったが、ロックしなかった。
5. 最終集計はPASS 36、NO LOCK 36で、72条件すべて確定した。

## 8. 追加調査・対策結果

### 8.1 1.5/2.0 Msym/s受信設定

| Symbol rate | RX実サンプルレート | RX RF帯域 | FIR | 受信スペクトラム(-30 dB概算) | 結果 |
|---:|---:|---:|---|---:|---|
| 1.5 Msym/s | 3.0 MS/s | 2.025 MHz | ON | 約3.0 MHz | NO LOCK |
| 2.0 Msym/s | 4.0 MS/s | 2.700 MHz | ON | 約4.0 MHz | NO LOCK |

指定値はPlutoへ正しく反映され、IQも各4,194,304 byte取得できた。いずれもフレーム同期候補には一時到達するが同期を維持できず、スペクトラムはほぼNyquist幅を占有した。したがって未設定やIIO停止ではなく、高レート時の波形品質または同期処理が今後の調査対象である。

### 8.2 IIOプリフライト

GUIの受信開始前に短いIIO DMA読出しを追加した。4,096 byteを6秒以内に取得できない場合は受信処理を開始せず、`RF NO LOCK`ではなくPluto RX DMA/IIO異常として通知する。実機では4,096 byte取得に成功した。

### 8.3 H.264映像表示判定

MPEG-TS内のH.264 Annex-B NALを監視し、SPS (NAL 7) とPPS (NAL 8) の受信後、最初のIDR (NAL 5)を検出した時点で`video_ready=1`をGUIへ通知するよう変更した。RFループ試験（0.5 Msym/s、QPSK 1/2、pilot OFF、RX gain 40 dB）では、受信開始約2秒後にSPS/PPS/IDRを検出し、DVB-S2 Lock=True、20秒で約1.02 MBのTS受信を確認した。

## 9. 生データ

- 72条件初回結果: Pi4 `/home/pi/rf_sweep_72_results.csv`
- 条件1・6・8再測定: Pi4 `/home/pi/rf_retest_1_6_8.csv`
- 条件2・3・4・5・7再測定: Pi4 `/home/pi/rf_retest_remaining5.csv`

## 10. 無印ADALM-Pluto Rev.C 72条件再試験

### 10.1 試験対象

- 機種: 無印ADALM-Pluto Rev.C (Z7010/AD9363、IIO稼働時AD9364表示)
- IPアドレス: 192.168.0.136
- RF接続: TX - 40 dB外部アッテネータ - RX
- TX出力: 0 dB
- 周波数: 437 MHz
- 判定時間: 各条件60秒（送信安定待ち10秒を別途確保）

### 10.2 再試験結果

| シンボルレート | PASS | NO LOCK | IIO ERROR | 結果 |
|---:|---:|---:|---:|---|
| 0.5 Msym/s | 18 | 0 | 0 | 全条件PASS |
| 1.0 Msym/s | 18 | 0 | 0 | 全条件PASS |
| 1.5 Msym/s | 0 | 18 | 0 | 全条件NO LOCK |
| 2.0 Msym/s | 0 | 18 | 0 | 全条件NO LOCK |
| 合計 | 36 | 36 | 0 | 72条件確定 |

FEC 1/2・3/5・2/3、Pilot ON/OFF、RX gain 40/50/60 dBを組み合わせた72条件をすべて再試験した。各条件でPilot要求値と実際の`pluto_dvb`設定が一致し、不一致は0件だった。0.5/1.0 Msym/sのPASS条件では継続した`Lock=True`とTS byte増加を確認した。1.5/2.0 Msym/sは全判定で`Lock=False`、TS 0 byteだったが、IIOプリフライト異常は発生していない。

### 10.3 再試験データ

- CSV: `pi4/docs/rf_sweep_72_rerun_2026-08-11.csv`
- 行数: 72、条件番号: 1～72（一意）
- 最終集計: PASS 36、NO LOCK 36、IIO ERROR 0、Pilot不一致 0
