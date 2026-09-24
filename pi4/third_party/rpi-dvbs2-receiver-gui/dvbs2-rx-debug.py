#!/usr/bin/env python3
"""Wrapper that enables GNU Radio's spdlog debug-level output before
running the real dvbs2-rx script, so the built-in GR_LOG_DEBUG_LEVEL
traces in pl_frame_sync/pl_freq_sync actually get printed.
"""
import sys
import runpy

from gnuradio import gr

logging = gr.logging()
logging.set_default_level(gr.log_levels.debug)
logging.set_debug_level(gr.log_levels.debug)
logging.add_default_console_sink()
logging.add_debug_console_sink()

sys.argv[0] = '/usr/local/bin/dvbs2-rx'
runpy.run_path('/usr/local/bin/dvbs2-rx', run_name='__main__')
