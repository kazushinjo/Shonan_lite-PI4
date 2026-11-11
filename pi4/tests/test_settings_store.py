import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


GUI_DIR = Path(__file__).resolve().parents[1] / "gui"
sys.path.insert(0, str(GUI_DIR))

import settings_store


class SettingsStoreTest(unittest.TestCase):
    def test_android_compatible_defaults(self):
        settings = settings_store.AppSettings()
        self.assertEqual(settings.pluto_uri, "ip:192.168.0.10")
        self.assertEqual(settings.tx_destination_port, 7272)
        self.assertEqual(settings.rx_listen_port, 4003)
        self.assertEqual(settings.rx_status_port, 4002)
        self.assertEqual(settings.rx_volume, 1.0)
        self.assertEqual(settings.symbol_rate_msps, 0.5)
        self.assertEqual(settings.fec_rate, "3/5")
        self.assertEqual(settings.modulation_scheme, "QPSK")
        self.assertFalse(settings.iio_preflight_enabled)

    def test_symbol_rate_and_modcod_conversion(self):
        settings = settings_store.AppSettings(symbol_rate_msps=0.333)
        self.assertEqual(settings.symbol_rate_hz(), 333_000)
        self.assertEqual(settings.mod_cod(), "QPSK-S_3/5")
        self.assertTrue(settings.tx_mod_cod_supported())
        self.assertTrue(settings.rx_mod_cod_supported())

    def test_invalid_dvbs2_modcod_is_rejected(self):
        settings = settings_store.AppSettings(modulation_scheme="32APSK", fec_rate="1/4")
        self.assertFalse(settings.tx_mod_cod_supported())
        self.assertFalse(settings.rx_mod_cod_supported())

    def test_all_dvbs2_modcods_are_supported(self):
        self.assertEqual(len(settings_store.TX_SUPPORTED_MODCODS), 28)
        for mod_cod in ("QPSK-S_1/4", "QPSK-S_9/10", "8PSK-S_9/10",
                        "16APSK-S_2/3", "16APSK-S_9/10", "32APSK-S_3/4", "32APSK-S_9/10"):
            self.assertIn(mod_cod, settings_store.TX_SUPPORTED_MODCODS)
            self.assertIn(mod_cod, settings_store.RX_SUPPORTED_MODCODS)
        self.assertEqual(settings_store.supported_fec_rates("16APSK"),
                         ["2/3", "3/4", "4/5", "5/6", "8/9", "9/10"])

    def test_rx_modcod_table_matches_gui(self):
        # shonan_rx.pyはGNU Radioを読み込むためimportせず、定義部分だけを評価して照合する
        rx_source = (GUI_DIR.parent / "rx" / "shonan_rx.py").read_text(encoding="utf-8")
        tree = ast.parse(rx_source)
        for node in tree.body:
            if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "_MODCOD_FEC_RATES"):
                rx_rates = ast.literal_eval(node.value)
                break
        else:
            self.fail("_MODCOD_FEC_RATES not found in shonan_rx.py")
        self.assertEqual(rx_rates, settings_store.MODULATION_FEC_RATES)

    def test_loopback_destination_and_frequency_fallback(self):
        settings = settings_store.AppSettings(
            selected_band="LOOPBACK",
            custom_lo_frequency_hz=437_000_000,
            loopback_use_localhost=True,
        )
        self.assertEqual(settings.effective_lo_hz(), 437_000_000)
        self.assertEqual(settings.effective_loopback_host(), "127.0.0.1")

    def test_load_migrates_older_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"pluto_uri": "ip:192.168.0.136"}), encoding="utf-8")
            with mock.patch.object(settings_store, "SETTINGS_PATH", path):
                loaded = settings_store.load()
        self.assertEqual(loaded.pluto_uri, "ip:192.168.0.136")
        self.assertEqual(loaded.tx_destination_port, 7272)
        self.assertEqual(loaded.rx_volume, 1.0)
        self.assertFalse(loaded.iio_preflight_enabled)


if __name__ == "__main__":
    unittest.main()


class AutoFecTest(unittest.TestCase):
    def test_capacity_matches_dvbs2_frame_structure(self):
        # QPSK 3/5 パイロットあり: 1フレーム 33282 シンボルに 38688-80 ビット
        self.assertAlmostEqual(settings_store.dvbs2_ts_capacity_bps(500_000, "QPSK", "3/5"),
                               500_000 * (38688 - 80) / 33282)
        # 32APSK: 144スロット+8パイロットブロック = 13338 シンボル
        self.assertAlmostEqual(settings_store.dvbs2_ts_capacity_bps(1_000_000, "32APSK", "3/4"),
                               1_000_000 * (48408 - 80) / 13338)

    def test_auto_fec_picks_most_robust_rate_with_enough_capacity(self):
        self.assertEqual(settings_store.auto_fec_rate(500_000, "QPSK"), "3/5")
        self.assertEqual(settings_store.auto_fec_rate(1_000_000, "QPSK"), "1/3")
        self.assertEqual(settings_store.auto_fec_rate(2_000_000, "QPSK"), "1/4")
        self.assertEqual(settings_store.auto_fec_rate(1_000_000, "8PSK"), "3/5")
        # どれでも足りなければ、いちばん多く送れるFEC
        self.assertEqual(settings_store.auto_fec_rate(100_000, "QPSK"), "9/10")

    def test_apply_auto_fec_respects_manual_mode(self):
        s = settings_store.AppSettings(symbol_rate_msps=1.0, fec_rate="8/9", fec_auto=False)
        self.assertFalse(s.apply_auto_fec())
        self.assertEqual(s.fec_rate, "8/9")
        s.fec_auto = True
        self.assertTrue(s.apply_auto_fec())
        self.assertEqual(s.fec_rate, "1/3")


class PlutoCapabilityTest(unittest.TestCase):
    def test_available_modulations(self):
        self.assertEqual(settings_store.available_modulation_schemes(False), ["QPSK", "8PSK"])
        self.assertEqual(settings_store.available_modulation_schemes(True),
                         ["QPSK", "8PSK", "16APSK", "32APSK"])

    def test_apsk_is_changed_to_8psk_on_non_fpga_pluto(self):
        s = settings_store.AppSettings(symbol_rate_msps=1.0, modulation_scheme="32APSK", fec_rate="3/4")
        self.assertTrue(s.apply_pluto_capability(False))
        self.assertEqual(s.modulation_scheme, "8PSK")
        self.assertIn(s.fec_rate, settings_store.supported_fec_rates("8PSK"))
        self.assertFalse(s.pluto_apsk_capable)

    def test_qpsk_is_kept_and_fpga_allows_apsk(self):
        s = settings_store.AppSettings(modulation_scheme="QPSK")
        self.assertFalse(s.apply_pluto_capability(False))
        s.modulation_scheme = "16APSK"
        self.assertFalse(s.apply_pluto_capability(True))
        self.assertEqual(s.modulation_scheme, "16APSK")
