import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    """Embedded Python Block: passthrough placeholder.

    Original implementation is missing from the repository; this simply
    copies the TS byte stream through unchanged (equivalent to the
    commented-out direct hier -> UDP sink connection in RF_UDP_dvbs2_rx.py).
    Replace with the real logic if/when recovered.
    """

    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',
            in_sig=[np.uint8],
            out_sig=[np.uint8]
        )
        self._total = 0

    def work(self, input_items, output_items):
        n = len(input_items[0])
        output_items[0][:] = input_items[0]
        self._total += n
        if n > 0:
            print(f"[epy_block_0] +{n} bytes, total={self._total}", flush=True)
        return n
