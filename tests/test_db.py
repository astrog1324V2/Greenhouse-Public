from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))

from greenhouse_monitor.db import count_readings, fetch_history, fetch_latest_reading, initialize_database, insert_reading
from greenhouse_monitor.sensors import SensorReading


class DatabaseTestCase(unittest.TestCase):
    def test_insert_latest_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "greenhouse.db"
            initialize_database(db_path)

            insert_reading(
                db_path,
                "greenhouse-pi",
                SensorReading(temperature_c=22.5, humidity_pct=61.0, light_lux=400.0),
            )

            self.assertEqual(count_readings(db_path), 1)
            latest = fetch_latest_reading(db_path)
            self.assertIsNotNone(latest)
            assert latest is not None
            self.assertEqual(latest.temperature_c, 22.5)
            self.assertEqual(latest.device_id, "greenhouse-pi")

            history = fetch_history(db_path, hours=24)
            self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()

