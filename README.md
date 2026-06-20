# Greenhouse Monitor

Open-source local greenhouse monitor for a Raspberry Pi Zero 2 W, a DHT22
temperature/humidity sensor, a BH1750 light sensor, and a native iOS/iPadOS app.

This public MVP is local-first:

- the Raspberry Pi reads the sensors directly
- the Pi stores history locally in SQLite
- the iOS app reads from the Pi over local Wi-Fi
- optional hosted/self-hosted API support is planned, but not required for local use

## Repository layout

- `pi/`: Python Raspberry Pi service, API, sensor reader, systemd installer
- `ios/GreenhouseMonitor/`: SwiftUI app that opens in Xcode
- `hardware/enclosure/`: 3D-print enclosure notes and `.3mf` drop folder
- `tests/`: Python unit tests for the Pi service

## Hardware MVP

Default wiring:

- Raspberry Pi Zero 2 W
- DHT22 data on GPIO4
- BH1750 on I2C bus 1
- I2C SDA on GPIO2
- I2C SCL on GPIO3
- 3.3V power for both sensors

No OLED, ESP32, or Windows server is part of this MVP.

## Run locally with mock sensors

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "Flask>=3.0,<4.0" "qrcode>=7.4,<9.0"
PYTHONPATH=pi GREENHOUSE_MOCK_SENSORS=1 python -m greenhouse_monitor --data-dir ./data
```

Open:

```text
http://127.0.0.1:8000/setup
```

The setup page shows a pairing code and QR image for the iOS app.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Raspberry Pi install

On Raspberry Pi OS Lite:

```bash
cd Greenhouse-Public
sudo pi/scripts/install.sh
```

Before plugging in the BH1750, enable I2C with `sudo raspi-config` under
`Interface Options`.

The installer creates a Python virtual environment in `/opt/greenhouse-monitor`,
stores data in `/var/lib/greenhouse-monitor`, writes configuration to
`/etc/greenhouse-monitor/config.env`, and enables a `systemd` service.

After install, visit:

```text
http://<your-pi-ip>:8000/setup
```

## iOS/iPadOS app

Open `ios/GreenhouseMonitor/GreenhouseMonitor.xcodeproj` in Xcode and run it on
the simulator or a device on the same Wi-Fi network as the Pi.

Pairing options:

- scan the QR code from the Pi setup page
- paste/type the manual pairing code from the Pi setup page
- enter the Pi URL and read token manually in settings

## Future remote access

The app and Pi are structured for three modes:

- local Wi-Fi
- self-hosted API
- future subscription API

For the future subscription API, the Pi should remain the source of truth and
push only the latest reading to hosted infrastructure. Full history stays local
on the Pi.
