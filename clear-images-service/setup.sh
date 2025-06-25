#!/bin/bash

# setup.sh - Creates a one-time startup cleanup service
# Run this script as the user whose home directory should be cleaned

set -e

# Get actual user (handles both direct execution and sudo execution)
if [[ -n "$SUDO_USER" ]]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER="$USER"
fi

HOME_DIR="/home/$ACTUAL_USER"

echo "Setting up cleanup service for user: $ACTUAL_USER"

# Verify directories exist
if [ ! -d "$HOME_DIR/processed_images" ]; then
    echo "Warning: $HOME_DIR/processed_images does not exist. Creating it..."
    mkdir -p "$HOME_DIR/processed_images/critical"
fi

if [ ! -d "$HOME_DIR/processed_images/critical" ]; then
    echo "Warning: $HOME_DIR/processed_images/critical does not exist. Creating it..."
    mkdir -p "$HOME_DIR/processed_images/critical"
fi

# Create the cleanup script
CLEANUP_SCRIPT="/usr/local/bin/startup-cleanup-$ACTUAL_USER.sh"

echo "Creating cleanup script at $CLEANUP_SCRIPT..."

sudo tee "$CLEANUP_SCRIPT" > /dev/null << EOF
#!/bin/bash
# Startup cleanup script for user: $ACTUAL_USER
# This script runs once on startup to clean processed_images directories

set -e

echo "Running startup cleanup for user: $ACTUAL_USER"

# Clean critical directory
echo "Cleaning $HOME_DIR/processed_images/critical..."
cd "$HOME_DIR/processed_images/critical"
rm -rf *

# Clean directories starting with 0
echo "Cleaning directories starting with '0' in $HOME_DIR/processed_images..."
cd "$HOME_DIR/processed_images"
rm -rf 0*

echo "Startup cleanup completed successfully"

# Disable the service after first run to ensure it only runs once
echo "Disabling startup-cleanup-$ACTUAL_USER service..."
systemctl disable startup-cleanup-$ACTUAL_USER.service

echo "Cleanup service has been disabled after first run"
EOF

# Make cleanup script executable
sudo chmod +x "$CLEANUP_SCRIPT"

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/startup-cleanup-$ACTUAL_USER.service"

echo "Creating systemd service at $SERVICE_FILE..."

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Startup Cleanup Service for $ACTUAL_USER
After=multi-user.target
Wants=multi-user.target

[Service]
Type=oneshot
ExecStart=$CLEANUP_SCRIPT
RemainAfterExit=yes
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service
echo "Enabling startup-cleanup-$ACTUAL_USER service..."
sudo systemctl enable startup-cleanup-$ACTUAL_USER.service

echo ""
echo "Setup completed successfully!"
echo ""
echo "The service 'startup-cleanup-$ACTUAL_USER' has been created and enabled."
echo "It will run once on the next system startup and then disable itself."
echo ""
echo "To manually run the cleanup now (for testing): sudo systemctl start startup-cleanup-$ACTUAL_USER.service"
echo "To check service status: sudo systemctl status startup-cleanup-$ACTUAL_USER.service"
echo "To view service logs: sudo journalctl -u startup-cleanup-$ACTUAL_USER.service"
echo ""
echo "Files created:"
echo "- Cleanup script: $CLEANUP_SCRIPT"
echo "- Service file: $SERVICE_FILE"
EOF