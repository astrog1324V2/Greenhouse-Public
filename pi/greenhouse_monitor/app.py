from __future__ import annotations

from datetime import datetime, timezone
from hmac import compare_digest
from io import BytesIO
from typing import Any

from flask import Flask, Response, jsonify, request

from .config import Settings
from .db import StoredReading, count_readings, fetch_history, fetch_latest_reading
from .pairing import build_pairing_code, build_pairing_payload


def create_app(settings: Settings) -> Flask:
    app = Flask(__name__)
    app.config["SETTINGS"] = settings

    @app.before_request
    def protect_app_api() -> Response | None:
        if request.endpoint in {"app_latest", "app_history"}:
            return _require_bearer_token(settings.read_token)
        return None

    @app.get("/")
    def index() -> Response:
        return Response(_render_home(settings), mimetype="text/html")

    @app.get("/setup")
    def setup() -> Response:
        return Response(_render_setup(settings), mimetype="text/html")

    @app.get("/setup/pairing.svg")
    def pairing_svg() -> Response:
        try:
            import qrcode
            import qrcode.image.svg
        except ImportError:
            return jsonify({"error": "qrcode package is not installed."}), 503

        code = build_pairing_code(settings)
        image = qrcode.make(code, image_factory=qrcode.image.svg.SvgImage)
        buffer = BytesIO()
        image.save(buffer)
        return Response(buffer.getvalue(), mimetype="image/svg+xml")

    @app.get("/api/v1/pairing")
    def pairing() -> Response:
        payload = build_pairing_payload(settings)
        return jsonify({"code": build_pairing_code(settings), "payload": payload})

    @app.get("/health")
    def health() -> Response:
        latest = fetch_latest_reading(settings.db_path)
        return jsonify(
            {
                "status": "ok",
                "timestamp_utc": _utc_now_iso(),
                "device_id": settings.device_id,
                "reading_count": count_readings(settings.db_path),
                "latest_age_seconds": _age_seconds(latest.measured_at_utc) if latest else None,
            }
        )

    @app.get("/api/v1/app/latest")
    def app_latest() -> Response:
        latest = fetch_latest_reading(settings.db_path)
        return jsonify(_latest_payload(settings, latest))

    @app.get("/api/v1/app/history")
    def app_history() -> Response:
        hours = _bounded_int(request.args.get("hours"), default=24, minimum=1, maximum=168)
        readings = fetch_history(settings.db_path, hours=hours)
        return jsonify(
            {
                "generated_at_utc": _utc_now_iso(),
                "device_id": settings.device_id,
                "hours": hours,
                "readings": [_reading_payload(settings, reading) for reading in readings],
            }
        )

    return app


def _require_bearer_token(expected_token: str) -> Response | None:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, supplied_token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not supplied_token:
        return jsonify({"error": "Missing read bearer token."}), 401
    if not compare_digest(supplied_token.strip(), expected_token):
        return jsonify({"error": "Invalid read bearer token."}), 401
    return None


def _latest_payload(settings: Settings, reading: StoredReading | None) -> dict[str, Any]:
    return {
        "generated_at_utc": _utc_now_iso(),
        "device_id": settings.device_id,
        "device_name": settings.device_name,
        "current": _reading_payload(settings, reading) if reading else None,
    }


def _reading_payload(settings: Settings, reading: StoredReading | None) -> dict[str, Any] | None:
    if reading is None:
        return None
    age_seconds = _age_seconds(reading.measured_at_utc)
    return {
        "temperature_c": reading.temperature_c,
        "humidity_pct": reading.humidity_pct,
        "light_lux": reading.light_lux,
        "measurement_at_utc": reading.measured_at_utc,
        "age_seconds": age_seconds,
        "is_stale": age_seconds > settings.stale_seconds,
        "error": reading.error,
    }


def _render_home(settings: Settings) -> str:
    latest = fetch_latest_reading(settings.db_path)
    current = _reading_payload(settings, latest)
    if current is None:
        body = "<p>No readings yet. The collector should populate this page soon.</p>"
    else:
        body = f"""
        <dl>
          <dt>Temperature</dt><dd>{_format_value(current["temperature_c"], "C")}</dd>
          <dt>Humidity</dt><dd>{_format_value(current["humidity_pct"], "%")}</dd>
          <dt>Light</dt><dd>{_format_value(current["light_lux"], "lux")}</dd>
          <dt>Updated</dt><dd>{current["measurement_at_utc"]}</dd>
          <dt>Status</dt><dd>{"stale" if current["is_stale"] else "fresh"}</dd>
        </dl>
        """
    return _page(
        "Greenhouse Monitor",
        f"""
        <h1>{settings.device_name}</h1>
        {body}
        <p><a href="/setup">Open setup and pairing</a></p>
        """,
    )


def _render_setup(settings: Settings) -> str:
    code = build_pairing_code(settings)
    return _page(
        "Greenhouse Monitor Setup",
        f"""
        <h1>Pair {settings.device_name}</h1>
        <p>Open the iOS app and scan this QR code, or paste the manual pairing code.</p>
        <img alt="Pairing QR code" src="/setup/pairing.svg" width="240" height="240">
        <label for="pairing-code">Manual pairing code</label>
        <textarea id="pairing-code" readonly rows="8">{code}</textarea>
        <p class="muted">Local API: {settings.local_base_url}</p>
        """,
    )


def _page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7f2;
      color: #182115;
    }}
    main {{
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 20px;
    }}
    h1 {{ margin-top: 0; }}
    dl {{
      display: grid;
      grid-template-columns: minmax(120px, 180px) 1fr;
      gap: 12px;
      padding: 20px;
      background: white;
      border: 1px solid #dce4d6;
      border-radius: 8px;
    }}
    dt {{ font-weight: 700; }}
    textarea {{
      box-sizing: border-box;
      width: 100%;
      margin-top: 8px;
      padding: 12px;
      border: 1px solid #b9c7b0;
      border-radius: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    img {{
      display: block;
      margin: 20px 0;
      background: white;
      border: 1px solid #dce4d6;
      border-radius: 8px;
      padding: 12px;
    }}
    .muted {{ color: #596354; }}
  </style>
</head>
<body>
  <main>{content}</main>
</body>
</html>"""


def _format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "unavailable"
    return f"{value} {unit}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _age_seconds(timestamp_utc: str) -> int:
    parsed = datetime.fromisoformat(timestamp_utc)
    return int((datetime.now(timezone.utc) - parsed).total_seconds())


def _bounded_int(value: str | None, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    return max(minimum, min(maximum, parsed))

