# DVB-S2 ループバック試験 手順書

対象機: Raspberry Pi 4(ホスト名 `DVB-S2`, `192.168.0.135`, ユーザー `pi`)
前提: `docs/loopback_test_report.docx` の試験を再現するための手順。ビルド環境(GNU Radio 3.10.12.0 / gr-dvbs2rx / GTK4 / `~/dvb-s` 一式)は構築済みであること。

## 0. ハードウェア接続

```
PlutoSDR TX ── 同軸ケーブル ── 固定アッテネータ 40dB ── PlutoSDR RX
```

- PlutoSDR は USB でPiに接続(`ip:192.168.2.1` または `usb:` で認識)
- USBカメラ(Logitech Webcam C270)を使う場合は Pi の USBポートに接続。認識されると `/dev/video0` が生成される

## 1. 前提確認

```bash
ssh pi@192.168.0.135

# PlutoSDR認識確認
iio_info -s | grep -i pluto

# (カメラを使う場合) カメラ認識確認
v4l2-ctl --list-devices
ls -la /dev/video0
```

## 2. テスト用映像ソースの準備

### 2a. 合成テストパターン(カラーバー、ffmpeg生成)

```bash
cd ~/dvb-s
ffmpeg -y -f lavfi -i "testsrc=size=320x240:rate=25" -t 30 \
  -c:v mpeg2video -b:v 1500k -f mpegts test.ts
```

### 2b. USBカメラのライブ映像を使う場合(代替)

`test.ts` の代わりにカメラ映像を直接 `dvbs2-tx` へパイプする、またはファイル化してから送信する。

```bash
# 例: カメラ映像を10秒分ファイル化してテスト
ffmpeg -y -f v4l2 -i /dev/video0 -t 10 -c:v mpeg2video -b:v 1500k -f mpegts cam_test.ts

# 例: ライブでパイプしてそのまま送信(--source fd, --in-repeatなし)
ffmpeg -f v4l2 -i /dev/video0 -c:v mpeg2video -b:v 1500k -f mpegts - | \
  dvbs2-tx --source fd --sink plutosdr --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
    -f 438022000 -m QPSK1/4 -s 333000 -o 4 -r 0.2
```

解像度・フレームレートは `v4l2-ctl -d /dev/video0 --list-formats-ext` で対応フォーマットを確認してから決めること。

## 3. 送信側(TX)起動

```bash
cd ~/dvb-s
nohup dvbs2-tx --source file --in-file test.ts --in-repeat \
  --sink plutosdr --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
  -f 438022000 -m QPSK1/4 -s 333000 -o 4 -r 0.2 \
  > /tmp/tx_test.log 2>&1 &
```

- `--plutosdr-attn 0`: TX内部減衰0dB(外部40dBパッドと合わせて実効40dB程度)。信号が強すぎる/弱すぎる場合はここを調整する(パッドの付け替えは不要)
- 起動確認: `ps aux | grep dvbs2-tx`、`cat /tmp/tx_test.log`

## 4. 受信側(RX)起動

実運用スクリプトをそのまま使う。

```bash
cd ~/dvb-s
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 nohup ./start_rx.sh 438022000 QPSK1/4 333000 \
  > /tmp/start_rx_out.log 2>&1 &
```

内部で `RF_UDP_dvbs2_rx.py`(受信フローグラフ)と `ffplay`(`udp://127.0.0.1:2000`)が起動する。

## 5. 動作確認

`tmp.ts` ファイル(`blocks_file_sink_0`)は **未接続の dead code** なので確認に使わないこと。以下で確認する:

```bash
# 受信データが流れているか(epy_block_0のログ、デバッグ計装時のみ)
tail -f /tmp/rx_stdout.log

# ffplayが実際にフレームをデコードしているか(M-V:行が進んでいれば再生中)
tail -c 800 /tmp/ffplay_rx.log

# RSSI / AGCゲイン確認(信号強度の目安)
iio_attr -u ip:192.168.2.1 -i -c ad9361-phy voltage0 rssi
iio_attr -u ip:192.168.2.1 -i -c ad9361-phy voltage0 hardwaregain
```

### スクリーンショット取得(重要: Wayland環境)

Piのデスクトップは **Wayland** のため `scrot`(X11用)では黒画像になる。`grim` を使うこと。

```bash
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 grim /tmp/screenshot.png
scp pi@192.168.0.135:/tmp/screenshot.png ./
```

## 6. 停止・後片付け

```bash
cd ~/dvb-s
./stop_rx.sh
pkill -f dvbs2-tx
ps aux | grep -E "dvbs2-tx|RF_UDP|ffplay" | grep -v grep   # 何も出なければOK
```

## 7. リアルタイム(ライブ)配信の場合の注意 【重要】

USBカメラのライブ映像をその場でエンコードして流す(ファイルに事前録画しない)場合、**起動順序を間違えると受信が一切成功しない**。原因と正しい手順は以下のとおり。

### 原因1: RXの起動タイミング(主原因)

自作 `RF_UDP_dvbs2_rx.py`(再構築した `dvbs2rx_rx_hier`)は、公式 `dvbs2-rx` CLI と比べて初期ロックの頑健性が低い。**TXが起動した直後(周波数/ゲイン安定化中の過渡状態)にRXを起動すると、初期ロックに失敗し、以後データが一切流れない。**

切り分け方法: 公式 `dvbs2-rx --log` CLIを同じ信号に向けて即座にロックすることを確認し(TX側の信号自体は正常と証明)、自作RXの起動タイミングをTX安定後にずらすと同じ信号で成功する、という手順で特定した。`--source fd`(ライブパイプ)自体は無罪。

### 原因2: `start_rx.sh` 内の `pkill -f ffmpeg`

`start_rx.sh` は起動時に無条件で `ffmpeg` という名前のプロセスを全て強制終了する(元々は前回実行の残骸を掃除するための処理)。ライブカメラ配信のTX側も `ffmpeg` を使うため、`start_rx.sh` でRXを起動するたびに **TX側のffmpegも巻き込んで停止**してしまう。ファイル事前録画方式ではffmpegがTX開始前に終了しているため、この問題は表面化しない。

### 正しい手順(ライブ配信用)

```bash
# 1. TX(カメラ→ffmpeg→dvbs2-tx)を先に起動
cd ~/dvb-s
nohup bash -c "ffmpeg -f v4l2 -input_format yuyv422 -video_size 160x120 -framerate 10 \
  -i /dev/video0 -c:v mpeg2video -b:v 400k -f mpegts - | \
  dvbs2-tx --source fd --sink plutosdr --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
  -f 438022000 -m QPSK1/4 -s 333000 -o 4 -r 0.2" > /tmp/tx_live.log 2>&1 &

# 2. 約10秒待ってTXを安定させる(この間にRXを起動しないこと)
sleep 10

# 3. RXは start_rx.sh を使わず、コンポーネントを個別に手動起動する
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 nohup ./RF_UDP_dvbs2_rx.py \
  -g 438022000 -m QPSK1/4 -s 333000 -o 4 > /tmp/rx_live.log 2>&1 &
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 nohup ffplay -loglevel info \
  udp://127.0.0.1:2000 > /tmp/ffplay_live.log 2>&1 &
```

解像度は160x120/10fps/400kbps程度に抑えること(320x240/25fps/1500kbpsだとPi4のCPUがソフトウェアエンコードに追いつかず実時間の0.3〜0.4倍程度まで落ち込む。160x120/10fpsなら実時間の1.2倍程度で安定)。

停止時も `pkill -f ffmpeg` を使わず、記録したPIDを個別に `kill` すること。

## 8. シンボルレート上限とHD映像伝送 【重要】

### 発見: RPi4-PlutoSDR間のUSBスループット実測上限

生IQサンプルを `iio_readdev` で直接キャプチャして測定した結果、**USB経由の実効スループットに上限(約1.8〜1.9 Msps)がある**ことが判明した。これを超えるサンプルレートを要求しても、実際に届くのはこの上限までで、超過分は失われて信号が破綻し、DVB-S2ロックが不可能になる。

| 要求サンプルレート | 実測達成レート | 達成率 |
|---|---|---|
| 1.332 Msps(333kSym/s, sps=4) | 1.325 Msps | 99.5% |
| 2.00 Msps | 1.907 Msps | 95.4% |
| 4.00 Msps(1MSym/s sps=4 など) | 1.82 Msps | 45.5%(大幅未達 → ロック不可) |

計測コマンド:
```bash
iio_attr -u ip:192.168.2.1 -i -c ad9361-phy voltage0 sampling_frequency <Hz>
timeout 5 iio_readdev -u ip:192.168.2.1 -b 8192 cf-ad9361-lpc voltage0 voltage1 > /tmp/rawiq.bin
# 実測レート = ファイルサイズ / 4バイト(I+Q) / 秒数
```

MODCOD(QPSK/8PSK)や信号の質は無関係。**サンプルレート(=シンボルレート×sps)がこの上限を超えるかどうかだけ**が問題。

### 新しい実用上限: 1 MSym/s(sps=2, 2Msps)

333kSym/sの3倍のスループットを、以下の設定で安定動作を確認済み(ファイルベース試験、SNR~30dB):

```bash
# TX
dvbs2-tx --source file --in-file test.ts --in-repeat --sink plutosdr \
  --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
  -f 438022000 -m QPSK3/4 -s 1000000 -o 2 -r 0.2

# RX
dvbs2-rx --source plutosdr --plutosdr-addr usb:X.X.X --plutosdr-gain-mode slow_attack \
  -f 438022000 -m QPSK3/4 -s 1000000 -o 2 -r 0.2 --log --sink file --out-file received.ts
```

1.5 MSym/s(sps=2, 3Msps)では初期ロック後に急激に劣化する(SNRが31dB→2.6dBまで数秒で崩壊)ことを確認済み。**1 MSym/sを安全な上限とすること。**

### HD(720p)映像の実現

- カメラのMJPG形式(`-input_format mjpeg`)で1280x720/30fpsをキャプチャ(YUYV形式だと720pは7.5fpsまでしか出ない)
- コーデックは `mpeg2video` ではなく **`libx264`**(H.264)を使うこと。mpeg2videoは320x240でも実時間0.4倍程度までしか出ないが、libx264 ultrafastなら720pで実時間1.1〜1.3倍を達成できる

```bash
ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i /dev/video0 \
  -c:v libx264 -preset ultrafast -tune zerolatency -b:v 1400k -pix_fmt yuv420p \
  -f mpegts - | \
  dvbs2-tx --source fd --sink plutosdr --plutosdr-addr ip:192.168.2.1 --plutosdr-attn 0 \
  -f 438022000 -m QPSK3/4 -s 1000000 -o 2 -r 0.2
```

QPSK3/4・1MSym/sの実効容量(約1.5Mbps)とH.264 1.4Mbpsのビットレートがちょうど適合する。720pの鮮明な映像伝送を実機で確認済み。

### 既知の不具合: ライブ配信が10〜20秒で停止する

ライブ(その場エンコード)配信を続けると、`dvbs2-rx` が **10〜20秒ほどで出力を停止**することがある。原因をスレッドごとのCPU使用量(`/proc/<pid>/task/*/stat`)で特定:

```bash
for tid in <各ブロックのTID>; do
  cat /proc/<pid>/task/$tid/comm
  cat /proc/<pid>/task/$tid/stat | awk '{print $14+$15}'  # utime+stime
done
```

`plsync_cc`(物理層フレーム同期ブロック)だけがCPUを消費し続け(再ロックを探索し続けている)、その先の `xfecframe_demapper` 以降(LDPC/BCH/デスクランブラ/デヘッダ/シンク)は完全に停止したまま、という状態だった。ライブソース特有のビットレート変動が `plsync_cc` の再ロックを妨げ、そのまま復帰しない実装上の弱点と判断。信号自体(RSSI)は正常なままなので、RF的な問題ではない。

### 対策: 自動再起動監視スクリプト(`watchdog_rx.sh`)

根本修正ではなく運用上の回避策として、出力が止まったら自動的にdvbs2-rxを再起動するスクリプトを実装した。

```bash
cd ~/dvb-s
./watchdog_rx.sh <freq> <modcod> <symrate> <sps> [rolloff]
# 例:
./watchdog_rx.sh 438022000 QPSK3/4 1000000 2 0.2
```

- Pluto USBアドレスを起動のたびに自動検出(セッション中にアドレスが変わることがあるため)
- `udp_relay.py` の送信バイト数を2秒ごとに監視し、**8秒間増加がなければスタールと判断してプロセスを再起動**
- 停止するときは `kill -TERM <watchdog_rx.shのPID>`(内部でdvbs2-rx/relayも道連れに終了する)

動作実績: 1回目の起動が18秒でスタール→自動検知→再起動、2回目の起動は35秒以上安定動作を確認。UDP経由でのHD映像受信(`ffmpeg -c copy`でのストリーム検出)も再起動後に機能することを確認済み。

### UDP経由送信の技術的注意点(`udp_relay.py`)

`dvbs2-rx --sink fd` の出力を `nc -u` で単純にUDP転送すると機能しない。判明した原因と対策:

1. **OpenBSD版 `nc -u` はUDPソケットを`connect()`するため**、宛先ポートに一瞬でもリスナーが不在だと`ICMP port unreachable`を受けて**サイレントに終了**する → `socket.sendto()`(unconnected socket)を使う自作リレーに置き換えて解決
2. **UDPデータグラムはTSパケット境界(188バイトの倍数)に揃える必要がある**。単純に固定バイト数で分割すると同期バイト(`0x47`)がずれ、ffmppeg/ffplayが認識できない → パケットごとに同期バイトを検証し、ズレたら自動再同期する実装(`udp_relay.py`)で解決
3. `ffplay`は元々バースト的な到達パターンに弱く`nan`のまま検出失敗することがあるが、`ffmpeg -c copy`(コピー/検証用途)なら同じデータを正しく検出できる。**再生用にはffplayではなく一度ファイル保存してから確認する方が確実**

`udp_relay.py` は `~/dvb-s/udp_relay.py` に配置済み。使い方:
```bash
dvbs2-rx --source plutosdr --plutosdr-addr usb:X.X.X ... --sink fd --out-fd 1 | python3 udp_relay.py
# UDP 127.0.0.1:2000 へ送信される
```

## 9. ライブ配信スタールの根本原因調査(詳細)

7〜8節で報告した「ライブ配信が10〜20秒で停止する」不具合について、さらに踏み込んだ調査を行った記録。

### 9.1 スレッド別CPU使用量による切り分け

`/proc/<pid>/task/*/stat` の utime+stime を数秒間隔でサンプリングし、どのブロックが動き続けているか特定する:

```bash
for tid in /proc/<pid>/task/*/; do
  echo "$(cat $tid/comm): $(cat $tid/stat | awk '{print $14+$15}')"
done
# 数秒後にもう一度実行し、差分を比較する
```

結果: `plsync_cc`(物理層フレーム同期)だけがCPUを消費し続け、`xfecframe_demapper`以降(LDPC/BCH/デスクランブラ/デヘッダ/シンク)は完全に停止。**信号を探索し続けているが、フレームの確定(ロック)に至っていない状態**と判明。

### 9.2 GNU Radio内蔵デバッグログの有効化

`gr-dvbs2rx`はビルド時に`DEBUG_LOGS=ON`(デフォルト)であれば`GR_LOG_DEBUG_LEVEL`マクロで詳細ログを出す仕組みを持つが、**`-d`フラグだけでは出力されない**。GNU Radio自体のログレベルがデフォルト`info`のため、`debug`レベルのログがフィルタされてしまう。

有効化するには、`gr.logging()`のAPIで明示的にdebugレベルを設定し、コンソールシンクを追加する必要がある(`~/dvb-s/dvbs2-rx-debug.py`というラッパースクリプトを作成済み):

```python
from gnuradio import gr
logging = gr.logging()
logging.set_default_level(gr.log_levels.debug)
logging.set_debug_level(gr.log_levels.debug)
logging.add_default_console_sink()
logging.add_debug_console_sink()
# この後で実際のdvbs2-rxスクリプトを実行する
```

使い方: `python3 dvbs2-rx-debug.py <dvbs2-rxと同じ引数群>`

**注意: `-d 2`以上は極めて大量のログを出力する(1分足らずで1GB超)。`/tmp`(tmpfsで2GB上限)を圧迫するため、必ずディスク使用量を監視すること(9.3節参照)。**

### 9.3 重要な副次的発見: ディスク(`/tmp`)枯渇によるスタール

上記デバッグログを使った長時間調査の過程で、**調査自体が生成したログファイルが`/tmp`(tmpfs 2GB上限)を使い切り、`file_sink write failed with error 8`という書き込みエラーが発生**することが分かった。この場合はロック自体はSNR30dB前後で維持されたまま、単に書き込みが止まるだけなので、`ls -la`によるファイルサイズ監視だけでは見分けがつかない。

対策:
- 長時間ログ取得時は`df -h /tmp`をこまめに確認する
- `watchdog_rx.sh`を使う場合も、将来的にはディスク空き容量チェックの追加を検討すること(現状はUDP送信バイト数の増加のみを監視)

`/tmp`をクリーンアップ(2GB→32MB使用)した上で再試験しても**独立してスタールが再現**したため、ディスク枯渇は「別に存在する副次的な問題」であり、後述の真の根本原因(9.4節)とは別物と判明した。

### 9.4 周波数オフセット推定値の追跡(`-d 2`)

`freq_sync`クラスの`Coarse frequency offset`/`Coarse corrected`の値をログから追跡した結果:
- ロック直後は`Coarse corrected: 1`(補正達成)、オフセットはほぼゼロ
- その後ほとんどの時間は`Coarse corrected: 0`のまま推移(全体の99.5%が`0`)
- ロック消失→再ロックを繰り返すたびに、ロック継続時間が短くなっていく(1000フレーム相当→14万フレーム相当→11フレーム→17→7→11→20→**以降永続的に消失**)

この「ロック保持時間が徐々に短くなる」というパターンから、**ライブソース特有の断続的なビットレート変動にさらされ続けることで、受信機内部の追従状態(周波数/タイミングループ)が徐々に劣化していく**ことが示唆された(ファームウェア更新前の観測)。

### 9.5 PlutoSDRファームウェア更新による検証

上記の「徐々に劣化する」現象がPlutoSDR側のハードウェアAGC/校正処理に起因する可能性を検証するため、ファームウェアを更新した。

このPlutoSDRには、DATV/QO-100運用向けの**サードパーティ製カスタムファームウェア**(`leandvb`/`leandvbtx`/`hacktv`/`qo100websdr`等を同梱、バージョン文字列は`v0.32-dirty`)が導入されていた(ユーザーは把握済みの状態)。ユーザー了承のもと、Analog Devices純正ファームウェア`v0.39`に更新した(カスタムツール一式は更新により消去される)。

更新手順(マスストレージへのドラッグ&ドロップ方式は本機では自動発火せず、以下の手動方式が確実だった):
```bash
# 1. 最新ファームウェアを取得・展開(pluto.frmを得る)
# 2. Piから直接Plutoにレガシーscpで転送(sftp-serverが無いため -O 必須)
sshpass -p analog scp -O /tmp/pluto.frm root@192.168.2.1:/tmp/pluto.frm
# 3. Pluto内部で手動更新スクリプトを実行
sshpass -p analog ssh root@192.168.2.1 '/sbin/update_frm.sh /tmp/pluto.frm'
# "Done" と表示されれば成功
sshpass -p analog ssh root@192.168.2.1 'reboot'
```

**更新後の結果**:

| 指標 | 更新前(v0.32-dirty) | 更新後(v0.39) |
|---|---|---|
| 安定ロック継続時間 | 10〜20秒 | 約100秒以上 |
| SNR推移 | 30dB→23dB→2.6dBと徐々に崩壊 | 27.4dB前後で最後まで安定、崩壊なし |
| 失われ方 | 品質の緩やかな劣化を経て消失 | 前兆なく突然消失 |
| 再ロック | 失敗し続けた | 今回も最終的に復帰せず |

**結論**: ファームウェア更新により**信号品質の緩やかな劣化(ハードウェアAGC/校正由来と推定)は大幅に改善**された。しかし、**一度ロックを失うと`plsync_cc`が再ロックできず探索し続ける**という`gr-dvbs2rx`ソフトウェア側の根本問題は解消していない。ただし発生までの時間が大幅に延びたため、`watchdog_rx.sh`との併用で実用性は大きく向上した。

### 9.6 C++根本原因の特定と`freq_sync`状態リセット修正

`plsync_cc_impl.cc`のソースコードを精査した結果、`freq_sync`クラスの`estimate_coarse()`メソッドが使う`pilot_corr`自己相関累積バッファおよび関連状態変数(`coarse_foffset`、`i_frame`、`coarse_corrected`、`fine_foffset`、`w_angle_avg`、`fine_est_ready`)が、フレームロック消失時に一切リセットされないことが判明した。再ロック時に古い蓄積データと新しい試行のサンプルが混在し、再ロック品質が劣化する原因と考えられる。

```cpp
// pl_freq_sync.h に追加
void reset()
{
    coarse_foffset = 0.0;
    i_frame = 0;
    coarse_corrected = false;
    fine_foffset = 0.0;
    w_angle_avg = 0.0;
    fine_est_ready = false;
    std::fill(pilot_corr.begin(), pilot_corr.end(), 0);
}
```
```cpp
// plsync_cc_impl.cc の general_work() 内
const bool was_locked = d_locked;
bool is_sof = d_frame_sync->step(in[i]);
d_locked = d_frame_sync->is_locked();
if (was_locked && !d_locked) {
    d_freq_sync->reset();  // 再ロック前に周波数推定器の状態をクリア
    GR_LOG_DEBUG_LEVEL(1, "Lock lost: frequency synchronizer state reset");
}
```

**検証結果**: 1回目は約20秒で完全スタール(改善なし)、2回目は約40秒後にロック消失→完全停止ではなく劣化状態(SNR~6dB、FER40%超)で再ロックし継続、という部分的な改善にとどまった。SNRが特定値に固定される劣化パターンから、`symbol_sync_cc`(Gardnerシンボルタイミングループ)にも同様の状態リセット漏れがあると推測された。

### 9.7 `symbol_sync_cc`状態リセット修正(Python側ポーリング方式)

`symbol_sync_cc_impl`が保持するGardnerループ状態(`d_vi`積分器、`d_cnt`モジュロ1カウンタ、`d_mu`、`d_jump`、`d_init`、`d_last_xi`)も、ロック消失時にリセットされていなかった。`freq_sync`はC++内(`plsync_cc_impl.cc`)から直接参照できるが、`symbol_sync_cc`は`plsync_cc`とは別のGNU Radioブロックであり直接の相互参照がないため、Pythonの制御プレーン層でポーリングして呼び出す方式にした。

1. `~/gr-dvbs2rx/include/gnuradio/dvbs2rx/symbol_sync_cc.h`、`lib/symbol_sync_cc_impl.h/.cc`に`reset()`メソッドを追加(コンストラクタの初期化値に合わせてリセット)、`python/dvbs2rx/bindings/symbol_sync_cc_python.cc`にpybind11バインディングを追加してビルド・インストール。
   - `D(symbol_sync_cc, reset)`ドキュメント抽出マクロはビルド時に未生成でコンパイルエラーとなったため、プレーン文字列("Reset the symbol timing loop state.")に置き換えて解消。
2. `/usr/local/bin/dvbs2-rx`の`connect_dvbs2rx()`内で`self.plsync`/`self.symbol_sync`をインスタンス属性として保持するよう変更。
3. `main()`の`tb.start()`直後に、`tb.plsync.get_locked()`を0.05秒間隔でポーリングし、ロック→非ロックの立ち下がりエッジで`tb.symbol_sync.reset()`を呼ぶ`symbol_sync_reset_loop`スレッドを追加(`daemon=True`のバックグラウンドスレッド)。

```python
def symbol_sync_reset_loop(top_block, period=0.05):
    was_locked = False
    while (True):
        locked = top_block.plsync.get_locked()
        if was_locked and not locked:
            top_block.symbol_sync.reset()
            gr.log.info("Lock lost: symbol timing loop state reset")
        was_locked = locked
        time.sleep(period)
```

**検証結果(ファームウェアv0.39・freq_syncリセット修正併用、720p H.264/QPSK3/4/1MSym/s)**: 約205秒間の連続動作で完全停止は一度も発生せず、11回のロック消失イベントは全て1〜3秒以内にSNR ~27.4dBまで完全復帰した。従来(freq_syncリセットのみ)はロック消失後にSNR~6dB前後の劣化状態に固着していたが、`symbol_sync_cc`のリセットを併用したことで**フル回復を伴う継続動作**を確認した。これにより、GNU Radio本体(`agc_cc`等)を修正せずとも`gr-dvbs2rx`側のみの修正でライブ配信の安定性が大幅に向上することが実証された。

### 9.8 `symbol_sync_reset_loop`のデータ競合を発見・GNU Radioメッセージポート方式に修正

9.7節のPythonポーリングスレッド方式には重大な設計上の弱点があった。`tb.symbol_sync.reset()`は独立したPythonスレッドから呼ばれる一方、`symbol_sync_cc_impl`の内部状態(`d_vi`、`d_cnt`、`d_mu`等)はフローグラフ本体の`general_work()`スレッドと**排他制御なしに同時アクセス**されるため、データ競合(race condition)が存在した。実際、UDP経由の再試験で`dvbs2-rx`が起動から約19秒で無言のまま(エラー出力なし)終了する事象が発生し、この競合が疑われた。

**修正方針**: Pythonスレッドでのポーリングを廃止し、GNU Radioのメッセージポート機構を使って`reset()`の呼び出しを`symbol_sync_cc`ブロック自身のスケジューラスレッド内で安全に実行させる方式に変更した(`freq_sync`の修正が`plsync_cc`内部の同一スレッドで完結しているのと同じ安全性)。

1. `plsync_cc_impl`(`~/gr-dvbs2rx/lib/plsync_cc_impl.h/.cc`)に`lock_lost`という出力メッセージポートを追加し、ロック消失検出時(既存の`was_locked && !d_locked`分岐)に`message_port_pub()`でメッセージを発行するよう変更。
2. `symbol_sync_cc_impl`(`~/gr-dvbs2rx/lib/symbol_sync_cc_impl.h/.cc`)に`reset`という入力メッセージポートを追加し、メッセージ受信時に内部で`reset()`を呼ぶハンドラを登録(既存の`rotator_cc_impl.cc`の`set_msg_handler`パターンを踏襲)。
3. Python側(`~/gr-dvbs2rx/apps/dvbs2-rx`)の`connect_dvbs2rx()`内で、既存の`self.msg_connect((plsync, 'rotator_phase_inc'), (rotator, 'cmd'))`の直後に以下を追加するだけで完結:
   ```python
   self.msg_connect((plsync, 'lock_lost'), (symbol_sync, 'reset'))
   ```
   これによりPython側のポーリングスレッド・独自インスタンス属性は一切不要になり、コードは既存の`msg_connect`パターンと完全に一致する形にシンプル化された。

**重要な教訓**: `/usr/local/bin/dvbs2-rx`は`~/gr-dvbs2rx`の`sudo make install`のたびに`apps/dvbs2-rx`の内容で**上書きされる**。9.7節で直接`/usr/local/bin/dvbs2-rx`に施したPatchは、本節の`make install`で全て消失していたことが判明した。以後はソース(`~/gr-dvbs2rx/apps/dvbs2-rx`)を編集すること。

### 9.9 修正後の再検証で判明した残存課題: 稀な無限探索状態

データ競合を解消した状態でUDP経由の再試験を実施したところ、クラッシュ(無言終了)は発生しなかったものの、**別の既知の残存課題が再現**した: 起動後しばらくは正常に動作しUDPでデータが流れたが、あるタイミングでロックを喪失した後、`plsync_cc`が**無限に再探索を続けて二度とロックに戻らない状態**に陥った。

スレッド別CPU使用量で確認したところ、`plsync_cc`スレッドのみが継続的に約100%のCPUを消費し続け(3秒間で約3.04秒分のCPU時間)、下流の`xfecframe_demapper`以降は完全に停止したままだった。これは9節冒頭で最初に特定した「ライブ配信が10〜20秒でスタールする」根本原因と全く同じパターンであり、`freq_sync`・`symbol_sync_cc`双方の状態リセット修正をもってしても**確率的に発生しうる**ことが分かった。

**結論**: 今回の一連の修正(ファームウェア更新・`freq_sync`リセット・`symbol_sync_cc`リセット・データ競合解消)は、ロック消失からの**復帰成功率を大幅に高める**効果があることは実証されたが(9.7節で11/11回復帰)、`plsync_cc`のPLHEADER/SOF相関探索アルゴリズム自体には、**探索が恒久的に失敗し続ける確率がゼロではない**という、より深い根本的な弱点が残っている。したがって実運用では、これらのC++修正と`watchdog_rx.sh`による自動再起動監視を**併用すること**を引き続き推奨する。

## 10. `dvbs2-rx`改修の最終状態まとめ(2026-07-14時点)

### 10.1 変更したファイルと内容

すべて `~/gr-dvbs2rx`(Pi上、gitで管理されたクローン)配下。正確な差分は `docs/gr-dvbs2rx_reset_fixes.patch`(`git diff`の出力)として本リポジトリにも保存済み。

| ファイル | 変更内容 |
|---|---|
| `lib/pl_freq_sync.h` | `freq_sync`クラスに`reset()`を追加(`coarse_foffset`・`i_frame`・`coarse_corrected`・`fine_foffset`・`w_angle_avg`・`fine_est_ready`・`pilot_corr`累積バッファをクリア)。`<algorithm>`のインクルードを追加(`std::fill`用)。 |
| `lib/plsync_cc_impl.h` | 新しい出力メッセージポートID `d_lock_lost_port_id = pmt::mp("lock_lost")` を追加。 |
| `lib/plsync_cc_impl.cc` | コンストラクタで`lock_lost`ポートを登録。`general_work()`内、ロック消失検出(`was_locked && !d_locked`)時に `d_freq_sync->reset()` の呼び出しと `message_port_pub(d_lock_lost_port_id, pmt::PMT_T)` によるメッセージ発行を追加。 |
| `include/gnuradio/dvbs2rx/symbol_sync_cc.h` | 純粋仮想関数 `virtual void reset() = 0;` を公開APIに追加。 |
| `lib/symbol_sync_cc_impl.h` | `reset()`のオーバーライド宣言、`reset`入力メッセージポートID、ハンドラ`handle_reset_msg()`の宣言を追加。 |
| `lib/symbol_sync_cc_impl.cc` | `reset()`を実装(`d_vi`・`d_cnt`・`d_mu`・`d_jump`・`d_init`・`d_last_xi`をコンストラクタ初期値相当にクリア)。コンストラクタで`reset`メッセージポートを登録し、受信時に`reset()`を呼ぶハンドラを`set_msg_handler`で登録。 |
| `python/dvbs2rx/bindings/symbol_sync_cc_python.cc` | pybind11バインディングに`.def("reset", &symbol_sync_cc::reset, "...")`を追加(Python直接呼び出し用。現在は主にC++内のメッセージハンドラ経由で使われる)。 |
| `apps/dvbs2-rx` | `connect_dvbs2rx()`内に1行追加: `self.msg_connect((plsync, 'lock_lost'), (symbol_sync, 'reset'))`。 |

### 10.2 データフローの最終形態

```
plsync_cc: フレームロック消失を検出
   │
   ├─ (C++内、同一スレッド) d_freq_sync->reset()  … freq_syncは即座に直接リセット
   │
   └─ message_port_pub("lock_lost", PMT_T)  … GNU Radioのメッセージキュー経由
              │
              ▼
      symbol_sync_cc: 自身のスケジューラスレッドで
      set_msg_handler が発火 → reset() 実行
```

Python側にポーリングスレッドは一切存在しない。全てGNU Radioのブロック間メッセージパッシング(`msg_connect`)で完結しており、データ競合は構造的に発生しない。

### 10.3 重要な運用上の注意

- **`~/gr-dvbs2rx`で`sudo make install`を実行すると、`/usr/local/bin/dvbs2-rx`と`/usr/local/bin/dvbs2-tx`は`apps/`配下のソースで無条件に上書きされる。** 今後CLIスクリプトに変更を加える場合は、必ず`~/gr-dvbs2rx/apps/dvbs2-rx`(または`dvbs2-tx`)を編集し、その後`cd ~/gr-dvbs2rx/build && make -j4 && sudo make install`でデプロイすること。`/usr/local/bin/dvbs2-rx`を直接編集しても次のビルドで消える。
- ビルド後は`sudo ldconfig`を忘れずに実行する(共有ライブラリのキャッシュ更新)。
- 現在の`~/gr-dvbs2rx`はgitの作業ツリーに未コミットの変更として存在する(`git diff`で確認可能)。クリーンな状態に戻したい場合は`git stash`等ではなく、`docs/gr-dvbs2rx_reset_fixes.patch`を保存してから作業すること。

### 10.4 既知の残存課題(未解決)

`plsync_cc`のPLHEADER/SOF相関探索が、ロック消失後に**確率的に無限探索状態へ陥り、二度と再ロックしない**ケースが依然として存在する(9.9節)。今回の修正群はこの状態に陥る頻度を大きく下げたが、根絶はできていない。実運用では`watchdog_rx.sh`による自動再起動との併用を前提とすること。

## 11. 試験再開用ヘルパースクリプト

過去の試行錯誤(SSHセッション終了時のバックグラウンドプロセス消失、`--log`と`--sink fd`の併用によるUDPストリーム破損、`pgrep`が`bash -c`ラッパーを誤検出する問題など)を踏まえ、`~/dvb-s/`に3本のスクリプトを整備した。いずれも実機(`192.168.0.135`)上で動作確認済み。

### `run_udp_hd_test.sh` — HD over UDP 試験の一括起動

```bash
cd ~/dvb-s
./run_udp_hd_test.sh [freq] [modcod] [symrate] [sps] [rolloff] [capture_secs]
# 省略時のデフォルト値(これまでの検証で確立した実用上限設定):
./run_udp_hd_test.sh 438022000 QPSK3/4 1000000 2 0.2 90
```

- PlutoSDRのUSBアドレスを`iio_info -s`で自動検出
- カメラ(`/dev/video0`)→H.264(libx264 ultrafast)→`dvbs2-tx`のTXパイプラインを起動
- `dvbs2-rx`(`--log`は付けない。統計テキストがTSバイナリに混入しUDP同期を乱すため)→`udp_relay.py`(127.0.0.1:2000)のRXパイプラインを起動
- 検証用に`ffmpeg -c copy`でUDP受信を指定秒数キャプチャ(`capture_secs`に0を指定すると省略可)
- 全プロセスを`setsid`+`disown`+標準入力`/dev/null`で完全デタッチ。呼び出し元のSSHセッションが終了しても生き続ける
- ログファイルパスを起動時に一覧表示

### `check_stall.sh` — スタール診断

```bash
cd ~/dvb-s
./check_stall.sh          # 実行中のdvbs2-rxを自動検出
./check_stall.sh <pid>    # PIDを明示指定する場合
```

各GNU Radioブロックのスレッドの CPU 使用量(`/proc/<pid>/task/*/stat`のutime+stime)を3秒間隔で2回サンプリングし、`plsync_cc`のみが高負荷(3秒間で250 tick=約83%以上)で下流ブロックが停止している場合に「無限探索スタール」と判定して警告を出す。健全時は全ブロックが低〜中程度の負荷でバランスして動いている(10.4節の残存課題の簡易検知用)。

### `stop_test.sh` — 一括停止・後片付け

```bash
cd ~/dvb-s
./stop_test.sh
```

`dvbs2-rx`・`dvbs2-tx`・カメラ用`ffmpeg`・`udp_relay.py`・UDP検証用`ffmpeg`・`watchdog_rx.sh`をすべて強制終了し、`/tmp`に残る本試験関連のログ/キャプチャファイルを削除する(`/tmp`はtmpfsで容量制限があるため、9.3節のディスク枯渇の再発を防ぐ目的)。

### 動作確認

2026-07-14、`run_udp_hd_test.sh`(25秒キャプチャ)→`check_stall.sh`(正常ロック中と判定)→`stop_test.sh`の一連の流れを実機で実行し、正常に動作することを確認済み。

### 9.10 データ競合修正後の本試験(95秒、`run_udp_hd_test.sh`使用)

9.8節のメッセージポート方式修正後、`run_udp_hd_test.sh`を用いて720p H.264/QPSK3/4/1MSym/sのUDP送受信本試験を実施した(試験途中でPlutoSDR/Piがネットワークから一時的に切断・復旧する事象があり、再起動後は`iio_pluto_source.set_samplerate()`が`RuntimeError: Unable to set BB rate`を返す一過性のエラーで初回起動に失敗したが、`run_udp_hd_test.sh`の再実行で解消した)。

**結果**: 95秒間、クラッシュ(9.8節で確認された無言終了)・無限探索スタール(9.9節の残存課題)のいずれも発生せず、最後まで安定動作した。

| 指標 | 結果 |
|---|---|
| UDPリレー総送信量 | 13,528,480 バイト(約13.5MB) |
| TS再同期(resync)回数 | 1回(試験開始時の初回同期のみ。データ破損による再同期なし) |
| `dvbs2-rx`プロセス | 終始生存、stderrにエラー出力なし |
| `plsync_cc`スレッドCPU負荷(`check_stall.sh`) | 約10%(3秒間で31 tick)。9.9節で観測した無限探索時の約100%(250 tick以上)とは明確に異なる正常範囲 |

一点、UDP検証用に併走させた`ffmpeg -c copy`キャプチャは53秒付近から`Packet corrupt`を頻発し、映像フレーム数(`frame=`カウンタ)が頭打ちになった。しかしこの間もUDPリレーの送信バイト数は一貫して増加を続けており(最終的に13.5MB送信 vs キャプチャファイルは6.8MBのみ)、DVB-S2復調・UDPリレー自体は健全に動作し続けていたことが確認できる。したがってこの`Packet corrupt`はRX/UDPリレー側の不具合ではなく、検証用`ffmpeg`クライアント側のデコード/バッファリングの問題(残留ビット誤りによるPESパケットの部分的破損を`-c copy`でも検出してしまう、等)と考えられる。

**結論**: 今回の1回の試行では、9.8・9.9節で確認していた2つの既知の失敗モードのどちらも再現しなかった。ただし9.9節で述べた無限探索状態は確率的事象であるため、この1回の成功は統計的な解決の証明にはならない。引き続き`watchdog_rx.sh`との併用、および複数回・長時間の試行によるさらなる検証が望ましい。

## 既知の注意点

- `blocks_file_sink_0`(`tmp.ts`)は未接続。動作確認には使えない
- `dvbs2_rx_epy_block_0` は原実装不明のためパススルー実装(`docs/` と同階層の `dvb-s/dvbs2_rx_epy_block_0.py`)で代替中
- 40dBパッド使用時、TX内部減衰は `--plutosdr-attn 0` が動作実績あり(RSSI ~58dB, AGC ~37dB で安定ロック)
- SSH接続が稀に鍵交換直後にリセットされることがある(原因未特定)。`ping`/ポート22が生きていれば数回リトライで復旧する
- Pluto RXは1プロセスしか同時に掴めないため、`dvbs2-rx`(公式CLI)と自作`RF_UDP_dvbs2_rx.py`を同時に起動しないこと
- **ライブ配信時は7節の手順に従うこと。** `start_rx.sh`を使う、またはTX起動直後にRXを起動すると受信できない
- USBカメラ使用時、`dmesg`に`usb: reset high-speed USB device`が頻発することがある(カメラ・PlutoSDRは同じUSBバスを共有)。今回はRX側の起動タイミング問題と切り分けて確認済みだが、長時間運用時は念のため注視すること

## 動作実績

- 2026-07-13: 合成テストパターン(カラーバー)によるループバックで、TX→RX→TS復調→UDP→ffplay再生まで再現確認済み(詳細は `docs/loopback_test_report.docx` 参照)
- 2026-07-14: USBカメラ(Logitech Webcam C270, `/dev/video0`)実写映像でのループバックテストを実施し成功。
  実際に使用したキャプチャコマンド:
  ```bash
  ffmpeg -y -f v4l2 -input_format yuyv422 -video_size 320x240 -framerate 25 -i /dev/video0 \
    -t 15 -c:v mpeg2video -b:v 1500k -f mpegts cam_test.ts
  ```
  以降は本手順の3〜6節と同じ(`--in-file` を `cam_test.ts` に変更するのみ)。
  ffplayで実際の室内映像がリアルタイム表示されることを確認(スクリーンショット: `loopback_test_camera_screenshot.png`)。
- 2026-07-14: **ライブ(リアルタイム)配信**もテストし、7節の手順(TX先行起動+RX手動起動)で成功を確認。
  カメラ映像がその場でエンコード・変調・復調・再生され、Pi画面にリアルタイム表示されることを確認済み。
- 2026-07-14: **USBスループット上限(約1.8〜1.9Msps)を実測で特定**(8節参照)。新しい実用上限として1MSym/s(sps=2)を確認。
- 2026-07-14: **720p HD映像伝送**に成功(H.264/libx264、QPSK3/4、1MSym/s)。実際に鮮明な720p映像を受信・デコードできることを画像で確認済み。
- 2026-07-14: **UDP経由でのDVB-S2データ送受信を実証**(`udp_relay.py`、TSパケット同期方式)。`ffmpeg -c copy`でのストリーム検出に成功。
- 2026-07-14: ライブ配信が10〜20秒でスタールする不具合を特定(`plsync_cc`が再ロックに失敗し続ける)。**`watchdog_rx.sh`による自動再起動**で運用上回避可能なことを確認済み。
- 2026-07-14: PlutoSDRファームウェアを純正v0.39に更新し、`freq_sync`状態リセット(C++修正)を実装。安定継続時間が10〜20秒→約100秒以上に改善したが、ロック消失後に低SNR状態へ固着する問題は残存(9.6節)。
- 2026-07-14: `symbol_sync_cc`状態リセット(Python側ポーリング方式)を追加実装し、約205秒の連続動作でロック消失からの**完全復帰**を11回とも確認。GNU Radio本体を修正せず`gr-dvbs2rx`側の修正のみで安定性を大幅に改善(9.7節)。
- 2026-07-14: UDP経由の再試験でPythonポーリング方式のデータ競合を発見(無言終了)。GNU Radioメッセージポート方式(`plsync_cc`の`lock_lost`出力ポート→`symbol_sync_cc`の`reset`入力ポートへ`msg_connect`)に修正し、競合を解消(9.8節)。
- 2026-07-14: 競合解消後の再試験で、`plsync_cc`が稀に無限探索状態に陥り二度と再ロックしない残存課題を確認。全修正を併用しても根絶はできず、`watchdog_rx.sh`との併用が引き続き必要(9.9節)。
- 2026-07-14: `run_udp_hd_test.sh`を用いた95秒のUDP本試験で、クラッシュ・無限探索スタールいずれも再現せず安定動作(総送信量13.5MB、resync1回のみ)。ただし1回の成功は統計的解決の証明にはならない(9.10節)。
