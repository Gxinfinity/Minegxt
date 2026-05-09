#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/mineruhi}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$APP_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. Install it first, for example: sudo apt-get update && sudo apt-get install -y ffmpeg"
  exit 1
fi

$PYTHON_BIN -m venv .venv
. .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Edit .env before starting the service."
fi

cat <<MSG
VPS setup complete.
Next steps:
1. Edit $APP_DIR/.env with real credentials.
2. Copy deploy/ruhi.service.example to /etc/systemd/system/ruhi.service.
3. Run: sudo systemctl daemon-reload && sudo systemctl enable --now ruhi
MSG
