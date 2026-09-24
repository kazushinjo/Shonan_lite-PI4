#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: DVB-S2 Rx
# Description: Full DVB-S2 receiver. Processes IQ samples from stdin and outputs MPEG TS packets to stdout.
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
import os
import sys
import logging as log
import dvbs2_rx_epy_block_0 as epy_block_0  # embedded python block
import threading

def get_state_directory() -> str:
    oldpath = os.path.expanduser("~/.grc_gnuradio")
    try:
        from gnuradio.gr import paths
        newpath = paths.persistent()
        if os.path.exists(newpath):
            return newpath
        if os.path.exists(oldpath):
            log.warning(f"Found persistent state path '{newpath}', but file does not exist. " +
                     f"Old default persistent state path '{oldpath}' exists; using that. " +
                     "Please consider moving state to new location.")
            return oldpath
        # Default to the correct path if both are configured.
        # neither old, nor new path exist: create new path, return that
        os.makedirs(newpath, exist_ok=True)
        return newpath
    except (ImportError, NameError):
        log.warning("Could not retrieve GNU Radio persistent state directory from GNU Radio. " +
                 "Trying defaults.")
        xdgstate = os.getenv("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
        xdgcand = os.path.join(xdgstate, "gnuradio")
        if os.path.exists(xdgcand):
            return xdgcand
        if os.path.exists(oldpath):
            log.warning(f"Using legacy state path '{oldpath}'. Please consider moving state " +
                     f"files to '{xdgcand}'.")
            return oldpath
        # neither old, nor new path exist: create new path, return that
        os.makedirs(xdgcand, exist_ok=True)
        return xdgcand

sys.path.append(os.environ.get('GRC_HIER_PATH', get_state_directory()))

from dvbs2rx_rx_hier import dvbs2rx_rx_hier  # grc-generated hier_block
from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import iio
from gnuradio import network
import sip
import threading



class dvbs2_rx(gr.top_block, Qt.QWidget):

    def __init__(self, agc_gain=1, agc_rate=(1e-5), agc_ref=1, debug=2, frame_size='normal', freq=438022000, gold_code=0, in_fd=0, modcod='QPSK1/4', out_fd=0, pl_freq_est_period=30, rolloff=0.2, rrc_delay=5, rrc_nfilts=128, sps=4, sym_rate=333000, sym_sync_damping=1.0, sym_sync_loop_bw=0.001):
        gr.top_block.__init__(self, "DVB-S2 Rx", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("DVB-S2 Rx")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)
        self.epy_block_0 = epy_block_0.blk()        

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "dvbs2_rx")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Parameters
        ##################################################
        self.agc_gain = agc_gain
        self.agc_rate = agc_rate
        self.agc_ref = agc_ref
        self.debug = debug
        self.frame_size = frame_size
        self.freq = freq
        self.gold_code = gold_code
        self.in_fd = in_fd
        self.modcod = modcod
        self.out_fd = out_fd
        self.pl_freq_est_period = pl_freq_est_period
        self.rolloff = rolloff
        self.rrc_delay = rrc_delay
        self.rrc_nfilts = rrc_nfilts
        self.sps = sps
        self.sym_rate = sym_rate
        self.sym_sync_damping = sym_sync_damping
        self.sym_sync_loop_bw = sym_sync_loop_bw

        ##################################################
        # Variables
        ##################################################
        self.code_rate = code_rate = modcod.upper().replace("8PSK", "").replace("QPSK", "")
        self.samp_rate = samp_rate = sym_rate * sps
        self.plheader_len = plheader_len = 90
        self.plframe_len = plframe_len = 33282
        self.pilot_len = pilot_len = int((360-1)/16)*36
        self.constellation = constellation = modcod.replace(code_rate, "")

        ##################################################
        # Blocks
        ##################################################

        self.tabs = Qt.QTabWidget()
        self.tabs_widget_0 = Qt.QWidget()
        self.tabs_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_0)
        self.tabs_grid_layout_0 = Qt.QGridLayout()
        self.tabs_layout_0.addLayout(self.tabs_grid_layout_0)
        self.tabs.addTab(self.tabs_widget_0, 'Input')
        self.tabs_widget_1 = Qt.QWidget()
        self.tabs_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_1)
        self.tabs_grid_layout_1 = Qt.QGridLayout()
        self.tabs_layout_1.addLayout(self.tabs_grid_layout_1)
        self.tabs.addTab(self.tabs_widget_1, 'Frequency Correction')
        self.tabs_widget_2 = Qt.QWidget()
        self.tabs_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_2)
        self.tabs_grid_layout_2 = Qt.QGridLayout()
        self.tabs_layout_2.addLayout(self.tabs_grid_layout_2)
        self.tabs.addTab(self.tabs_widget_2, 'Symbol Sync')
        self.tabs_widget_3 = Qt.QWidget()
        self.tabs_layout_3 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_3)
        self.tabs_grid_layout_3 = Qt.QGridLayout()
        self.tabs_layout_3.addLayout(self.tabs_grid_layout_3)
        self.tabs.addTab(self.tabs_widget_3, 'Frame Recovery')
        self.tabs_widget_4 = Qt.QWidget()
        self.tabs_layout_4 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tabs_widget_4)
        self.tabs_grid_layout_4 = Qt.QGridLayout()
        self.tabs_layout_4.addLayout(self.tabs_grid_layout_4)
        self.tabs.addTab(self.tabs_widget_4, 'Phase Recovery')
        self.top_grid_layout.addWidget(self.tabs, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_const_sink_x_0_0 = qtgui.const_sink_c(
            1024, #size
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_const_sink_x_0_0.set_update_time(0.10)
        self.qtgui_const_sink_x_0_0.set_y_axis((-2), 2)
        self.qtgui_const_sink_x_0_0.set_x_axis((-2), 2)
        self.qtgui_const_sink_x_0_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, "")
        self.qtgui_const_sink_x_0_0.enable_autoscale(False)
        self.qtgui_const_sink_x_0_0.enable_grid(False)
        self.qtgui_const_sink_x_0_0.enable_axis_labels(True)


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        styles = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        markers = [0, 0, 0, 0, 0,
            0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_const_sink_x_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_const_sink_x_0_0.set_line_label(i, labels[i])
            self.qtgui_const_sink_x_0_0.set_line_width(i, widths[i])
            self.qtgui_const_sink_x_0_0.set_line_color(i, colors[i])
            self.qtgui_const_sink_x_0_0.set_line_style(i, styles[i])
            self.qtgui_const_sink_x_0_0.set_line_marker(i, markers[i])
            self.qtgui_const_sink_x_0_0.set_line_alpha(i, alphas[i])

        self._qtgui_const_sink_x_0_0_win = sip.wrapinstance(self.qtgui_const_sink_x_0_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_const_sink_x_0_0_win)
        self.network_udp_sink_0 = network.udp_sink(gr.sizeof_char, 1, '127.0.0.1', 2000, 0, 1472, False)
        self.iio_pluto_source_0 = iio.fmcomms2_source_fc32('' if '' else iio.get_pluto_uri(), [True, True], 32768)
        self.iio_pluto_source_0.set_len_tag_key('packet_len')
        self.iio_pluto_source_0.set_frequency(freq)
        self.iio_pluto_source_0.set_samplerate(int(samp_rate))
        self.iio_pluto_source_0.set_gain_mode(0, 'slow_attack')
        self.iio_pluto_source_0.set_gain(0, 64)
        self.iio_pluto_source_0.set_quadrature(True)
        self.iio_pluto_source_0.set_rfdc(True)
        self.iio_pluto_source_0.set_bbdc(True)
        self.iio_pluto_source_0.set_filter_params('Auto', '', 0, 0)
        self.dvbs2rx_rx_hier_0 = dvbs2rx_rx_hier(
            agc_gain=agc_gain,
            agc_rate=agc_rate,
            agc_ref=agc_ref,
            debug=debug,
            frame_size=frame_size,
            gold_code=gold_code,
            modcod=modcod,
            pl_freq_est_period=pl_freq_est_period,
            rolloff=rolloff,
            rrc_delay=rrc_delay,
            rrc_nfilts=rrc_nfilts,
            sps=sps,
            sym_rate=sym_rate,
            sym_sync_damping=sym_sync_damping,
            sym_sync_loop_bw=sym_sync_loop_bw,
        )
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, 'tmp.ts', False)
        self.blocks_file_sink_0.set_unbuffered(False)
        self.blocks_fd_sink = blocks.file_descriptor_sink(gr.sizeof_char*1, out_fd)


        ##################################################
        # Connections
        ##################################################

        # Pluto Source → receiver 入力
        self.connect((self.iio_pluto_source_0, 0),
                     (self.dvbs2rx_rx_hier_0, 0))

        # コンステレーション
        self.connect((self.dvbs2rx_rx_hier_0, 2),
                     (self.qtgui_const_sink_x_0_0, 0))

        # TS 出力 → epy_block_0 → UDP Sink
        self.connect((self.dvbs2rx_rx_hier_0, 0),
                     (self.epy_block_0, 0))             # self.dvbs2rx_rx_hier_0 -> self.epy_block_0 -> self.network_udp_sink

        self.connect((self.epy_block_0, 0),
                     (self.network_udp_sink_0, 0))
#        self.connect((self.dvbs2rx_rx_hier_0, 0),
#                     (self.network_udp_sink_0, 0))       # self.dvbs2rx_rx_hier_0 -> self.network_udp_sink


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "dvbs2_rx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_agc_gain(self):
        return self.agc_gain

    def set_agc_gain(self, agc_gain):
        self.agc_gain = agc_gain
        self.dvbs2rx_rx_hier_0.set_agc_gain(self.agc_gain)

    def get_agc_rate(self):
        return self.agc_rate

    def set_agc_rate(self, agc_rate):
        self.agc_rate = agc_rate
        self.dvbs2rx_rx_hier_0.set_agc_rate(self.agc_rate)

    def get_agc_ref(self):
        return self.agc_ref

    def set_agc_ref(self, agc_ref):
        self.agc_ref = agc_ref
        self.dvbs2rx_rx_hier_0.set_agc_ref(self.agc_ref)

    def get_debug(self):
        return self.debug

    def set_debug(self, debug):
        self.debug = debug
        self.dvbs2rx_rx_hier_0.set_debug(self.debug)

    def get_frame_size(self):
        return self.frame_size

    def set_frame_size(self, frame_size):
        self.frame_size = frame_size
        self.dvbs2rx_rx_hier_0.set_frame_size(self.frame_size)

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.iio_pluto_source_0.set_frequency(self.freq)

    def get_gold_code(self):
        return self.gold_code

    def set_gold_code(self, gold_code):
        self.gold_code = gold_code
        self.dvbs2rx_rx_hier_0.set_gold_code(self.gold_code)

    def get_in_fd(self):
        return self.in_fd

    def set_in_fd(self, in_fd):
        self.in_fd = in_fd

    def get_modcod(self):
        return self.modcod

    def set_modcod(self, modcod):
        self.modcod = modcod
        self.dvbs2rx_rx_hier_0.set_modcod(self.modcod)

    def get_out_fd(self):
        return self.out_fd

    def set_out_fd(self, out_fd):
        self.out_fd = out_fd

    def get_pl_freq_est_period(self):
        return self.pl_freq_est_period

    def set_pl_freq_est_period(self, pl_freq_est_period):
        self.pl_freq_est_period = pl_freq_est_period
        self.dvbs2rx_rx_hier_0.set_pl_freq_est_period(self.pl_freq_est_period)

    def get_rolloff(self):
        return self.rolloff

    def set_rolloff(self, rolloff):
        self.rolloff = rolloff
        self.dvbs2rx_rx_hier_0.set_rolloff(self.rolloff)

    def get_rrc_delay(self):
        return self.rrc_delay

    def set_rrc_delay(self, rrc_delay):
        self.rrc_delay = rrc_delay
        self.dvbs2rx_rx_hier_0.set_rrc_delay(self.rrc_delay)

    def get_rrc_nfilts(self):
        return self.rrc_nfilts

    def set_rrc_nfilts(self, rrc_nfilts):
        self.rrc_nfilts = rrc_nfilts
        self.dvbs2rx_rx_hier_0.set_rrc_nfilts(self.rrc_nfilts)

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_samp_rate(self.sym_rate * self.sps)
        self.dvbs2rx_rx_hier_0.set_sps(self.sps)

    def get_sym_rate(self):
        return self.sym_rate

    def set_sym_rate(self, sym_rate):
        self.sym_rate = sym_rate
        self.set_samp_rate(self.sym_rate * self.sps)
        self.dvbs2rx_rx_hier_0.set_sym_rate(self.sym_rate)

    def get_sym_sync_damping(self):
        return self.sym_sync_damping

    def set_sym_sync_damping(self, sym_sync_damping):
        self.sym_sync_damping = sym_sync_damping
        self.dvbs2rx_rx_hier_0.set_sym_sync_damping(self.sym_sync_damping)

    def get_sym_sync_loop_bw(self):
        return self.sym_sync_loop_bw

    def set_sym_sync_loop_bw(self, sym_sync_loop_bw):
        self.sym_sync_loop_bw = sym_sync_loop_bw
        self.dvbs2rx_rx_hier_0.set_sym_sync_loop_bw(self.sym_sync_loop_bw)

    def get_code_rate(self):
        return self.code_rate

    def set_code_rate(self, code_rate):
        self.code_rate = code_rate
        self.set_constellation(modcod.replace(self.code_rate, ""))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.iio_pluto_source_0.set_samplerate(self.samp_rate)

    def get_plheader_len(self):
        return self.plheader_len

    def set_plheader_len(self, plheader_len):
        self.plheader_len = plheader_len

    def get_plframe_len(self):
        return self.plframe_len

    def set_plframe_len(self, plframe_len):
        self.plframe_len = plframe_len

    def get_pilot_len(self):
        return self.pilot_len

    def set_pilot_len(self, pilot_len):
        self.pilot_len = pilot_len

    def get_constellation(self):
        return self.constellation

    def set_constellation(self, constellation):
        self.constellation = constellation



def argument_parser():
    description = 'Full DVB-S2 receiver. Processes IQ samples from stdin and outputs MPEG TS packets to stdout.'
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "--agc-gain", dest="agc_gain", type=eng_float, default=eng_notation.num_to_str(float(1)),
        help="Set AGC gain [default=%(default)r]")
    parser.add_argument(
        "--agc-rate", dest="agc_rate", type=eng_float, default=eng_notation.num_to_str(float((1e-5))),
        help="Set AGC update rate [default=%(default)r]")
    parser.add_argument(
        "--agc-ref", dest="agc_ref", type=eng_float, default=eng_notation.num_to_str(float(1)),
        help="Set AGC's reference value [default=%(default)r]")
    parser.add_argument(
        "-d", "--debug", dest="debug", type=intx, default=0,
        help="Set debugging level [default=%(default)r]")
    parser.add_argument(
        "-f", "--frame-size", dest="frame_size", type=str, default='normal',
        help="Set FECFRAME size [default=%(default)r]")
    parser.add_argument(
        "-g", "--freq", dest="freq", type=eng_float, default=eng_notation.num_to_str(float(438022000)),
        help="Set center frequency [default=%(default)r]")
    parser.add_argument(
        "--gold-code", dest="gold_code", type=intx, default=0,
        help="Set Gold code [default=%(default)r]")
    parser.add_argument(
        "-I", "--in-fd", dest="in_fd", type=intx, default=0,
        help="Set input file descriptor [default=%(default)r]")
    parser.add_argument(
        "-m", "--modcod", dest="modcod", type=str, default='QPSK1/4',
        help="Set MODCOD [default=%(default)r]")
    parser.add_argument(
        "-O", "--out-fd", dest="out_fd", type=intx, default=1,
        help="Set output file descriptor [default=%(default)r]")
    parser.add_argument(
        "--pl-freq-est-period", dest="pl_freq_est_period", type=intx, default=30,
        help="Set PL synchronizer's frequency estimation period in frames [default=%(default)r]")
    parser.add_argument(
        "-r", "--rolloff", dest="rolloff", type=eng_float, default=eng_notation.num_to_str(float(0.2)),
        help="Set rolloff factor [default=%(default)r]")
    parser.add_argument(
        "--rrc-delay", dest="rrc_delay", type=intx, default=5,
        help="Set RRC filter delay in symbol periods [default=%(default)r]")
    parser.add_argument(
        "--rrc-nfilts", dest="rrc_nfilts", type=intx, default=128,
        help="Set number of branches on the polyphase RRC filter [default=%(default)r]")
    parser.add_argument(
        "-o", "--sps", dest="sps", type=eng_float, default=eng_notation.num_to_str(float(4)),
        help="Set oversampling ratio in samples per symbol [default=%(default)r]")
    parser.add_argument(
        "-s", "--sym-rate", dest="sym_rate", type=intx, default=333000,
        help="Set symbol rate in bauds [default=%(default)r]")
    parser.add_argument(
        "--sym-sync-damping", dest="sym_sync_damping", type=eng_float, default=eng_notation.num_to_str(float(1.0)),
        help="Set symbol synchronizer's damping factor [default=%(default)r]")
    parser.add_argument(
        "--sym-sync-loop-bw", dest="sym_sync_loop_bw", type=eng_float, default=eng_notation.num_to_str(float(0.001)),
        help="Set symbol synchronizer's loop bandwidth [default=%(default)r]")
    return parser


def main(top_block_cls=dvbs2_rx, options=None):
    if options is None:
        options = argument_parser().parse_args()

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(agc_gain=options.agc_gain, agc_rate=options.agc_rate, agc_ref=options.agc_ref, debug=options.debug, frame_size=options.frame_size, freq=options.freq, gold_code=options.gold_code, in_fd=options.in_fd, modcod=options.modcod, out_fd=options.out_fd, pl_freq_est_period=options.pl_freq_est_period, rolloff=options.rolloff, rrc_delay=options.rrc_delay, rrc_nfilts=options.rrc_nfilts, sps=options.sps, sym_rate=options.sym_rate, sym_sync_damping=options.sym_sync_damping, sym_sync_loop_bw=options.sym_sync_loop_bw)


    tb.start()


    tb.flowgraph_started.set()

    tb.show()


    print("========== DVB-S2 RX Parameters ==========", file=sys.stderr)
    print(f"Frequency   : {options.freq}", file=sys.stderr)
    print(f"MODCOD      : {options.modcod}", file=sys.stderr)
    print(f"Symbol Rate : {options.sym_rate}", file=sys.stderr)
    print(f"SPS         : {options.sps}", file=sys.stderr)
    print(f"Sample Rate : {options.sym_rate * options.sps}", file=sys.stderr)
    print(f"Rolloff     : {options.rolloff}", file=sys.stderr)
    print(f"Frame Size  : {options.frame_size}", file=sys.stderr)
    print(f"Gold Code   : {options.gold_code}", file=sys.stderr)
    print(f"Debug       : {options.debug}", file=sys.stderr)
    print("==========================================", file=sys.stderr)
    sys.stderr.flush()



    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
