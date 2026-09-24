# Pi4実機PlutoSDRブリングアップ 調査報告書

作成日: 2026-08-09
対象: `pi4/rx/shonan_rx.py`(gr-dvbs2rx RX)+ `pi4/src/tx_main.cpp`(aff3ct TX)、
      同一PlutoSDR上でのTX→40dBアッテネータ→RXループバック試験

## 追記(2026-08-20): PL-syncロック不安定・映像デコード失敗の原因と恒久対策

### 現象
40dBアッテネータでのRFループバック試験で、RXが`locked=True`/`False`を
頻繁に繰り返し(以前は約50%の頻度で瞬断)、映像が0フレームしかデコード
できない事象が発生した。RXゲイン(45〜65dB手動/AGC)を振っても改善せず、
Pi4側送出のリアルタイム優先度(`chrt`)・`-muxrate`指定でも変化なし。

### 根本原因1: Pluto+上の`tsp`受信バッファが小さすぎる
`/root/udpts.sh`内の`tsp -r --buffer-size-mb 0.01`(=10KB)がPlutoの
Zynq(非力なARMコア)上でUDP受信→analyze/pcrextractプラグイン→
`pluto_dvb`へのパイプ、という処理チェーンに対して小さすぎ、内部で
詰まってPL-sync自体を不安定にしていた。**`0.2`(200KB)に拡大したところ
ロックがほぼ完全に安定した**(locked=True比率が劇的に改善)。
併せてtsp `-I ip`側のUDPソケット受信バッファも`--buffer-size 4194304`
(4MB)に拡大した(input側の受信キュー溢れ対策、ロック安定への寄与は
buffer-size-mbほど大きくないが実害はないため残置)。

### 根本原因2: 手動テストコマンドの`pkt_size`欠落(実機GUIには影響なし)
上記対策後もRXは安定ロックしたが映像は依然0フレームだった。原因は
**手動SSHテストで使っていたffmpeg TXコマンドに`?pkt_size=1316`が
付いていなかった**ため(実機の`backend.py`の`_build_udp_ts_url()`は
最初から`pkt_size=1316`付きで送信しており、この問題を元々抱えていない)。
`pkt_size=1316`を付けた途端に映像デコードが成功した(実機GUIでも
カラーバー映像の表示を確認済み)。**Pi4/Pi5間の違いではなく、調査時の
手動テストスクリプトの不備だった**と判断できる。

### 永続化の落とし穴: Plutoのルートファイルシステムは再起動でリセットされる
このPlutoSDR機はルートファイルシステムが`rootfs`(RAM上)で、
`/root`・`/etc`配下は電源断/再起動のたびに出荷時状態へ完全リセットされる。
`/etc/init.d/S89patchfirm`が毎起動時に唯一の永続化フラッシュ領域
`/mnt/jffs2/patch.zip`を`/`へ自動展開する仕組みが元々用意されていたが、
`patch.zip`自体が存在しなかったため機能していなかった。
**上記の`udpts.sh`修正(buffer-size-mb/UDPバッファ拡大)は
`root/udpts.sh`として`/mnt/jffs2/patch.zip`に格納し、再起動後も
自動再適用されることを確認済み。**

同様に`/www/settings.txt`(周波数/シンボルレート等のDVB-S2パラメータ)も
再起動でリセットされるが、こちらは**GUI側`TxController.start()`が
送信開始のたびに`_push_pluto_settings()`で毎回再送信する既存動作の
ため、追加対応は不要**(手動SSHテスト時のみ都度手動POSTが必要)。

### 検討したが見送った変更
- `rtmppluto.sh`(Android版が実際に使うRTMP経路、`RTMPTxController.kt`
  参照)は、Pi4/Pi5では未使用と誤認して一時無効化したが、**同一Pluto
  実機をAndroid版で使う際に支障が出るため再度有効化した**(CPU負荷は
  待受時0%で実害がないため、無効化するメリット自体がなかった)。
  複数プラットフォームで同一Pluto実機を共用する場合、片方専用の
  最適化のつもりで他方の経路を無効化しないよう注意すること。
- `pluto_dvb -L`(バッファ待機時間、既定400ms)を2000msへ拡大する案は
  効果が確認できなかったため見送り、400msのまま。

### 再発防止のポイント
- Pluto実機の設定変更(`/root/*.sh`, `/etc/init.d/*`)を行う際は、
  必ず`/mnt/jffs2/patch.zip`(`root/...`, `etc/...`の相対パス構成)に
  反映してから再起動で永続化を検証すること。ライブ編集のみで
  満足すると次回再起動で消える。
- 手動SSHでのTXテストでは`pkt_size=1316`を必ず付与すること
  (`udp://<host>:8282?pkt_size=1316`)。付け忘れると実機では
  発生しない映像破損を誤診断する。
- 複数プラットフォーム(Pi4/Pi5/Android)で同一Pluto実機を共用する
  前提を忘れず、片方の都合だけで起動スクリプトの経路を無効化しない。

## 追記(2026-08-09、同日6回目セッション追加3): パイロット有無も明確な傾向なし

ユーザーから「Android版ではパイロット信号はどうなっているか」の指摘を受け確認。
**`rtmppluto.sh`(Pluto+側、Android版が実際に使う経路)の`pluto_dvb`起動行には
`-p`フラグが一切存在しない=Android版の本番経路はパイロット信号OFFで動作している**
ことが判明した(それまでのRF検証テストは一貫してパイロットON`-p`/`--pilots`で
実施していた、報告書内の「rtmppluto.shの実際のpluto_dvb起動行」参照)。

パイロットOFF(`-p`なし・RX側`--no-pilots`、frame_len=32490)で同条件のRF
ループバック試験を実施したところ、**49件(22秒間)** — パイロットON時の
baseline(52件)とほぼ同水準だった。`errors=0`(パイロットON時は24〜164件)と
パケット単位のデータ整合性は改善したが、**周期的なロック喪失自体の頻度は
パイロット有無で変わらなかった**。

**まとめ(更新): calib_mode、RXトラッキングキャリブレーション、`pluto_dvb -q`、
unlock_thresh、TXデータ生成方法、TX/RXゲイン、パイロット有無のいずれも、
1.4秒周期のロック瞬断の原因ではないか、効果が限定的と切り分けが完了した。
Android版との設定差異(パイロット)を解消しても瞬断自体は解消しなかったため、
「Android版で問題が起きないのはパイロット設定の違いのため」という仮説も
否定された。**

---

## 追記(2026-08-09、同日6回目セッション追加2): TX/RXゲインの組み合わせも明確な傾向なし

ユーザーから「送受信のゲイン設定は影響していないか」の指摘を受け検証。ループバック
(TX SMA→40dBアッテネータ→RX SMA)構成で、TXゲイン(`-g`)とRXゲイン
(`--gain-db`)の組み合わせを振り、22秒間のロック喪失イベント数を比較した。

| TXゲイン | RXゲイン | ロック喪失イベント数 | 備考 |
|---|---|---|---|
| 0dB(既定・最大出力) | 60dB(既定) | 52件 | baseline |
| -10dB | 60dB | 58件 | |
| -20dB | 60dB | 43件 | |
| -40dB | 60dB | (ロック自体不成立) | 信号が弱すぎてmetricが閾値付近(42〜43)まで低下、SN比不足による別の失敗モード |
| 0dB | 40dB | 48件 | |

`-40dB`のような極端な減衰では信号強度不足で別の失敗モード(ロック不成立)になるが、
それ以外の組み合わせ(0/-10/-20dB × 40/60dB)は**43〜58件の狭いレンジに収まり、
単調な傾向が見られなかった**。これは、これまで確認してきた試行ごとの自然な
ばらつきの範囲内である可能性が高く、TX/RXゲインの調整では明確な改善は
得られないと判断した。ただし相関検出の`metric`値自体はAGC非依存に正規化
されているため(`pl_frame_sync.cc`参照)、信号レベルの変化を直接読み取る
指標としては使えない点に注意。

**まとめ: calib_mode、RXトラッキングキャリブレーション、`pluto_dvb -q`、
unlock_thresh、TXデータ生成方法(ライブ/静的)、TX/RXゲインの組み合わせの
いずれも、1.4秒周期のロック瞬断の決定的な原因ではないか、効果が限定的と
切り分けが完了した。実機で試せる現実的な選択肢はほぼ尽きたと考えられる。**

---

## 追記(2026-08-09、同日6回目セッション追加): TXデータ(ライブエンコード)は原因ではないと確定

ユーザーからの「TXデータの問題ではなかったのか」という指摘を受け、それまでの
RF系再検証が全てffmpegによる**ライブエンコード**(testsrc→libx264リアルタイム
変換)をTXソースに使っていたことに気づいた。エンコーダ自身のタイミング揺らぎ
(キーフレーム挿入・CBR fillerの挙動等)が原因である可能性を切り分けていなかった。

**検証: 事前に20秒分のTSファイルを1回だけ生成し(`-c:v libx264 ... /tmp/static_test.ts`)、
それを`ffmpeg -re -stream_loop -1 -i static_test.ts -c copy`で再エンコードなし・
実時間ペーシングのみでループ再生してpluto_dvbへ送信した。**

結果: **52件のロック喪失(22秒間)** — ライブエンコード時(55〜72件)とほぼ同水準。
**TXデータ生成方法(ライブエンコード有無)を変えても瞬断の頻度は変わらないことが
確定した。TXデータの内容・生成タイミングは原因ではない。**

これにより、原因は「ライブエンコードの揺らぎ」ではなく、より低レベルな要因
(RFフロントエンド・AD9361チップ内部・pluto_dvb変調プロセス自体の何らかの周期動作)
にあることがさらに裏付けられた。

---

## 追記(2026-08-09、同日6回目セッション): unlock_thresh実験も効果なし

「今後の課題」①(1.4秒周期のPLロック瞬断)の調査を再開。`gr-dvbs2rx`の
`pl_frame_sync`の`unlock_thresh`(既定3、`plsync_cc_impl.cc`で
`new frame_sync(debug_level)`と呼ばれ明示指定なし=既定値のまま使われている
ことを確認)を6に引き上げてリビルドし、同一セッション内で3と6を直接比較した。

| unlock_thresh | ロック喪失イベント数(22秒間) |
|---|---|
| 6 | 55件 |
| 3(既定) | 72件 |

閾値を上げるとやや減る(3→6でおよそ24%減)ものの、大きな改善にはならなかった。
これは基礎となるRF振幅ドロップアウト(生IQダンプで確認済み)自体が、6シンボル
分の連続ミスでも吸収しきれないほど長く/頻繁に発生していることを示唆する。
実験後はunlock_threshを既定値3に復元済み。

**AD9361の全デバイス属性(`iio_attr -d ad9361-phy`)も再確認したが
(`dcxo_tune_*`, `ensm_mode`, `gain_table_config`, `rssi_gain_step_error`,
`trx_rate_governor`等)、新たな有力な手がかりは見つからなかった。
`ensm_mode`には`pinctrl_fdd_indep`という別のFDD動作モードが存在するが、
実機を壊すリスクがあるため未検証のまま。**

**現時点の結論: calib_mode・RXトラッキングキャリブレーション・`pluto_dvb -q`
フラグ・unlock_thresh・AD9361属性一式のいずれも原因ではないか、効果が
限定的と切り分けが完了した。生IQダンプで実際のRF振幅ドロップアウトが
存在することは実証済みだが、その発生源はソフトウェア側の設定調整では
到達できない領域(AD9361チップ内部の非公開動作、FDD運用時のRFフロントエンドの
物理的な制約等)にある可能性が高い。次の一手として現実的なのは、
`pinctrl_fdd_indep`モードの慎重な検証、またはこの問題を「既知の制約」として
一旦棚上げし、Pi4のCPU実時間マージン確認など他の項目に移ることだと考えられる。**

---

## 追記(2026-08-09、同日5回目セッション): SSH直接パイプを廃止しRTMP方式へ

**下記「4回目セッション」で導入したSSH直接パイプ方式(`ffmpeg | ssh ... pluto_dvb`)は
廃止し、shonan-android版RTMPTxController.ktと全く同じRTMP方式に切り替えた。**
カメラ+音声診断で長時間悩まされたUnderflowの真因が判明したため。

### 真因判明の経緯

ユーザーから「Android版は同じPlutoでpluto_dvbを使っているのに問題ないのはなぜか」
という指摘を受け、Android版のTX実装(`RTMPTxController.kt`)を調査した。
結果、**Android版はSSHを一切使わずRTMPで
Pluto+上の`rtmppluto.sh`(常駐RTMP受信デーモン、`/etc/init.d/S90datv`起点)へ
プッシュしている**ことが判明。SSH方式ではpluto_dvbの標準入力が直接ネットワークに
晒されるのに対し、RTMP方式ではPluto上の頑丈なffmpeg(rtmppluto.sh)がネットワークの
揺らぎを吸収し、pluto_dvb自体はPluto内部のローカルパイプからしかデータを受け取らない
構造になっている。

実機調査の結果、以下が判明した:

1. **`rtmppluto.sh`は実際には機能する。** 過去のセッションで「このPlutoのffmpegには
   `"match up:"`という文字列が存在しない」と結論していたが、これは誤りだった。
   `"match up:"`はPluto独自パッチではなく、標準的なRTMPプロトコルの警告メッセージ
   `"App field don't match up: <値> <-> "`の一部で、実際に存在する。
2. **原因はFEC値に含まれる`/`だった。** DVB-S2パラメータはRTMP接続URLのパス部分
   (例: `rtmp://host:7272/,437,DVBS2,QPSK,1500,3/5,-40,nocalib,800,64,,`)に
   カンマ区切りで埋め込まれ、`rtmppluto.sh`はffmpegの上記警告メッセージに
   そのパス全体がエコーされる挙動を利用してパラメータを取り出す。しかしFEC値を
   `"3/5"`のようにスラッシュ付きで書くと、RTMPのapp/playpath区切り(`/`)と衝突し
   パラメータが分断される。Android版は`FECRate.plutoParameter`でスラッシュを
   除いた表記(`"3/5"`→`"35"`)を使っており、これが回避策になっていた。
3. **カメラ+音声診断のUnderflowの主因は、単純なビットレート不足だった。**
   `pluto_dvb -m DVBS2 -c QPSK -s 1500000 -f 3/5 -d`のdry-run出力で確認したところ、
   このシンボルレート/変調方式構成が要求する実ネットビットレートは約
   **1,782,456bps(≈1.78Mbps)**。旧診断機能の映像800kbps+音声64kbps≈864kbpsは
   これを大きく下回っており、慢性的なUnderflowの直接原因だった。通常送信
   (`start()`)は既に1.9Mbps程度を供給していたため問題が起きていなかった。
4. RTMP方式でも、テスト間でログファイルをクリアせずに累積カウントを見ていたために
   誤って「大量のUnderflowが残っている」と誤診した場面があった。ログを都度クリアし
   十分なビットレートで計測し直すと、**2回連続で0 Underflowを確認**できた。

### 実装

- `pi4/gui/backend.py`: `TxController`を全面書き換え。SSH関連コード(sshpass、
  リモートpluto_dvbのkillall等)を全て削除し、ffmpegを`setsid bash -c "..."`経由
  ではなく**直接QProcessで起動**(`-f flv rtmp://<pluto>:7272/,...`へプッシュ)する
  シンプルな構成にした。これによりプロセスグループ管理(setsid/os.killpg)も
  不要になった(ffmpeg単一プロセスなのでQProcess.terminate()がそのまま効く)。
  Pluto側のpluto_dvbライフサイクルは`rtmppluto.sh`が自律管理するため、Pi4側から
  リモートプロセスを気にする必要が一切なくなった。
  - ステータス判定: RTMP方式ではPluto側のUnderflow等がPi4から見えなくなる
    (Android版も同様の制約)ため、`status_updated`は`{"connected": bool}`のみに
    簡略化。ffmpeg自身の進捗行(`frame=...`)の出現を"connected"とみなす。
  - ウォッチドッグ再接続を追加: Android版のコメントに「Pluto+側RTMP受信が
    接続後20〜30秒程度で自発的に切断する」既知の挙動が記載されていたため、
    `stop()`が呼ばれていないのにffmpegプロセスが終了したら0.5秒後に自動的に
    再起動する仕組みを追加(RxControllerの既存ウォッチドッグと同様の設計)。
  - カメラ+音声診断のビットレートを800k/64k→symbol_rate_hzに比例した値
    (既定1.9Mbps程度)に引き上げ。
- `pi4/gui/screens/testequipment.py`/`tx.py`: `underflow_count`を参照する箇所を
  全て削除し、`connected`のみで健全性判定するよう簡略化。

### 実機検証結果

`start()`(映像のみ)・`start_camera_audio()`(カメラ+音声)とも、実機eglfs上で
`TxController`を通して複数回実行し、いずれも`connected=True`・エラーなしで
安定動作を確認した。Pluto側も`rtmppluto.sh`のループが正しく待受状態へ戻ることを
確認済み(孤児プロセスなし)。

**注意: `rtmppluto.sh`はPluto+の`/etc/init.d/S90datv`起点で起動する常駐サービス。
本セッション中に調査のため手動で何度も停止・再起動したため、既に正規の起動方法
(`/root/rtmppluto.sh >/dev/null </dev/null 2>/dev/null &`)で復旧済みだが、
Pluto+を再起動すれば通常通り自動起動する。**

---

## 追記(2026-08-09、同日4回目セッション): TX経路をaff3ctからpluto_dvbへ切り替え

**GUIのTX経路を、下記「解決」節で実証済みの`pluto_dvb`(Pluto内蔵変調器、SSH経由)を
正式経路とするよう変更した。理由: `pluto_dvb`は単独でDVB-S2符号化・変調まで完結する
独立したモジュレータであり、aff3ctが行っていた符号化+変調を丸ごと代替できる
(むしろこちらが実証済みの経路)。shonan-android版の実績あるTXパスも元々
`pluto_dvb`を使っており、Pi4版のaff3ct実装(未解決のBBHEADER CRC8不具合を抱えたまま)
の方が他の兄弟プロジェクトとは異なる独自路線だった。旧`shonan_tx`(aff3ct、
`pi4/src/tx_main.cpp`)・`run_tx.sh`はソースを削除せずGUIからの呼び出しのみ停止した
(手動CLI利用や将来の参照用に残す)。**

### 変更内容

- `pi4/gui/backend.py`: `TxController.start()`/`start_camera_audio()`を
  `run_tx.sh`(aff3ct)経由から`ffmpeg | sshpass ssh root@Pluto 'pluto_dvb ...'`
  (SSHパイプ)経由に変更。ステータス判定もaff3ct固有の`starved`/`dmaRms`から、
  pluto_dvbの出力(`PlutoDVB Init`等の起動バナー検出=`connected`、`Underflow`行の
  カウント)ベースに変更。
- `pi4/gui/settings_store.py`: `bandwidth_hz`/`rf_port`/`runtime_dir`は
  pluto_dvbが使わないため削除(GUI設定・streamoutput.py画面からも撤去)。
  `sample_rate_hz`の既定値を`1_500_000`→`3_000_000`に変更(実IQサンプルレート、
  symbol_rate=sample_rate_hz/2としてpluto_dvbの`-s`へ渡す。3.0Msps=symbol_rate
  1.5Msym/sは実機で繰り返し検証済みの値)。
- `pi4/gui/screens/testequipment.py`/`tx.py`: TX単体診断・カメラ+音声診断の
  健全性判定を`connected`かつ累積`underflow_count`が増えていないことに変更。
- `pi4/rx/shonan_rx.py`: CLI既定値を`pluto_dvb`向け(`--framesize normal`
  `--rolloff 0.35` `--sample-rate-hz 3000000`)に変更(旧aff3ct向けの
  `short`/`0.20`から)。

### 実機検証: 通常送信は解決、カメラ+音声診断は原因不明のまま残存

**通常送信(`start()`、映像のみ。testsrcまたは実カメラ、音声キャプチャなし)は
QProcess経由・実機eglfsで繰り返し`underflow_count=0`を確認**、問題なし。

**カメラ+音声同時キャプチャの診断(`start_camera_audio()`)のみ、QProcess経由だと
断続的にUnderflow(100〜160件/10秒程度)が発生する現象が残っている。** 生の
`ffmpeg | ssh ... pluto_dvb`をPi4上でbashスクリプトとして直接実行すると
毎回`Underflow=0`で安定するのに対し、全く同じコマンドをPyQt5の`QProcess`から
起動すると高頻度でUnderflowが発生する、という差が繰り返し確認された。

以下を切り分けたが、**いずれも決定的な原因ではなかった**:

- `QProcess`が既定でstdinを開いたパイプのままにする問題
  (`setStandardInputFile(QProcess.nullDevice())`で対策、単体切り分けでは
  効果があったがTxController全体に組み込むと再現)
- `status_updated`/`log_line`シグナルの発行自体(スロット未接続でも`emit()`する
  こと自体が悪影響、という切り分け結果が単体テストでは複数回再現したが、
  TxControllerへ組み込んで`quiet_mode`(シグナルを一切発行せずポーリングのみ)に
  変更しても解消しなかった)
- `refresh_camera_audio_frame_counts()`のログファイル全読み込み
  (差分読み込みに変更、さらに完全に呼ばないパターンでも試したが変化なし)
- `pluto_dvb`出力を`QProcess`のstdout(`2>&1`)へ合流させていたのをやめ、
  ffmpegログと同様ファイルへ落としてポーリングする方式に変更(有力な仮説
  だったが、実装後の実機検証でも改善しなかった)
- Pluto側の孤児プロセス(`stop()`がリモートのpluto_dvbを確実に終了できて
  おらず、`ps aux`で最大6個の`pluto_dvb`が同時残存していたことを発見。
  `killall pluto_dvb`による同期クリーンアップをTX開始時・非同期クリーンアップを
  停止時に追加。これ自体は実在する重大なバグで修正済みだが、完全クリーンな
  状態から実行してもUnderflowは再現した)
- USB Audio(C920 PRO)のカーネルレベルのサンプルレート不整合警告
  (`dmesg`に`current rate 16000 is different from the runtime rate 32000`
  `cannot set freq 32000 to ep 0x82`が多数記録されているのを発見、USBデバイスを
  unbind/rebindでリセットしたが変化なし)
- `QtWidgets.QApplication`(実機eglfs、カーソル管理あり)と`QtCore.QCoreApplication`
  (ヘッドレス)の違い(どちらでも再現)

**最終的に、「0件を安定して再現していたはずの最小テストスクリプト」自体が、
コード変更なしに同一セッション内で0件→150件に振れることを確認し、
これまでの「コードの違いが原因」という切り分け結果の少なくとも一部が
セッション中の環境/ハードウェア側の変動(時間経過・連続試験による劣化等)と
たまたま相関していただけだった可能性が高いと判断し、この方向のコード調査は
打ち切った。**

**この過程で実装した以下の修正は、原因の全容解明には至らなかったものの、
いずれも独立して正当な改善であり保持する**: stdinの明示的nullDevice化、
Pluto側孤児プロセスの確実なクリーンアップ(TX開始時の同期killall+停止時の
非同期killall)、カメラ+音声診断のシグナル発行をやめポーリング方式にした
`quiet_mode`アーキテクチャ、ffmpeg/pluto_dvb両ログの差分読み込み化。

### 次回セッションで検討すべきこと

1. カメラ+音声診断のUnderflowが真に環境要因(熱・USB劣化・電源等)なのか、
   長時間・複数回の反復試行(統計的手法)で再現性を検証する。
2. USB Audio(C920 PRO)のカーネル警告(`cannot set freq 32000 to ep 0x82`)が
   実際の音声キャプチャ品質に影響しているか、専用の切り分け試験を行う。
3. 診断機能自体の必要性を見直す(通常送信は健全なので、カメラ+音声の
   同時キャプチャという診断シナリオ自体が実運用よりも過酷すぎる可能性がある)。

**現状(2026-08-09更新): `gr-dvbs2rx`(RX)自体は完全に正しいことを実機で証明済み
(Pluto内蔵変調器`pluto_dvb`との組み合わせでTSパケット抽出・エラー0件まで到達)。
一方、`shonan_tx`(aff3ct)をTXに使った場合はBBHEADER(CRC8)以降でデータが壊れ、
TSパケット出力に至らない。原因は`gr-dvbs2rx`ではなく`aff3ct`側にある可能性が
極めて高いところまで切り分けられた(詳細は「解決: gr-dvbs2rxの正しさをPluto内蔵
変調器で実証」節を参照)。**

---

## クイックスタート(次回セッション用)

### 実機の現在の状態(2026-08-09セッション終了時点)

- Pi4の`shonan-gui.service`は**通常稼働に復元済み**(タッチGUIが使える状態)。
  今回のセッション中は表示テストのため一時停止していたが、再開している。
- Pluto上の`pluto_dvb`テスト送信は**停止済み**。`rtmppluto.sh`由来の壊れた
  待ち受けプロセス(PID 1059/1144/30080相当、無害・パラメータ空)が残っている
  可能性があるが、実害はないので放置してよい。
- `~/gr-dvbs2rx`(Pi実機)のビルド・インストールは完了済みの状態
  (`pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch`の内容が反映済み)。
  Pi実機を再起動しても`/usr/local/lib/`にインストール済みの`.so`はそのまま
  残るため、**再ビルドは不要**(`~/gr-dvbs2rx`のワークツリー自体を作り直した
  場合のみ、上記パッチを再適用してビルドし直すこと)。
- `~/shonan-pi4/pi4/rx/shonan_rx.py`はこのリポジトリの最新版と同一
  (`--framesize`/`--pilots`オプション反映済み)。

### 最後に成功した検証手順の再現(pluto_dvbリファレンスTX経由)

```sh
# 1. Pi4からSSH(パスワード: raspberry、鍵認証は使わずパスワード認証で)
ssh pi@192.168.0.142
# (毎回 -o PreferredAuthentications=password -o PubkeyAuthentication=no
#  を付けないと鍵認証の試行で固まることがある。sshpass -p raspberry推奨)

# 2. shonan-gui.serviceが起動中なら一旦停止(画面を使う場合)
sudo systemctl stop shonan-gui.service

# 3. Pluto側でpluto_dvbを起動(SSH経由でTSを直接パイプ、rtmppluto.shは使わない)
#    ffmpegはPi4側で実行し、パイプの先でPlutoへSSHログイン(root/analog)して
#    pluto_dvbへ渡す。カメラ映像を使う場合:
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -tune zerolatency \
  -x264-params nal-hrd=cbr:force-cfr=1 -b:v 1.9M -maxrate 1.9M -bufsize 1.9M \
  -g 15 -pix_fmt yuv420p -f mpegts -muxrate 1900k -mpegts_flags +resend_headers - | \
  ssh root@192.168.2.1 "/root/pluto_dvb -s 1500000 -f 3/5 -m DVBS2 -c QPSK -p \
  -t 437000000 -g 0 -L 800 -T 8"
# (Pluto側ログイン: root/analog。-pでパイロット有効化必須。
#  nal-hrd=cbr+muxrateを付けないとUnderflowが発生するので必須)

# 4. 別ターミナル(またはPi4上の別セッション)でRX起動
python3 ~/shonan-pi4/pi4/rx/shonan_rx.py --pluto-uri ip:192.168.2.1 \
  --lo-hz 437000000 --sample-rate-hz 3000000 --mod-cod QPSK-S_3/5 \
  --framesize normal --pilots --rolloff 0.35 --no-agc --gain-db 60 \
  --output-fifo /tmp/rx.ts --status-interval-sec 2
# (sample-rate-hzはシンボルレート1.5Msym/sの2倍=3000000であること、
#  rolloffは0.35固定、gain-dbは60が反復的に最も安定)

# 5. 作業終了後はGUIサービスを再開しておく
sudo systemctl start shonan-gui.service
```

**期待される結果**: `locked=True`が断続的に出つつ`frame`/`packets`が
着実に増加、`errors`は0〜数十件程度(実行ごとに変動、詳細は
「pluto_dvb経路での映像品質改善」節参照)。約1.4秒周期で一瞬
`locked=False`に戻るのは既知の制約で、映像自体は表示可能
(視覚確認済み)。

### 次にやること(優先順)

1. ~~1.4秒周期のロック瞬断の原因調査(calib_mode manual実験)~~ →
   **2026-08-09追記: calib_mode=manualは逆効果、RX側トラッキングキャリブレーション
   無効化・`pluto_dvb -q 0`明示指定もいずれも効果なしと判明(いずれも
   実機で切り分け済み)。生IQダンプで実際のRF振幅ドロップアウトが存在する
   ことは確認済みだが、AD9361キャリブレーション周りでは説明できなかった。
   `manual_tx_quad`への自動遷移(pluto_dvb起動時に無条件発生)が本当に
   関係あるのか、それとも無関係な副産物なのか未確定のまま。次はpluto_dvb
   ソース自体の確認、またはこの方向性を打ち切ってaff3ct側TX精査へ切り替える
   ことを検討(下記「追記」節参照)。**
2. aff3ct側TX(`shonan_tx`)のBBHEADER/スクランブラ関連コード精査

---

## 追記(2026-08-09、同日後続セッション): Pluto接続がUSB→LANに変更・新規リグレッションと対処

**重要: 本セッション中にPlutoの接続方式がUSB直結(192.168.2.1)から
LAN経由(192.168.0.136、Pi4と同一eth0セグメント)に変更された。
TX SMA→40dBアッテネータ→RX SMAの物理ループバックは同一Pluto上で従前通り
接続されたまま。以降のクイックスタート手順は`--pluto-uri ip:192.168.0.136`
に読み替えること。**

### 新規リグレッション: LAN接続化でPLロックが一度も成立しなくなっていた

上記「クイックスタート」の手順をLAN接続後に再現したところ、SOF相関自体は
健全(metric≈53、閾値42を安定して上回る)にもかかわらず、`found`状態のまま
一度も`locked`に遷移しなくなっていた(旧USB接続時は安定してlocked可能だった)。

**原因: `gr-iio`の`fmcomms2_source_fc32`のIIOバッファサイズ(`0x8000`=32768
サンプル)がLAN経由の読み出しには小さすぎ、毎秒10回近くバッファオーバーフロー
(gr-iioが無改行で出す`O`マーカーがログに混入して発覚)していた。** USB-CDC-ECM
直結時はこの頻度でも問題なかったが、実Ethernet経由になったことで読み出し
オーバーヘッドが増え、サンプル取りこぼしが頻発しPLフレーム境界のシンボル
カウントが同期しなくなっていた。

**対処(コミット済み)**: `pi4/rx/shonan_rx.py`のバッファサイズを`0x8000`→
`0x40000`(262144サンプル)に拡大。これによりオーバーフロー頻度が大幅に減り、
`locked=True`への到達・複数フレーム連続デコードが再び可能になった
(ただし完全に0件にはならず、後述の1.4秒周期問題は残存)。

### 除外できた仮説: `[fsdbg]`デバッグ計装のオーバーヘッド

`pl_frame_sync.cc`の`[fsdbg]`(is_peak時に毎秒9〜10回発火するfprintf)を
一時的に無効化してリビルドしても、オーバーフロー頻度・ロック不能症状は
一切改善しなかった。**計装のオーバーヘッドが原因ではないと確定**、その後
`[fsdbg]`は復元済み(現在のビルドに反映済み)。

### 【重要・危険】calib_mode=manualはpluto_dvb自体を壊す(この方向性は放棄)

上記バッファサイズ修正後、当初の最優先課題だった「1.4秒周期のロック瞬断」の
原因調査として`ad9361-phy`の`calib_mode`を`auto`→`manual`に切り替えて
比較実験を行った。結果:

- `calib_mode=manual`にした状態で`pluto_dvb`を起動すると、TX側で
  `Underflow`カウンタが特定の値(例: 2784, 3876)に固着したまま
  進まなくなり、最終的に**`Plutodvb exiting..`で異常終了**した。
  RX側もSOF相関が一度も検出されない(`sof=0`のまま)状態になった。
- **`calib_mode`を`auto`に書き戻すだけでは復旧しなかった**(AD9361の
  ドライバは`auto`書き込み時に即座に再校正をトリガーするわけではない
  ため、キャリブレーション状態が壊れたまま残る)。
- **Plutoの`reboot`で完全復旧を確認**(起動後`calib_mode=auto`、
  `pluto_dvb`正常起動、`locked=True`まで到達)。

**結論: `calib_mode=manual`への切り替えは1.4秒周期問題の解決策ではなく、
むしろTXチェーン自体を破壊する。実機実験としてはこの1回で十分な証拠が
得られたため、この仮説は放棄する。**

### 生IQダンプでの波形観測: 実際のRFレベル振幅ドロップアウトを確認

`pl_frame_sync.cc`の`[unlockdbg]`ログにエポックms単位の絶対時刻(`t_ms`)を追加、
`shonan_rx.py`に`symbol_sync_cc`出力(plsync_ccへの直接入力、シンボルレート
1.5Msym/s)を生complex64でファイルへ記録する`--raw-iq-dump`オプションを一時的に
追加して(共に未コミットの一時計装)、アンロック発生時刻付近の波形を直接観測した。

**結果: 記録した5件のアンロックイベント全てで、該当時刻付近(±100ms窓)に
振幅(RMS)が中央値の約1%まで落ち込む区間が存在することを確認した
(dip_ratio≈0.01、全件で一致)。** これはソフトウェア/タイミング側の
問題(バーストで処理が遅延して見かけ上ロックが飛ぶ等)ではなく、**実際に
RF信号のパワーが一瞬失われている**ことを示す直接証拠であり、
「RF/AD9361チップレベルの周期性を疑う」という当初の仮説の方向性自体は
正しかったことが実機データで裏付けられた(ただし対処法としての
`calib_mode=manual`は誤りだった、という点が上記の教訓)。

### 有力な原因候補: pluto_dvbによるAD9361の自動TX直交(quadrature)再校正

上記振幅ドロップアウトの原因調査中、`pluto_dvb`を一度でも起動すると、
**明示的に触っていないにもかかわらず`ad9361-phy`の`calib_mode`が
`auto`から`manual_tx_quad`へ勝手に遷移している**ことに気づいた
(`iio_attr`で複数回再現確認)。これは`pluto_dvb`(またはその配下の
AD9361ドライバ)が動作中に**TX直交キャリブレーションを自発的に実行し、
完了後の状態を`calib_mode`に残している**ことを示唆する。

`pluto_dvb --help`には`-q {0,1} 0:Use a calibration file 1:Process
calibration (!HF peak!)`というオプションが存在し(未指定時の既定値は
未検証)、"!HF peak!"という警告文言から、有効時にRF較正用のテスト信号
(高周波ピーク)を実際に送出する動作である可能性が高い。ただし今回の
全試験で`-q`は一度も明示指定していないため、この特定のCLIオプションが
直接の引き金かどうかは未確認(既定動作の可能性、あるいはAD9361ドライバの
バックグラウンドtracking calibration機能が`pluto_dvb`の初期化と独立に
働いている可能性も残る)。Pluto上に既存の較正ファイルは見つからなかった
(`find / -iname '*calib*'`で該当ファイルなし)。

**2026-08-09追記(同日3回目セッション): 上記1・2を実施、いずれも効果なしと判明**

- **RX側トラッキングキャリブレーション3種の無効化(`quadrature_tracking_en`/
  `rf_dc_offset_tracking_en`/`bb_dc_offset_tracking_en`を`voltage0`(入力)
  チャンネルで`0`に設定)**: `calib_mode=manual`のような破壊的な影響は一切なく
  安全に切り替えられたが、`unlockdbg`件数は有効時(78件/22秒)→無効時
  (78件/22秒)と**完全に同数**。RX側トラッキングは原因ではないと確定。
- **`pluto_dvb -q 0`明示指定**: 3回試行(18件/22秒、0件/接続断で無効試行、
  150件/22秒)し、結果は有効時と同程度〜それ以上に大きくばらついた
  (既知の「同一設定でも試行ごとに大きくばらつく」現象の範囲内と判断)。
  さらに重要な点として、**`-q 0`を指定してもTX起動後の`calib_mode`は
  やはり`manual_tx_quad`へ自動遷移する**ことを確認した。つまり`-q`フラグは
  この遷移の発生条件ではない(常に発生する、`pluto_dvb`起動シーケンスに
  組み込まれた無条件の一回限りの校正と見られる)。
- **副次的に判明した既知の挙動**: `iio_attr`で`ad9361-phy`の`calib_mode`
  属性へ書き込む(`auto`書き込みも含む)と、直後の数秒間Plutoのiiodが
  一時的に無応答になることがある(ping自体は生きている場合が多く、
  ネットワーク断ではなくiiod/AD9361ドライバ側の処理待ちと見られる)。
  次回セッションでスクリプトから`iio_attr`を呼ぶ際は、書き込み直後に
  十分な待機時間を入れること。

**結論: RX側トラッキングキャリブレーション・`pluto_dvb -q`フラグのいずれも
原因ではないと切り分けられた。`manual_tx_quad`への自動遷移自体は
`pluto_dvb`起動時に無条件で発生する既知の副作用であり、これが本当に
アンロックの直接原因なのか、単に無害な副産物なのかは依然未確定。**

**残る次回セッションでの候補**:
1. pluto_dvbのソース(`fmc_perfom_calibration`/`bandwidth_calibrating`という
   シンボルがバイナリ内に存在することを確認済み)が公開されていれば、
   周期的な再校正のトリガー条件を直接確認する。

### 実機の状態(このセッション終了時点)

- Plutoは`calib_mode=auto`・`ip:192.168.0.136`で正常動作確認済み。
- `~/gr-dvbs2rx`の`pl_frame_sync.cc`は`[unlockdbg]`にt_ms(絶対時刻)を追加した
  状態でビルド・インストール済み(一時計装、`fsdbg`同様に問題解決後に
  削除すること。`pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch`は
  未更新なので、次回セッションでこの追加分も含めてエクスポートし直すこと)。
- `pi4/rx/shonan_rx.py`のIIOバッファサイズ拡大(`0x40000`)はリポジトリに
  コミット済み。Pi実機側も同期済み。`--raw-iq-dump`オプション付きの
  一時コピー(`/tmp/shonan_rx_iqdump.py`)は削除済み・未コミット
  (再度波形観測する場合は本節の記述を参考に作り直すこと)。
- `shonan-gui.service`は通常稼働に復元済み。
- テスト用一時スクリプト・ログ・生IQダンプファイル(`/tmp/rf_test*`,
  `/tmp/rf_iqdump*`)は削除済み。

---

## ハードウェア構成

- Pi4 + PlutoSDR無印(Pluto+ではない)、F5OEO製DATVカスタムファームウェア(`datvplutofrm` v0.32-dirty)
- TX SMA出力 → 40dBアッテネータ → RX SMA入力 のケーブル自己ループバック
- 周波数: 437MHz(カスタムLO設定)、帯域幅1.2MHz、サンプルレート1.5Msps
- Mod-Cod: `QPSK-S_3/5`(実体はDVB-S2 Short FECFRAME、後述)
- 映像ソース: Logicool C920 PRO(USB UVCカメラ、`/dev/video0`)
- TX送信パワー: 0dB(最大出力、アッテネータ側で減衰)
- RXゲイン: 手動55dB固定(**AGC OFF必須**、後述)

## 再現・試験コマンド

```sh
# TX(GUI外、手動起動する場合)
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v 1.5M -maxrate 1.5M -bufsize 1.5M -g 15 -pix_fmt yuv420p -f mpegts \
  -mpegts_flags +resend_headers - | \
  /home/pi/shonan-pi4/pi4/scripts/run_tx.sh --pluto-uri ip:192.168.2.1 \
  --lo-hz 437000000 --bandwidth-hz 1200000 --sample-rate-hz 1500000 \
  --mod-cod QPSK-S_3/5 --rf-port A_BALANCED --tx-power-db 0.0 --tmp-dir /tmp

# RX(GUI外、手動起動する場合。--agcは絶対に付けないこと、後述)
python3 ~/shonan-pi4/pi4/rx/shonan_rx.py --pluto-uri ip:192.168.2.1 \
  --lo-hz 437000000 --sample-rate-hz 1500000 --mod-cod QPSK-S_3/5 \
  --no-agc --gain-db 55 --output-fifo /tmp/rx.ts --status-interval-sec 1
```

ステータス行 `[shonan_rx] locked=... sof=... frame=... rejected=... freq_off=... packets=... errors=...`
で状態を確認する。

---

## 修正済みの実バグ

### 1. gr-dvbs2rxのビルド済み修正が一度もインストールされていなかった

`~/gr-dvbs2rx`(third-party、`igorauad/gr-dvbs2rx`のクローン)に、PLSフィルタ誤検出を直す
未コミットのソース修正が存在していたが、`sudo make install`が一度も実行されておらず、
システムにインストールされた`.so`は修正前のまま(ビルド時刻とインストール済み`.so`の
mtimeを比較して発覚)。`make install`を実行して解消。

**教訓: `~/gr-dvbs2rx/build`でビルド成功しても、`sudo make install`を忘れると
`/usr/local/lib/aarch64-linux-gnu/libgnuradio-dvbs2rx.so.*`は更新されない。**

### 2. AGC使用時にsymbol_sync_ccがSIGSEGV

Pluto内蔵AGC(`slow_attack`)使用時、ゲイン変動により`symbol_sync_cc`のタイミング
補間ループ(`polyphase_interpolator::operator()`、`loop()`内のW1/W2/d_jump計算)が
不安定化し、バッファ範囲外アクセスでクラッシュする。

**回避策(必須)**: RXは必ず`--no-agc --gain-db <値>`で起動すること。`--agc`は使わない。

根本修正として、`portsdown5-ipad`(同じユーザーの別プロジェクト、iOS版・同じ
gr-dvbs2rxライブラリ使用)の実機ブリングアップで見つかっていた修正パッチ
(`docs/patches/gr-dvbs2rx_ios_real_pluto_bringup.patch`)を`~/gr-dvbs2rx/lib/symbol_sync_cc_impl.cc`
に移植済み(`idx_subfilt`のクランプ、W1/W2の正値クランプ、`d_jump`の`[1,4*sps]`クランプ)。

### 3. PLSフィルタのしきい値が振幅非正規化のまま

`pl_frame_sync.cc`のSOF/PLSC相関に使う差分値`diff`が、AGC/ゲインの実スケールに
直接依存する未正規化の値のまま、振幅非依存であるべき固定しきい値
(`threshold_u`/`threshold_l`)と比較されていた。これも上記iOS版で解決済みの
問題で、同じ修正を移植:

- `diff`を単位振幅に正規化(`pl_frame_sync.cc`)
- found状態(ロック確認待ち)のゲート条件を`is_locked()`単体から`is_locked_or_almost()`
  (found or locked)に変更 — found状態のまま毎シンボル相関計算し続けていたバグ
- しきい値を`30/25`→`42/36`に引き上げ(`pl_frame_sync.h`)

移植前は誤検出が秒間数十万〜100万回のオーダーで発生していたが、この修正で
解消(正常な相関ピークのみが検出されるようになった)。

### 4. 【最重要・本セッションで新規発見】RXのPLS想定が実際のTX出力と不一致

`shonan_rx.py`は「Normal FECFRAME(64800bit)・パイロットなし」を前提に
`dvbs2rx.dvbs2_pls(mod, rate, "normal", False)`を呼んでいたが、実際のTX
(`aff3ct`の`DVBS2.hpp`、`N_ldpc=16200`)は**QPSK-S_3/5に対して常にShort
FECFRAME(16200bit)・パイロット付き**で送信する(`aff3ct`側にオン/オフの
選択肢は存在せず、コードレートによって固定)。

正しいPLS値は以下で確認済み:

```python
from gnuradio import dvbs2rx
target_pls = dvbs2rx.dvbs2_pls("QPSK", "3/5", "short", True)  # => 23
```

真のPLFRAME長は8370シンボル(RXが誤って想定していた32490ではない)。
この不一致のせいで、PL相関自体は強く成立する(相関値50台後半、理論最大値57に近い)
にもかかわらず、found→locked遷移に必要な「次のSOFがちょうど1フレーム後に来る」
という条件が絶対に成立せず、**一度も真のロックに到達できなかった**。

`shonan_rx.py`側の修正(コミット済み):
```python
framesize = dvbs2rx.FECFRAME_SHORT  # 旧: FECFRAME_NORMAL
target_pls = dvbs2rx.dvbs2_pls(pls_const_str, pls_code_str, "short", True)  # 旧: "normal", False
```

この修正により、`locked=True`が安定して継続し、`frame`カウンタが理論値に近い
速度(~85fps)で増加するようになった。**PLフレーム同期はこれで実用上完全に解決**。

### 5. TXのUSBカメラが物理的に故障していた

古いカメラ(`046d:0825`)が`ioctl(VIDIOC_DQBUF): No such device`で1フレームも
取得できず、TX入力映像がほぼ空(`throughput=0.07Mbps`程度)のまま、TXリング
バッファが慢性的に`starved=100%`になっていた。これがPLロックが数十〜百数十
フレームごとに一瞬外れる不安定性の直接原因だった(TXが実際に送信データを
欠落させていたため)。

**C920 PRO(`046d:08e5`)に交換して解決**。交換後は`starved=0%`が継続し、
RXのPLロックも(#4の修正と合わせて)ほぼ完全に安定した。

### 6. RXウォッチドッグの追加

`pi4/gui/backend.py`の`RxController`に、`frame`カウンタが8秒間進まなければ
RXプロセスを自動再起動するウォッチドッグを追加(shonan-android版
`RxController.kt`のロック状態ポーリングの考え方を参考にしつつ、あちらには
なかった「実際に再起動する」動作を追加。Android版はUIフラグ更新のみで
プロセス再起動はしない)。

---

## BBHEADER CRC8が(aff3ct TX使用時のみ)常に失敗する問題

PLロックが完全に安定した状態(`locked=True`継続、`frame`が理論値通り増加)でも、
`aff3ct`(`shonan_tx`)をTXに使うと`bbdeheader.get_packet_count()`は**一度も
増加しない**(TSパケットが1つも出力されない)。

### 確認できている事実

- LDPCは高速に収束(`get_average_trials()`は12〜14回、最大試行回数よりずっと少ない)
  → 信号品質自体は良好で、LDPCレベルでは大きな破綻はないと考えられる
- BCHのエラーカウント(`bch_decoder.get_error_count()`)は緩やかに増加する程度で、
  致命的なレベルではない
- `bbdescrambler`から`bbdeheader`への入力バイト数は着実に増加している
  (`nitems_written`/`nitems_read`で確認、データは実際に流れている)
- BBHEADER CRC8成功回数は、**純粋なランダム一致で期待される回数
  (試行回数 ÷ 256)とほぼ一致**(3399フレーム中11回成功、期待値13.3回)。
  つまり「まれに成功している」のではなく、実質**常に失敗している**とみなすべき

### 除外できた仮説(すべて独立に検証済み)

| 仮説 | 検証方法 | 結果 |
|---|---|---|
| FECパラメータ(K_bch/N_bch/t)の不一致 | `aff3ct`の`DVBS2.cpp`と`gr-dvbs2rx`の`fec_params.cc`を直接比較 | **完全一致**(K=9552, N=9720, t=12) |
| BBスクランブラのアルゴリズム/シード不一致 | 両実装のLFSR構造を手動で数学的に照合(インデックス逆順で同型と証明) | **同一の系列を生成することを確認** |
| BBスクランブラのC++実装バグ | Pythonでクリーンルーム再実装し、C++が出力した生バイトに対して独立にデスクランブル+CRC8計算 | **C++と完全に同じ結果**(実装バグではない) |
| LDPCの`output_mode`設定ミス | `OM_MESSAGE`(情報ビットのみ出力)を確認 | **正しい設定** |
| インターリーバの有無不一致 | `aff3ct`の`build_itl_core()`を確認 | QPSK-S_3/5は`Interleaver_core_NO`(無効)と確定、**問題なし** |
| ビット/バイトのシフトミスアライメント | 生バイト列に対し0〜127ビットの全シフトを総当たりでCRC8検証 | 各サンプルで異なる(66bit, 88bitなど)シフト位置でしか成功せず、**固定ズレではなく偶然の一致と判定** |
| ビット反転(LLR符号反転) | 生バイトをビット単位で反転してCRC8検証 | **成功なし** |
| バイト内ビット順反転(MSB/LSB逆) | 各バイトのビット順を反転してCRC8検証 | **成功なし** |

## 解決: gr-dvbs2rxの正しさをPluto内蔵変調器(pluto_dvb)で実証

上記の「除外できた仮説」を一通り潰した後、**shonan-android版の送信は
`aff3ct`ではなくPlutoのオンボード変調デーモン(`pluto_dvb`)を使っている**
ことに気づいた(`RTMPTxController.kt`のコメントで確認: 「機器試験機能の
LibiioSession/aff3ctとは完全に独立」)。つまりshonan-android側で実績が
あるのは「Pluto内蔵変調器 + gr-dvbs2rx RX」の組み合わせであり、
「`aff3ct` + gr-dvbs2rx RX」はこのユーザーの過去プロジェクトでも
**一度も実証されたことがない、今回が初めての組み合わせ**だった。

### rtmppluto.shのRTMP経由制御は機能しない(既知の欠陥)

Pluto内蔵の`/root/rtmppluto.sh`は、RTMPの正式なメタデータではなく
**ffmpeg自身が出す"match up:"という診断警告文をgrepしてDVB-S2パラメータを
抽出する**という特殊な仕組みだが、このPlutoのffmpeg(v4.3.1、
`--disable-librtmp`でビルド)にはその文字列が存在しない
(`strings`で確認、外部`librtmp`ライブラリの冗長ログ出力に依存した仕組みで、
ffmpeg自前のRTMP実装ではそもそも生成されない)。そのためRTMP接続自体は
成功しても、変調パラメータが全て空(`pluto_dvb -m -c -s 000 -f -d`)のまま
起動してしまい、意味のある信号が出ない。

**回避策**: `pluto_dvb`は標準入力から直接TSを受け取れる独立したバイナリ
なので、`rtmppluto.sh`を経由せず**SSH経由でTSを直接パイプ**する:

```sh
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -tune zerolatency \
  -b:v 2.2M -maxrate 2.2M -bufsize 2.2M -g 15 -pix_fmt yuv420p -f mpegts \
  -mpegts_flags +resend_headers - | \
  ssh root@192.168.2.1 "/root/pluto_dvb -s 1500000 -f 3/5 -m DVBS2 -c QPSK -p \
  -t 437000000 -g 0 -L 800 -T 8"
```
(Pluto側SSHログイン: `root`/`analog`。`-p`でパイロット有効化。映像
ビットレートは`pluto_dvb`が要求するTS帯域(この設定で約1.78Mbps、起動時に
`Net TS bitrate input should be ...`とログ表示される)以上にしないと
null packetでの穴埋め(`Underflow`ログ)が増える。)

### pluto_dvbの実際の変調パラメータ(aff3ctとの相違点)

`pluto_dvb --help`と実機ログ(`Bandwidrh LPF = 2025000`等)から特定:

| 項目 | aff3ct(shonan_tx) | pluto_dvb(Pluto内蔵、`-v`/`-p`未指定時) |
|---|---|---|
| FECFRAME長 | Short(16200bit、選択肢なし) | **Normal**(64800bit、既定) |
| パイロット | 常に付加(選択肢なし) | **既定は無効**、`-p`で有効化可能 |
| ロールオフ | 0.20(aff3ct既定値) | **0.35固定** |
| サンプルレート/シンボルレート比 | 2倍(sps=2固定) | 2倍(`Upsample=2`、同じ) |

### 実機検証結果

`pluto_dvb`を上記コマンドで起動し、`shonan_rx.py`を
`--framesize normal --pilots --rolloff 0.35 --sample-rate-hz 3000000`
(シンボルレート1.5Msym/sの2倍)で起動したところ:

- `-p`なし(パイロット無効): 20秒で`packets=478`、`errors=42`
- `-p`あり(パイロット有効、RX側`--pilots`は既定でON): 20秒で
  `packets=478`、**`errors=0`**

**TSパケットが継続的に、ほぼエラーなしで抽出できることを確認**(2分以上の
連続実行でも`packets`が977まで安定して増加、`errors`は42のみ)。これにより
`gr-dvbs2rx`側(symbol_sync_cc、pl_frame_sync、plsync_cc、xfecframe_demapper、
ldpc_decoder、bch_decoder、bbdescrambler、bbdeheaderの全チェーン)が
正しく実装・設定されていることが実証された。**BBHEADER CRC8の失敗は
`gr-dvbs2rx`のバグではなく、`aff3ct`側TXの何らかの非互換が原因である
可能性が極めて高い。**

### shonan_rx.pyへの反映(コミット済み)

TXの実装(aff3ct/pluto_dvb)を切り替えられるよう、以下をCLI引数化した
(それまでは`aff3ct`前提でハードコードされていた):

```sh
--framesize {short,normal}   # 既定: short(shonan_tx向け)
--pilots / --no-pilots       # 既定: --pilots(shonan_tx向け)
--rolloff                    # 既存。pluto_dvb向けには0.35を明示指定
```

### 残っている仮説(aff3ct側TXに絞り込み、次回セッションで着手すべき候補)

gr-dvbs2rxが実証されたことで、以前の仮説1・2(demapperのLLR規約、LDPCの
誤収束)は**同一のgr-dvbs2rxコードで実際に正しく動作することが確認された
ため事実上除外**された。残るは仮説3のみ:

1. **aff3ct側TXの非標準的な挙動**。`aff3ct`は元々研究・教育用ライブラリであり、
   市販DVB-S2変調器や他のオープンソース実装(Pluto内蔵変調デーモン等)
   ほど広く相互接続検証されていない。BBHEADER生成やスクランブラ適用範囲
   (BBHEADER自体もスクランブル対象に含めているか等)に規格からの逸脱が
   ないか、`aff3ct`のFramerモジュールのソースを直接読む必要がある
   (`~/shonan-pi4-native-build/.build-tmp-dvbs2/dvbs2/src/common/Module/Framer/`)。

2. 生IQダンプ(`blocks::file_sink`で`xfecframe_demapper`直前の出力を保存)を
   取得し、aff3ct TX出力とpluto_dvb TX出力を直接比較する(既にgr-dvbs2rx側の
   正しさは実証済みなので、比較対象を用意すれば差分から原因を絞り込める)。

### 一時的なデバッグ計装(残存)

以下は`~/gr-dvbs2rx`(Pi実機、`git diff`で確認可能)に残っている一時的な
`fprintf`計装。実害はないが、問題解決後にまとめて削除すること。

- `lib/pl_frame_sync.cc`: `[fsdbg]`(ピーク検出時のsym_cnt/metric/state)、
  `[unlockdbg]`(アンロック時のmetric推移)
- `lib/bbdeheader_bb_impl.cc`: `[bbhdbg]`(BBHEADER CRC8の成功/失敗と先頭バイト)
- `lib/bbdescrambler_bb_impl.cc`: `[descdbg2]`(デスクランブル前の生バイト、
  48バイト分)
- `pi4/rx/shonan_rx.py`: `[flowdbg]`(ブロック間アイテム流量)、`[fecdbg]`
  (LDPC平均試行回数・BCHエラー数)— こちらはコミット済み

**注意**: `~/gr-dvbs2rx`はgitリポジトリだが、リモートは`igorauad/gr-dvbs2rx`
(本家)のため、ここへの変更は**ローカルコミットのみ**(プッシュ不可/不適切)。
全変更(上記#2・#3の恒久修正 + 本節の一時デバッグ計装)は
`pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch`にエクスポート済み
(`git -C ~/gr-dvbs2rx diff`の出力そのまま)。新しく`~/gr-dvbs2rx`をクローン
し直した場合は、このパッチを適用してから再ビルドすること:

```sh
cd ~/gr-dvbs2rx
git apply /home/pi/shonan-pi4/pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch
cd build
make -j4 gnuradio-dvbs2rx
sudo make install
```

---

## pluto_dvb経路での映像品質改善(TX Underflow解消・RXゲイン最適化)

`pluto_dvb`をリファレンスTXとして実際に映像を表示できることを確認した後、
映像品質を安定させるための調整を行った。

### TX側: Underflow(Null Packet埋め)の解消

`pluto_dvb`は要求TSビットレート(この設定で約1.74Mbps)を下回ると
`Underflow : N Filling Null Packet`ログを出し続ける。原因はffmpeg
(`libx264`、`ultrafast`+`tune zerolatency`)の実測ビットレートが
**1166kbps**(目標2.2Mbpsの約53%)しか出ていなかったこと。カメラ映像が
暗く静止気味のシーンのため、CBRレート制御でも`filler=0`(x264既定)により
コンテンツに必要な分のビットしか使われず、目標に届いていなかった。

**修正**: `-x264-params nal-hrd=cbr:force-cfr=1`を追加してfillerを
強制的に有効化し、`-f mpegts -muxrate 1900k`でTS層のペーシングも明示。
実測ビットレートが**1850〜1862kbps**に安定し、要求値(1.74Mbps)を
常時上回るようになった結果、**Underflowログが完全に消えた**(30秒以上の
連続実行で0件)。

### RX側: ゲイン最適化

55dBから45/50/60/65dBまで振って比較した結果、**60dB**が最も安定して
`errors=0`を再現できた(複数回の20〜30秒試験で確認)。ただし実行ごとに
0〜149件までの変動があり、ゲイン単体では完全には安定しない(下記の
パケット欠落調査を参照)。

### 残る問題: TS連続性ギャップ(パケット欠落)とPLロックの周期的な瞬断の相関

`bbdeheader`のパケット単位CRC(`errors`カウンタ)が0でも、実際にはTS
`continuity_counter`にギャップがあり(1145パケット中53箇所、約4.6%)、
これがH.264デコード失敗(`Decode error rate 1 exceeds maximum`)の
直接原因だった。CRCは個々のパケットの破損は検知できるが、パケットが
**丸ごと欠落する**ケースは検知できないため、これまで見えていなかった。

`[unlockdbg]`計装でPLロックの瞬断を計測したところ、20秒間に
**正確に14回の完全なアンロック→再ロックサイクル**(約1.4秒に1回の
規則的な周期)が発生しており、TS連続性ギャップ数(51箇所/20秒)と
オーダーが一致した。ロック中の相関値は理論値付近(56前後)なのに、
アンロック時は4〜12まで完全に相関が失われる(緩やかな劣化ではなく
突発的な喪失)。

### 追加検証(同日): SSH・ペーシング・パラメータの切り分け

以下をすべて個別に検証したが、**いずれも1.4秒周期のアンロックを
解消しなかった**:

| 検証内容 | 手法 | 結果(20秒間のunlockdbgイベント数) |
|---|---|---|
| 基準(SSH経由、ライブ映像) | `ffmpeg`(Pi4)→SSHパイプ→`pluto_dvb`(Pluto) | 42件 |
| SSH排除(ペーシングなし) | `while true; do cat clip.ts; done`をPluto上でローカル実行 | 45件(**同等、SSHは無関係と判明**) |
| `-L`(バッファレイテンシ)200msに短縮 | 同上+`-L 200` | 18件(改善したが後述の通り再現性に疑問) |
| `-L`を100msにさらに短縮 | 同上+`-L 100` | 33件(**200msより悪化、単純な線形関係ではない**) |
| `freq_est_period`を30→10に短縮 | `shonan_rx.py`の`plsync_cc`引数変更 | 12件(誤差範囲の可能性) |
| **SSH排除+正しい実時間ペーシング** | Pluto上で`ffmpeg -re`により実時間再生速度に補正 | 30件/25秒(≒24件/20秒換算、**やはり同等〜やや改善程度**) |

最後の「正しいペーシング」検証が特に重要: 当初のSSH排除テストは
`cat`でファイルを一気に流し込んでおり(実時間再生速度を無視した
バースト転送)、公平な比較になっていなかった。`ffmpeg -re`で実時間
ペーシングを復元しても結果は変わらなかったため、**SSH・転送方式・
ペーシングの不備はいずれも主因ではないと結論**できる。

`-L`や`freq_est_period`のパラメータ実験は、同一設定でも試行ごとに
大きくばらつく(例: gain=60dB固定でもerrorsが0〜176件まで変動する
ことを既に確認済み)ため、単発試行だけでは因果関係を確定できない。
反復試行による統計的な検証が必要。

**現時点の結論**: 原因はソフトウェア設定(SSH、バッファ、ペーシング、
plsync_ccの各種パラメータ)よりも、**単一Pluto上でTX/RXを同時動作
させるループバック構成自体に内在する、より根本的な要因**(RF/AD9361
チップレベルの周期的な挙動等)を疑うべき段階に来ている。

### 次回セッションで着手すべき候補

1. **RF/ハードウェアレベルの周期性調査**（最優先）。
   `iio_attr`でAD9361の`calib_mode`(現状`auto`)を`manual`に固定して
   自動キャリブレーションが周期性の原因か確認する。TX/RXが同一チップの
   同時動作(FDD)であることに起因する内部スケジューリングも疑う。
2. 生IQダンプ(`blocks::file_sink`)でアンロック発生の瞬間を波形レベルで
   直接観測し、振幅・位相にどのような変化が起きているか確認する。
3. `d_unlock_thresh`(既定3)を増やす実験(副作用として真のロック喪失の
   検知が遅れる点に注意)。
4. `-L`/`freq_est_period`のパラメータ実験を反復試行(各設定で5回以上)
   して統計的に有意な傾向があるか再検証する。
5. TS連続性ギャップを`shonan_rx.py`の`[flowdbg]`系統に恒常的な診断
   として組み込み、今後のチューニングで定量的に追跡できるようにする。

---

## 既知の制約

### 単一PlutoのTX/RX同時動作時に発生するPLロック瞬断

同一PlutoSDR上でTXとRXを同時動作させ、40dBアッテネータでループバックする
構成では、約1.4秒周期のPLロック瞬断が発生する。生IQ観測でRF振幅の
ドロップアウトを確認しており、SSH転送、RTMP方式、ペーシング、ゲイン、
パイロット、`calib_mode`、`unlock_thresh`等のソフトウェア設定変更では
決定的な改善を得られなかった。

この現象は、現在の簡易機器試験では合否対象外とできる一方、製品品質上は
**最優先で対策すべき未解決問題**である。単一PlutoでTX/RXを同時動作させる
ループバック構成の既知の再現現象として、追加調査を継続する。

## 今後の課題

**2026-08-09（簡易機器試験の整理後）時点の状況整理:**

- **約1.4秒周期のPLロック瞬断の原因特定**（最優先、未解決）。
  簡易機器試験では合否対象外とするが、製品品質上は対策完了まで残存課題とする。
- ~~aff3ct側TXのBBHEADER/スクランブラ関連コードの精査~~ →
  **TX経路をpluto_dvb(RTMP方式)へ正式移行しGUIからaff3ctを呼ばなくなった
  ため、優先度低下(ユーザー向け機能への影響がなくなった)**
- ~~aff3ct TX出力とpluto_dvb TX出力の生IQ比較~~ → 同上、優先度低下
- 一時デバッグ計装の削除（既知の制約の追加調査時に必要となるため保留。`gr-dvbs2rx`側は
  `pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch`参照)
- Pi4のCPU性能の実時間マージン確認(理論最大フレームレート約90fpsに対し、
  実測は概ね近いが余裕は大きくない可能性、**未着手**)
- ~~`rtmppluto.sh`の"match up:"抽出修正 or SSH直接パイプの正式化~~ →
  **解決済み。`rtmppluto.sh`自体は正常動作しており、原因はGUI側のURL
  エンコード(FEC値のスラッシュ)とカメラ+音声診断のビットレート不足だった。
  RTMP方式を正式なTX経路として採用した(5回目セッション追記参照)。**
