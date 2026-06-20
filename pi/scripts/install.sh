#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="/opt/greenhouse-monitor/app"
VENV_DIR="/opt/greenhouse-monitor/venv"
DATA_DIR="/var/lib/greenhouse-monitor"
CONFIG_DIR="/etc/greenhouse-monitor"

apt-get update
GPIOD_PACKAGE=""
if apt-cache show libgpiod3 >/dev/null 2>&1; then
  GPIOD_PACKAGE="libgpiod3"
elif apt-cache show libgpiod2 >/dev/null 2>&1; then
  GPIOD_PACKAGE="libgpiod2"
fi
apt-get install -y python3-venv python3-pip rsync i2c-tools gpiod ${GPIOD_PACKAGE}

id -u greenhouse >/dev/null 2>&1 || useradd --system --home "${DATA_DIR}" --shell /usr/sbin/nologin greenhouse
for group in gpio i2c; do
  if getent group "${group}" >/dev/null; then
    usermod -aG "${group}" greenhouse
  fi
done

mkdir -p "${APP_DIR}" "${DATA_DIR}" "${CONFIG_DIR}"
rsync -a --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "data" \
  "${ROOT_DIR}/" "${APP_DIR}/"

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"
"${VENV_DIR}/bin/python" -m pip install -e "${APP_DIR}"

if [[ ! -f "${CONFIG_DIR}/config.env" ]]; then
  cat > "${CONFIG_DIR}/config.env" <<'ENV'
GREENHOUSE_HOST=0.0.0.0
GREENHOUSE_PORT=8000
GREENHOUSE_DATA_DIR=/var/lib/greenhouse-monitor
GREENHOUSE_DB_PATH=/var/lib/greenhouse-monitor/greenhouse.db
GREENHOUSE_DEVICE_ID=greenhouse-pi
GREENHOUSE_DEVICE_NAME=Greenhouse Monitor
GREENHOUSE_SAMPLE_INTERVAL_SECONDS=60
GREENHOUSE_STALE_SECONDS=300
GREENHOUSE_DHT_PIN=D4
GREENHOUSE_DHT_RETRY_ATTEMPTS=4
GREENHOUSE_DHT_RETRY_DELAY_SECONDS=2.0
GREENHOUSE_I2C_SDA=SDA
GREENHOUSE_I2C_SCL=SCL
GREENHOUSE_BH1750_ADDRESS=0x23
GREENHOUSE_MOCK_SENSORS=0
ENV
fi

chown -R greenhouse:greenhouse "${DATA_DIR}"
chmod 700 "${DATA_DIR}"
cp "${APP_DIR}/pi/systemd/greenhouse-monitor.service" /etc/systemd/system/greenhouse-monitor.service

systemctl daemon-reload
systemctl enable greenhouse-monitor.service
systemctl restart greenhouse-monitor.service

echo "Greenhouse Monitor is installed."
echo "Open http://<your-pi-ip>:8000/setup on your local network."
