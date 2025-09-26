#!/usr/bin/env bash
set -euo pipefail

# Automated setup script for Ubuntu/Debian servers
# - Installs ffmpeg and Python toolchain if missing
# - Creates Python venv and installs requirements
# - Detects ffmpeg path and configures FFMPEG_PATH
# - Creates and enables a systemd service to run the bot persistently
#
# Usage:
#   sudo bash setup_server.sh
#
# Notes:
# - Run this script from the project root directory where bot.py and requirements.txt exist
# - You can re-run this script any time; it is idempotent and will update the service if needed

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="downloader-bot"
VENV_DIR="$PROJECT_DIR/.venv"
PY_BIN="python3"
PIP_BIN="pip3"
SVC_USER="${SUDO_USER:-$(whoami)}"

info() { echo -e "\033[1;34m[INFO]\033[0m $*"; }
success() { echo -e "\033[1;32m[SUCCESS]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; }

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    error "Please run as root: sudo bash setup_server.sh"
    exit 1
  fi
}

ensure_apt() {
  if ! command -v apt-get >/dev/null 2>&1; then
    error "This script requires apt-get (Ubuntu/Debian)."
    exit 1
  fi
}

install_packages() {
  info "Installing required packages (ffmpeg, python3, venv, pip)..."
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ffmpeg \
    python3 \
    python3-venv \
    python3-pip
}

ensure_python_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating Python virtual environment at $VENV_DIR"
    $PY_BIN -m venv "$VENV_DIR"
  else
    info "Virtual environment already exists at $VENV_DIR"
  fi
  # Upgrade pip and install requirements
  info "Installing Python dependencies from requirements.txt"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip wheel
  if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
    "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
  else
    warn "requirements.txt not found; skipping dependency installation"
  fi
}

resolve_ffmpeg() {
  local FF_BIN
  if command -v ffmpeg >/dev/null 2>&1; then
    FF_BIN="$(command -v ffmpeg)"
  elif [[ -x "/snap/bin/ffmpeg" ]]; then
    FF_BIN="/snap/bin/ffmpeg"
  else
    error "ffmpeg not found even after installation. Please verify manually."
    exit 1
  fi
  echo "$FF_BIN"
}

write_systemd_service() {
  local FF_BIN="$1"
  local SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

  info "Writing systemd service to $SERVICE_FILE"
  cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=DownloaderYT-V1 Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SVC_USER}
WorkingDirectory=${PROJECT_DIR}
# Ensure FFmpeg is picked up by the app
Environment=FFMPEG_PATH=${FF_BIN}
# Provide a full PATH including snap for ffmpeg if installed via Snap
Environment=PYTHONUNBUFFERED=1
Environment="PATH=${PROJECT_DIR}/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/snap/bin"
ExecStart=${PROJECT_DIR}/.venv/bin/python ${PROJECT_DIR}/bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1 || true
  info "Starting (or restarting) ${SERVICE_NAME}"
  systemctl restart "${SERVICE_NAME}"
  sleep 1 || true
  systemctl --no-pager --full status "${SERVICE_NAME}" || true
}

main() {
  require_root
  ensure_apt
  install_packages
  ensure_python_venv
  local FF_BIN
  FF_BIN="$(resolve_ffmpeg)"
  success "Detected ffmpeg at: ${FF_BIN}"
  write_systemd_service "$FF_BIN"
  success "Setup completed. Logs: journalctl -u ${SERVICE_NAME} -e"
}

main "$@"