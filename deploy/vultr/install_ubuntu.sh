#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-scholarcheck}"
APP_DIR="${APP_DIR:-/opt/scholarcheck/current}"
REPO_URL="${REPO_URL:-https://github.com/boundaryx01-uniquelife/scholarcheck.git}"
GIT_REF="${GIT_REF:-main}"

sudo apt update
sudo apt install -y git python3 python3-venv nginx

if ! id "${APP_USER}" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

sudo mkdir -p "$(dirname "${APP_DIR}")"
if [ ! -d "${APP_DIR}/.git" ]; then
  sudo git clone "${REPO_URL}" "${APP_DIR}"
fi

sudo git -C "${APP_DIR}" fetch --all --tags
sudo git -C "${APP_DIR}" checkout "${GIT_REF}"
sudo git -C "${APP_DIR}" pull --ff-only || true

sudo python3 -m venv "${APP_DIR}/.venv"
sudo "${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo "${APP_DIR}/.venv/bin/python" -m pip install -e "${APP_DIR}"

sudo mkdir -p "${APP_DIR}/data/sessions" "${APP_DIR}/data/projects" "${APP_DIR}/data/backups" "${APP_DIR}/outputs"
sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

sudo cp "${APP_DIR}/deploy/vultr/scholarcheck.service" /etc/systemd/system/scholarcheck.service
sudo systemctl daemon-reload
sudo systemctl enable --now scholarcheck

echo "Install complete."
echo "Next: copy deploy/vultr/nginx_scholarcheck.conf to /etc/nginx/sites-available/scholarcheck and set server_name."
