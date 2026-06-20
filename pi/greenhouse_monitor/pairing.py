from __future__ import annotations

import base64
import json
from typing import Any

from .config import Settings


def build_pairing_payload(settings: Settings) -> dict[str, Any]:
    return {
        "version": 1,
        "name": settings.device_name,
        "device_id": settings.device_id,
        "local_base_url": settings.local_base_url,
        "remote_base_url": settings.remote_base_url,
        "read_token": settings.read_token,
    }


def encode_pairing_code(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def decode_pairing_code(code: str) -> dict[str, Any]:
    cleaned = code.strip()
    padding = "=" * (-len(cleaned) % 4)
    data = base64.urlsafe_b64decode(cleaned + padding)
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Pairing code did not contain an object.")
    return payload


def build_pairing_code(settings: Settings) -> str:
    return encode_pairing_code(build_pairing_payload(settings))

