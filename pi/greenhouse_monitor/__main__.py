from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from .app import create_app
from .collector import ReadingCollector
from .config import load_settings
from .db import initialize_database
from .sensors import make_sensor_reader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Greenhouse Monitor Pi service.")
    parser.add_argument("--host", help="Bind host. Defaults to GREENHOUSE_HOST or 0.0.0.0.")
    parser.add_argument("--port", type=int, help="Bind port. Defaults to GREENHOUSE_PORT or 8000.")
    parser.add_argument("--data-dir", type=Path, help="Data directory for SQLite and generated tokens.")
    parser.add_argument("--mock", action="store_true", help="Use mock sensor readings.")
    parser.add_argument("--no-collector", action="store_true", help="Serve API without starting sampling.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    env = dict(os.environ)
    if args.data_dir:
        env["GREENHOUSE_DATA_DIR"] = str(args.data_dir)
        env.setdefault("GREENHOUSE_DB_PATH", str(args.data_dir / "greenhouse.db"))
    if args.host:
        env["GREENHOUSE_HOST"] = args.host
    if args.port:
        env["GREENHOUSE_PORT"] = str(args.port)
    if args.mock:
        env["GREENHOUSE_MOCK_SENSORS"] = "1"

    settings = load_settings(env)
    settings.ensure_directories()
    initialize_database(settings.db_path)

    collector: ReadingCollector | None = None
    if not args.no_collector:
        collector = ReadingCollector(settings, make_sensor_reader(settings))
        collector.start()

    app = create_app(settings)
    try:
        from waitress import serve

        serve(app, host=settings.host, port=settings.port)
    except ImportError:
        app.run(host=settings.host, port=settings.port, debug=False)
    finally:
        if collector:
            collector.stop()


if __name__ == "__main__":
    main()

