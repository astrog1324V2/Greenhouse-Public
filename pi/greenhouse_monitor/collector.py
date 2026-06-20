from __future__ import annotations

import logging
import threading
import time

from .config import Settings
from .db import insert_reading
from .sensors import SensorReader

LOGGER = logging.getLogger(__name__)


class ReadingCollector:
    def __init__(self, settings: Settings, sensor_reader: SensorReader) -> None:
        self._settings = settings
        self._sensor_reader = sensor_reader
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def sample_once(self) -> None:
        reading = self._sensor_reader.read()
        insert_reading(self._settings.db_path, self._settings.device_id, reading)
        if reading.error:
            LOGGER.warning("Sensor read completed with errors: %s", reading.error)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="greenhouse-collector", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                self.sample_once()
            except Exception:
                LOGGER.exception("Unexpected collector failure")

            elapsed = time.monotonic() - started
            remaining = max(1.0, self._settings.sample_interval_seconds - elapsed)
            self._stop_event.wait(remaining)

