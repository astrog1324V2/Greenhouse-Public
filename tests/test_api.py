from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))

from greenhouse_monitor.app import create_app
from greenhouse_monitor.config import load_settings
from greenhouse_monitor.db import initialize_database, insert_reading
from greenhouse_monitor.sensors import SensorReading


class APITestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.settings = load_settings(
            {
                "GREENHOUSE_DATA_DIR": str(base),
                "GREENHOUSE_DB_PATH": str(base / "test.db"),
                "GREENHOUSE_READ_TOKEN": "read-secret",
                "GREENHOUSE_LOCAL_BASE_URL": "http://127.0.0.1:8000",
                "GREENHOUSE_STALE_SECONDS": "300",
            }
        )
        initialize_database(self.settings.db_path)
        self.app = create_app(self.settings)
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_latest_requires_read_token(self) -> None:
        response = self.client.get("/api/v1/app/latest")
        self.assertEqual(response.status_code, 401)

        authorized = self.client.get(
            "/api/v1/app/latest",
            headers={"Authorization": "Bearer read-secret"},
        )
        self.assertEqual(authorized.status_code, 200)

    def test_latest_returns_current_reading(self) -> None:
        insert_reading(
            self.settings.db_path,
            self.settings.device_id,
            SensorReading(temperature_c=24.0, humidity_pct=55.0, light_lux=500.0),
        )

        response = self.client.get(
            "/api/v1/app/latest",
            headers={"Authorization": "Bearer read-secret"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["device_id"], "greenhouse-pi")
        self.assertEqual(payload["current"]["temperature_c"], 24.0)
        self.assertFalse(payload["current"]["is_stale"])

    def test_history_returns_recent_readings(self) -> None:
        insert_reading(
            self.settings.db_path,
            self.settings.device_id,
            SensorReading(temperature_c=20.0, humidity_pct=50.0, light_lux=100.0),
        )

        response = self.client.get(
            "/api/v1/app/history?hours=24",
            headers={"Authorization": "Bearer read-secret"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["hours"], 24)
        self.assertEqual(len(payload["readings"]), 1)


if __name__ == "__main__":
    unittest.main()

