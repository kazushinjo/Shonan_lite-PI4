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
