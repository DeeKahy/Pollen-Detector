#!/usr/bin/env bash
# Install the pollen device software on a Raspberry Pi (Raspberry Pi OS Bookworm or newer).
# Run from inside the device/ folder:   ./install.sh
set -euo pipefail
cd "$(dirname "$0")"
DIR="$(pwd)"
USER_NAME="$(whoami)"

echo "== Installing system packages"
sudo apt-get update
sudo apt-get install -y python3-picamera2 python3-gpiozero python3-lgpio \
    python3-flask python3-requests python3-yaml python3-pil

# user needs gpio + video group access (default 'pi'-style users already have it)
sudo usermod -aG gpio,video "$USER_NAME" || true

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  sed -i "s/^device_id: .*/device_id: $(hostname)/" config.yaml
  echo "== Created config.yaml (device_id = $(hostname)) - edit it to set upload server/token"
fi

echo "== Installing systemd service 'pollen'"
sed -e "s|@USER@|$USER_NAME|g" -e "s|@DIR@|$DIR|g" pollen.service | sudo tee /etc/systemd/system/pollen.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable pollen

cat <<EOF

Done.
  Test wiring first:   python3 -m pollen_device.hwtest
  Start service:       sudo systemctl start pollen
  Logs:                journalctl -u pollen -f
  Web UI:              http://$(hostname -I | awk '{print $1}'):8080
EOF
