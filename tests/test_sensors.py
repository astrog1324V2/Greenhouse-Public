from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))

from greenhouse_monitor.config import load_settings
from greenhouse_monitor.sensors import RaspberryPiSensorReader


class FlakyDHT22:
    temperature_calls = 0

    def __init__(self, pin, use_pulseio=False):
        self.pin = pin
        self.use_pulseio = use_pulseio

    @property
    def temperature(self):
        type(self).temperature_calls += 1
        if type(self).temperature_calls == 1:
            raise RuntimeError("Checksum did not validate. Try again.")
        return 23.4

    @property
    def humidity(self):
        return 56.7


class FakeBH1750:
    def __init__(self, i2c, address):
        self.i2c = i2c
        self.address = address

    @property
    def lux(self):
        return 321.0


class SensorRetryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.original_modules = {
            name: sys.modules.get(name)
            for name in ("adafruit_dht", "adafruit_bh1750", "board", "busio")
        }
        FlakyDHT22.temperature_calls = 0
        sys.modules["adafruit_dht"] = types.SimpleNamespace(DHT22=FlakyDHT22)
        sys.modules["adafruit_bh1750"] = types.SimpleNamespace(BH1750=FakeBH1750)
        sys.modules["board"] = types.SimpleNamespace(D4=object(), SDA=object(), SCL=object())
        sys.modules["busio"] = types.SimpleNamespace(I2C=lambda scl, sda: object())

    def tearDown(self) -> None:
        for name, original in self.original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    def test_dht_checksum_failure_is_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings(
                {
                    "GREENHOUSE_DATA_DIR": temp_dir,
                    "GREENHOUSE_DB_PATH": str(Path(temp_dir) / "test.db"),
                    "GREENHOUSE_READ_TOKEN": "read-secret",
                    "GREENHOUSE_LOCAL_BASE_URL": "http://127.0.0.1:8000",
                    "GREENHOUSE_DHT_RETRY_ATTEMPTS": "2",
                    "GREENHOUSE_DHT_RETRY_DELAY_SECONDS": "0",
                }
            )

            reading = RaspberryPiSensorReader(settings).read()

            self.assertEqual(reading.temperature_c, 23.4)
            self.assertEqual(reading.humidity_pct, 56.7)
            self.assertEqual(reading.light_lux, 321.0)
            self.assertIsNone(reading.error)
            self.assertEqual(FlakyDHT22.temperature_calls, 2)


if __name__ == "__main__":
    unittest.main()
