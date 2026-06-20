from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))

from greenhouse_monitor.config import load_settings
from greenhouse_monitor.pairing import build_pairing_code, decode_pairing_code


class PairingTestCase(unittest.TestCase):
    def test_pairing_code_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings(
                {
                    "GREENHOUSE_DATA_DIR": temp_dir,
                    "GREENHOUSE_DB_PATH": str(Path(temp_dir) / "test.db"),
                    "GREENHOUSE_READ_TOKEN": "read-secret",
                    "GREENHOUSE_LOCAL_BASE_URL": "http://greenhouse.local:8000",
                }
            )

            payload = decode_pairing_code(build_pairing_code(settings))

            self.assertEqual(payload["version"], 1)
            self.assertEqual(payload["read_token"], "read-secret")
            self.assertEqual(payload["local_base_url"], "http://greenhouse.local:8000")


if __name__ == "__main__":
    unittest.main()

