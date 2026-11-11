"""設定画面「Pluto 情報」の読み取り結果の解析(pluto_info.py)のテスト。

iio_attr(libiio 0.25)の出力形式は tests/iio_attr.c の printf に合わせている。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gui"))

import pluto_info  # noqa: E402

CONTEXT_OUTPUT = """IIO context with 4 attributes:
hw_model: Analog Devices PlutoSDR Rev.C (Z7010-AD9363A)
fw_version: v0.39-dirty
ad9361-phy,model: ad9364
local,kernel: 5.15.0-xilinx
"""

DEVICE_OUTPUT = """dev 'ad9361-phy', attr 'calib_mode', value :'auto'
dev 'ad9361-phy', attr 'ensm_mode', value :'fdd'
dev 'ad9361-phy', attr 'xo_correction', value :'40000000'
"""

CHANNEL_OUTPUT = """dev 'ad9361-phy', channel 'altvoltage0' (output), id 'RX_LO', attr 'frequency', value '437000000'
dev 'ad9361-phy', channel 'altvoltage0' (output), id 'RX_LO', attr 'powerdown', value '0'
dev 'ad9361-phy', channel 'altvoltage1' (output), id 'TX_LO', attr 'frequency', value '1273000000'
dev 'ad9361-phy', channel 'voltage0' (input), attr 'hardwaregain', value '71.000000 dB'
dev 'ad9361-phy', channel 'voltage0' (input), attr 'sampling_frequency', value '2000000'
dev 'ad9361-phy', channel 'voltage0' (output), attr 'hardwaregain', value '-10.000000 dB'
"""


class PlutoInfoParseTest(unittest.TestCase):
    def test_context_attrs(self):
        attrs = pluto_info.parse_context_attrs(CONTEXT_OUTPUT)
        self.assertEqual(attrs["fw_version"], "v0.39-dirty")
        self.assertEqual(attrs["ad9361-phy,model"], "ad9364")
        self.assertNotIn("IIO context with 4 attributes", attrs)

    def test_device_attrs(self):
        attrs = pluto_info.parse_device_attrs(DEVICE_OUTPUT)
        self.assertEqual(attrs, {"calib_mode": "auto", "ensm_mode": "fdd", "xo_correction": "40000000"})

    def test_channel_attrs_input_output_distinguished(self):
        attrs = pluto_info.parse_channel_attrs(CHANNEL_OUTPUT)
        self.assertEqual(attrs[("altvoltage0", True, "frequency")], "437000000")
        self.assertEqual(attrs[("voltage0", False, "hardwaregain")], "71.000000 dB")
        self.assertEqual(attrs[("voltage0", True, "hardwaregain")], "-10.000000 dB")

    def test_read_ad9361_formats_rows(self):
        outputs = {"-d": DEVICE_OUTPUT, "-c": CHANNEL_OUTPUT}
        original = pluto_info._run_iio_attr
        pluto_info._run_iio_attr = lambda args: outputs[args[2]]
        try:
            rows = dict(pluto_info.read_ad9361("ip:192.168.0.51"))
        finally:
            pluto_info._run_iio_attr = original
        self.assertEqual(len(rows), len(pluto_info.AD9361_ENTRIES))
        self.assertEqual(rows["RX LO周波数"], "437.000 MHz")
        self.assertEqual(rows["TX LO周波数"], "1273.000 MHz")
        self.assertEqual(rows["RXサンプルレート"], "2.000 MHz")
        self.assertEqual(rows["TX減衰"], "-10.000000 dB")
        self.assertEqual(rows["RX RSSI"], "-")

    def test_settings_txt(self):
        rows = pluto_info.parse_settings_txt("callsign JA1XXX\nfreq 1273.0\n\nh265box \n")
        self.assertEqual(rows, [("callsign", "JA1XXX"), ("freq", "1273.0"), ("h265box", "")])


if __name__ == "__main__":
    unittest.main()
