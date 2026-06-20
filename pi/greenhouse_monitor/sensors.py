from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Protocol

from .config import Settings


@dataclass(frozen=True)
class SensorReading:
    temperature_c: float | None
    humidity_pct: float | None
    light_lux: float | None
    error: str | None = None


class SensorReader(Protocol):
    def read(self) -> SensorReading:
        ...


class MockSensorReader:
    def __init__(self) -> None:
        self._started = time.monotonic()

    def read(self) -> SensorReading:
        elapsed = time.monotonic() - self._started
        wave = math.sin(elapsed / 120.0)
        return SensorReading(
            temperature_c=round(22.0 + wave * 3.0, 1),
            humidity_pct=round(58.0 + wave * 8.0, 1),
            light_lux=round(max(0.0, 450.0 + wave * 220.0), 1),
        )


class RaspberryPiSensorReader:
    def __init__(self, settings: Settings) -> None:
        try:
            import adafruit_bh1750
            import adafruit_dht
            import board
            import busio
        except ImportError as exc:
            raise RuntimeError(
                "Real sensor mode requires adafruit-blinka, "
                "adafruit-circuitpython-dht, and adafruit-circuitpython-bh1750."
            ) from exc

        dht_pin = getattr(board, settings.dht_pin_name)
        scl_pin = getattr(board, settings.i2c_scl_name)
        sda_pin = getattr(board, settings.i2c_sda_name)

        try:
            self._dht = adafruit_dht.DHT22(dht_pin, use_pulseio=False)
        except TypeError:
            self._dht = adafruit_dht.DHT22(dht_pin)
        self._i2c = busio.I2C(scl_pin, sda_pin)
        self._light = adafruit_bh1750.BH1750(self._i2c, address=settings.bh1750_address)
        self._dht_retry_attempts = settings.dht_retry_attempts
        self._dht_retry_delay_seconds = settings.dht_retry_delay_seconds

    def read(self) -> SensorReading:
        errors: list[str] = []
        light_lux: float | None = None

        temperature_c, humidity_pct, dht_error = self._read_dht()
        if dht_error:
            errors.append(dht_error)

        try:
            light_lux = round(float(self._light.lux), 1)
        except RuntimeError as exc:
            errors.append(f"bh1750:{exc}")

        return SensorReading(
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            light_lux=light_lux,
            error="; ".join(errors) if errors else None,
        )

    def _read_dht(self) -> tuple[float | None, float | None, str | None]:
        last_error: Exception | None = None

        for attempt in range(self._dht_retry_attempts):
            try:
                temperature_c = round(float(self._dht.temperature), 1)
                humidity_pct = round(float(self._dht.humidity), 1)
                return temperature_c, humidity_pct, None
            except (RuntimeError, TypeError, ValueError) as exc:
                last_error = exc
                if attempt < self._dht_retry_attempts - 1:
                    time.sleep(self._dht_retry_delay_seconds)

        return None, None, f"dht:{last_error}" if last_error else "dht:unknown read failure"


def make_sensor_reader(settings: Settings) -> SensorReader:
    if settings.mock_sensors:
        return MockSensorReader()
    return RaspberryPiSensorReader(settings)
