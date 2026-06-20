from __future__ import annotations

import socket


def detect_lan_base_url(port: int) -> str:
    return f"http://{_detect_lan_ip()}:{port}"


def _detect_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.2)
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"

