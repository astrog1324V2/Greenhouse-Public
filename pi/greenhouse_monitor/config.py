from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, replace
from pathlib import Path

from .network import detect_lan_base_url


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    db_path: Path
    device_id: str
    device_name: str
    read_token: str
    sample_interval_seconds: int
    stale_seconds: int
    mock_sensors: bool
    dht_pin_name: str
    i2c_sda_name: str
    i2c_scl_name: str
    bh1750_address: int
    local_base_url: str
    remote_base_url: str | None

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def with_overrides(self, **kwargs: object) -> "Settings":
        return replace(self, **kwargs)


def load_settings(env: dict[str, str] | None = None) -> Settings:
    source = env or os.environ
    data_dir = Path(source.get("GREENHOUSE_DATA_DIR", "/var/lib/greenhouse-monitor")).expanduser()
    db_path = Path(source.get("GREENHOUSE_DB_PATH", data_dir / "greenhouse.db")).expanduser()
    host = source.get("GREENHOUSE_HOST", "0.0.0.0")
    port = int(source.get("GREENHOUSE_PORT", "8000"))
    read_token = _read_token(source, data_dir)
    local_base_url = source.get("GREENHOUSE_LOCAL_BASE_URL") or detect_lan_base_url(port)
    remote_base_url = _optional(source.get("GREENHOUSE_REMOTE_BASE_URL"))

    return Settings(
        host=host,
        port=port,
        data_dir=data_dir,
        db_path=db_path,
        device_id=source.get("GREENHOUSE_DEVICE_ID", "greenhouse-pi").strip() or "greenhouse-pi",
        device_name=source.get("GREENHOUSE_DEVICE_NAME", "Greenhouse Monitor").strip()
        or "Greenhouse Monitor",
        read_token=read_token,
        sample_interval_seconds=int(source.get("GREENHOUSE_SAMPLE_INTERVAL_SECONDS", "60")),
        stale_seconds=int(source.get("GREENHOUSE_STALE_SECONDS", "300")),
        mock_sensors=source.get("GREENHOUSE_MOCK_SENSORS", "0") == "1",
        dht_pin_name=source.get("GREENHOUSE_DHT_PIN", "D4"),
        i2c_sda_name=source.get("GREENHOUSE_I2C_SDA", "SDA"),
        i2c_scl_name=source.get("GREENHOUSE_I2C_SCL", "SCL"),
        bh1750_address=int(source.get("GREENHOUSE_BH1750_ADDRESS", "0x23"), 0),
        local_base_url=local_base_url,
        remote_base_url=remote_base_url,
    )


def _read_token(env: dict[str, str], data_dir: Path) -> str:
    configured = _optional(env.get("GREENHOUSE_READ_TOKEN"))
    if configured:
        return configured

    token_path = data_dir / "read_token"
    try:
        existing = token_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    except FileNotFoundError:
        pass

    token = secrets.token_urlsafe(32)
    data_dir.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    return token


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

