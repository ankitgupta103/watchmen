#!/bin/bash

# ==============================================================================
# Setup Script for Camera Capture Service
# ==============================================================================
# This script installs and configures the USB power cycling and image
# transfer service for a camera. It must be run with root privileges.
# ==============================================================================

OWNER_USER="ankit"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/dump-test-images.sh"

SERVICE_NAME="dump-test-images"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"

LOG_FILE="/var/log/dump-test-images.log"

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Please use 'sudo ./setup.sh'"
  exit 1
fi

cat > "$SERVICE_PATH" << EOF
[Unit]
Description=Dump Test Images Service
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
ExecStart=$SCRIPT_PATH
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
User=root

# Working Directory
WorkingDirectory=/home/ankit/Documents

[Install]
WantedBy=multi-user.target
EOF
echo "Service file created."

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
echo "Service enabled and started."

echo
echo "--- Setup Complete ---"
echo
echo "The dump test images service has been installed and started."
echo "To check the status of the service, run: sudo systemctl status $SERVICE_NAME"
echo "To view the service logs, run: sudo journalctl -u $SERVICE_NAME -f"
echo "To view the script's specific log file, run: tail -f $LOG_FILE"