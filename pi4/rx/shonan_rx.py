#!/usr/bin/env python3
"""shonan_rx -- Pi4ネイティブDVB-S2 RXフローグラフ。

GNU Radioフローグラフ構成をPythonで実装したもの。aff3ctベースのRX
(dvbs2_rx_lib.cpp)は実機で一度もフレーム同期に成功したことがない既知の不具合が
あるため採用せず、「実証済みの動作方式」であるgr-dvbs2rx(igorauad氏)+ gr-iioの
fmcomms2_sourceを使う。

Pluto+とはUSB接続(--pluto-uri usb: で自動検出、または usb:X.Y.Z を明示指定)。
復調後のMPEG-TSはFIFOへ書き出す。表示は別プロセス(ffplay等)がそのFIFOを読む
想定 (scripts/run_rx_display.sh 参照)。

ブロックチェーン(dvbs2rx_bridge.cpp:190-202と同一):
  fmcomms2_source -> agc_cc -> rotator_cc -> symbol_sync_cc -> plsync_cc
  -> xfecframe_demapper_cb -> ldpc_decoder_bb -> bch_decoder_bb
  -> bbdescrambler_bb -> bbdeheader_bb -> file_sink
  + msg_connect(plsync, "rotator_phase_inc", rotator, "cmd")
  + msg_connect(ldpc_decoder, "llr_pdu", xfecframe_demapper, "llr_pdu")
"""
import argparse
import os
import signal
import sys
import time

from gnuradio import gr, analog, blocks, iio, dvbs2rx

# TX(Pluto内蔵変調器pluto_dvb、GUIのbackend.py参照)が生成するMOD-CODのうち、
# 実際にgr-dvbs2rxで受信・復調できることを配線した組み合わせ。旧shonan_tx/aff3ct
# (conf/ファイル制約でQPSK-S_3/5・8/9等に限定されていた)はGUIから廃止済みのため、
# ここでの制約はpluto_dvb側の対応FEC(pi5版と共通)に合わせて随時追加してよい。
# 第3・4要素はdvbs2rx.dvbs2_pls()に渡す文字列(dvbs2rx.paramsのAPI表記に合わせる)。
_MODCOD_TABLE = {
    "QPSK-S_1/2": (dvbs2rx.MOD_QPSK, dvbs2rx.C1_2, "QPSK", "1/2"),
    "QPSK-S_3/5": (dvbs2rx.MOD_QPSK, dvbs2rx.C3_5, "QPSK", "3/5"),
    "QPSK-S_8/9": (dvbs2rx.MOD_QPSK, dvbs2rx.C8_9, "QPSK", "8/9"),
    "8PSK-S_3/5": (dvbs2rx.MOD_8PSK, dvbs2rx.C3_5, "8PSK", "3/5"),
    "8PSK-S_8/9": (dvbs2rx.MOD_8PSK, dvbs2rx.C8_9, "8PSK", "8/9"),
    "16APSK-S_8/9": (dvbs2rx.MOD_16APSK, dvbs2rx.C8_9, "16APSK", "8/9"),
}


def parse_args():
    p = argparse.ArgumentParser(description="shonan Pi4 DVB-S2 RX (gr-dvbs2rx)")
    # ★TX(pluto_dvb、GUIのbackend.py参照)はPluto上でSSH経由で直接動くためlibiio
    # クライアントではなく、本RXのiiod接続と競合しない。"ip:"URI(LAN経由)を使う。
    p.add_argument("--pluto-uri", default="ip:192.168.0.136", help="libiio URI")
    p.add_argument("--lo-hz", type=float, default=437000000, help="RX LO周波数")
    p.add_argument("--sample-rate-hz", type=int, default=3000000, help="サンプルレート")
    p.add_argument("--mod-cod", default="QPSK-S_3/5", choices=sorted(_MODCOD_TABLE.keys()))
    # ★TXはPluto内蔵変調器(pluto_dvb)を正式経路として使う(GUIのbackend.py参照、
    # real_pluto_bringup_status.md参照。旧shonan_tx/aff3ctはBBHEADER CRC8が常に
    # 失敗する不具合が未解決のままGUIからの呼び出しを廃止した)。pluto_dvbはnormal
    # FECFRAMEが既定(-vフラグ未指定時)、ロールオフ0.35固定、パイロットは-pで有効化
    # (-pなしでも受信自体は可能だったが、-pありの方がTSパケットエラー率が明確に
    # 低かった、実機検証済み)。
    p.add_argument("--rolloff", type=float, default=0.35)
    p.add_argument("--framesize", choices=["short", "normal"], default="normal",
                   help="FECFRAME長。pluto_dvb(Pluto内蔵変調器)はnormal")
    p.add_argument("--pilots", action="store_true", default=True,
                   help="パイロット付き(既定、pluto_dvb向け)")
    p.add_argument("--no-pilots", dest="pilots", action="store_false")
    p.add_argument("--agc", action="store_true", default=True, help="AGC有効(既定)")
    p.add_argument("--no-agc", dest="agc", action="store_false")
    p.add_argument("--gain-db", type=float, default=40.0, help="--no-agc時の手動ゲイン(dB)")
    p.add_argument("--output-fifo", required=True, help="復調後TSの出力先FIFOパス")
    p.add_argument("--status-interval-sec", type=float, default=1.0)
    return p.parse_args()


def main():
    args = parse_args()
    constellation, code_rate, pls_const_str, pls_code_str = _MODCOD_TABLE[args.mod_cod]

    if not os.path.exists(args.output_fifo):
        os.mkfifo(args.output_fifo, 0o600)

    sps = 2.0
    # ★Android版dvbs2rx_bridge.cppの実値にそのまま合わせる(実機でDVB-S2ロック・映像表示
    # まで確認済みの実績値のため)。
    rrc_delay = 5
    rrc_nfilts = 128
    framesize = dvbs2rx.FECFRAME_SHORT if args.framesize == "short" else dvbs2rx.FECFRAME_NORMAL

    tb = gr.top_block("shonan_rx")

    print(f"[shonan_rx] Pluto+へ接続中 (uri={args.pluto_uri}, lo={args.lo_hz}Hz, "
          f"sr={args.sample_rate_hz}Hz)...", file=sys.stderr)
    # voltage0/1=RX1のI/Q。gr_complex出力にはI/Q両方の有効化が必要
    # (dvbs2rx_bridge.cpp:138-141と同じ理由。片方だけだとchannel_list範囲外アクセスでSIGSEGV)。
    # ★USB-CDC-ECM直結(旧192.168.2.1)からLAN経由接続(192.168.0.136)に切り替えた後、
    # 0x8000(32768サンプル/read)ではIIOバッファのオーバーフロー('O'マーカー、gr-iio)が
    # 毎秒10回近く発生し、PLフレーム同期が一度もlockedへ遷移できなくなっていた。
    # 0x40000(262144サンプル/read)へ拡大しネットワーク経由の読み出し頻度を下げたところ、
    # 大幅に改善しlocked到達・複数フレーム連続デコードを確認(real_pluto_bringup_status.md参照)。
    src = iio.fmcomms2_source_fc32(args.pluto_uri, [True, True, False, False], 0x40000)
    src.set_frequency(args.lo_hz)
    src.set_samplerate(args.sample_rate_hz)
    if args.agc:
        src.set_gain_mode(0, "slow_attack")
    else:
        src.set_gain_mode(0, "manual")
        src.set_gain(0, args.gain_db)

    # ★Android版dvbs2rx_bridge.cppの実値にそのまま合わせる(ノイズ注入や固定ゲインは
    # Android版に存在しない独自の回避策だったため撤回し、実績のある設定に戻す)。
    agc = analog.agc_cc(1e-5, 1.0, 1.0, 65536)
    rotator = dvbs2rx.rotator_cc(0.0, True)
    symbol_sync = dvbs2rx.symbol_sync_cc(sps, 0.001, 1.0, args.rolloff, rrc_delay, rrc_nfilts, 0)
    # ★dvbs2_bridge.cpp/dvbs2rx_bridge.cppは「単一PLS値を厳密計算する代わりに全PLS許容
    # (0xFFFF...FFFF)にする」という回避策を取っていたが、これは相関器が見つけた候補を
    # 検証・棄却する仕組み(妥当なPLSコードかどうかのチェック)を実質無効化してしまい、
    # ノイズの少ないループバック環境でsofが際限なく誤検出される原因になっていた
    # (frame=0のまま毎秒数十万回sofが増加する事象で発覚)。dvbs2rx.dvbs2_pls()/
    # pls_filter()で実際に使うMODCODに対応する単一PLS値だけを許可するよう修正する。
    target_pls = dvbs2rx.dvbs2_pls(pls_const_str, pls_code_str, args.framesize, args.pilots)
    pls_filter_lo, pls_filter_hi = dvbs2rx.pls_filter(target_pls)
    # ★acm_vcm/multistreamは共にFalseが正しい: shonanのTX信号は単一MODCOD固定・単一
    # ストリームのCCM/SIS信号(ACM/VCMのような可変MODCODでも、MISのような複数TS多重でも
    # ない)。plsync_cc_impl.cc の実装では acm_vcm/multistream のどちらかがTrueだと
    # ダミーPLFRAME用のPLS(0-3)がexpected_plscに追加されてしまいexpected_plsc.size()が
    # 1にならず、本来CCM/SISで単純化されるはずのPLSCデコーダが無効化されないまま複雑な
    # 検証パスに入ってしまう。これがsofは増加し続けるのにframe/rejectedが常に0のまま
    # (=一度も真にロックしない)という不具合の原因だった。True/Trueは誤り。
    plsync = dvbs2rx.plsync_cc(0, 30, sps, 0, False, False, pls_filter_lo, pls_filter_hi)
    xfecframe_demapper = dvbs2rx.xfecframe_demapper_cb(framesize, code_rate, constellation)
    ldpc_decoder = dvbs2rx.ldpc_decoder_bb(dvbs2rx.STANDARD_DVBS2, framesize, code_rate,
                                            constellation, dvbs2rx.OM_MESSAGE, dvbs2rx.INFO_OFF, 25, 0)
    bch_decoder = dvbs2rx.bch_decoder_bb(dvbs2rx.STANDARD_DVBS2, framesize, code_rate,
                                          dvbs2rx.OM_MESSAGE, 0)
    bbdescrambler = dvbs2rx.bbdescrambler_bb(dvbs2rx.STANDARD_DVBS2, framesize, code_rate)
    bbdeheader = dvbs2rx.bbdeheader_bb(dvbs2rx.STANDARD_DVBS2, framesize, code_rate, 0)

    # file_sink::make()はFIFOをwriteでopenするため、読み手(ffplay等)が先にいないと
    # ブロックする(dvbs2rx_bridge.cpp:180-184と同じ注意点)。run_rx_display.shは
    # 本スクリプトをバックグラウンド起動してからffplayを起動する構成にすること。
    sink = blocks.file_sink(gr.sizeof_char, args.output_fifo, False)
    sink.set_unbuffered(True)

    tb.connect(src, agc)
    tb.connect(agc, rotator)
    tb.connect(rotator, symbol_sync)
    tb.connect(symbol_sync, plsync)
    tb.connect(plsync, xfecframe_demapper)
    tb.connect(xfecframe_demapper, ldpc_decoder)
    tb.connect(ldpc_decoder, bch_decoder)
    tb.connect(bch_decoder, bbdescrambler)
    tb.connect(bbdescrambler, bbdeheader)
    tb.connect(bbdeheader, sink)

    tb.msg_connect(plsync, "rotator_phase_inc", rotator, "cmd")
    tb.msg_connect(ldpc_decoder, "llr_pdu", xfecframe_demapper, "llr_pdu")

    shutdown = {"requested": False}

    def handle_signal(signum, frame):
        shutdown["requested"] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"[shonan_rx] RX開始 mod-cod={args.mod_cod} rolloff={args.rolloff}", file=sys.stderr)
    tb.start()
    try:
        while not shutdown["requested"]:
            time.sleep(args.status_interval_sec)
            print(f"[shonan_rx] locked={plsync.get_locked()} "
                  f"sof={plsync.get_sof_count()} frame={plsync.get_frame_count()} "
                  f"rejected={plsync.get_rejected_count()} "
                  f"freq_off={plsync.get_freq_offset():.1f} "
                  f"packets={bbdeheader.get_packet_count()} errors={bbdeheader.get_error_count()}",
                  file=sys.stderr)
            print(f"[flowdbg] plsync_out={plsync.nitems_written(0)} "
                  f"xfec_out={xfecframe_demapper.nitems_written(0)} "
                  f"ldpc_in={ldpc_decoder.nitems_read(0)} ldpc_out={ldpc_decoder.nitems_written(0)} "
                  f"bch_in={bch_decoder.nitems_read(0)} bch_out={bch_decoder.nitems_written(0)} "
                  f"descr_out={bbdescrambler.nitems_written(0)} deh_in={bbdeheader.nitems_read(0)}",
                  file=sys.stderr)
            print(f"[fecdbg] ldpc_avg_trials={ldpc_decoder.get_average_trials()} "
                  f"bch_error_count={bch_decoder.get_error_count()}",
                  file=sys.stderr)
    finally:
        print("[shonan_rx] 停止中...", file=sys.stderr)
        tb.stop()
        tb.wait()
        print("[shonan_rx] 終了しました", file=sys.stderr)


if __name__ == "__main__":
    main()
