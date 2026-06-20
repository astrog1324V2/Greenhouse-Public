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

        self._dht = adafruit_dht.DHT22(dht_pin)
        self._i2c = busio.I2C(scl_pin, sda_pin)
        self._light = adafruit_bh1750.BH1750(self._i2c, address=settings.bh1750_address)

    def read(self) -> SensorReading:
        errors: list[str] = []
        temperature_c: float | None = None
        humidity_pct: float | None = None
        light_lux: float | None = None

        try:
            temperature_c = round(float(self._dht.temperature), 1)
            humidity_pct = round(float(self._dht.humidity), 1)
        except RuntimeError as exc:
            errors.append(f"dht:{exc}")

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


def make_sensor_reader(settings: Settings) -> SensorReader:
    if settings.mock_sensors:
        return MockSensorReader()
    return RaspberryPiSensorReader(settings)

