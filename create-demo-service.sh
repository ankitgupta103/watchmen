#!/bin/bash
# Run Demo Service Script
set -e # Exit on any error

# Get the actual user (not root when using sudo)
if [[ -n "$SUDO_USER" ]]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER="$USER"
fi

# Set user-specific paths
USER_HOME="/home/$ACTUAL_USER"
CAMERA_IMAGE_FOLDER="$USER_HOME/images"
EVENT_OUTPUT_FOLDER="$USER_HOME/processed_images"
ENV_FILE_PATH="$USER_HOME/.bashrc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SERVICE_NAME="run-demob"
SERVICE_FILE="${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_FILE_PATH="${SCRIPT_DIR}/run_demob.py"
SYSTEMD_DIR="/etc/systemd/system"

echo -e "${BLUE}=== Run Demo Service Setup ===${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Display user information
print_status "Setting up service for user: $ACTUAL_USER"
print_status "User home directory: $USER_HOME"

# Check if Python script exists
if [[ ! -f "$PYTHON_FILE_PATH" ]]; then
    print_error "Python script not found: $PYTHON_FILE_PATH"
    exit 1
fi

print_status "Found Python script: $PYTHON_FILE_PATH"

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed or not in PATH"
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p "$CAMERA_IMAGE_FOLDER" "$EVENT_OUTPUT_FOLDER"
chown $ACTUAL_USER:$ACTUAL_USER "$CAMERA_IMAGE_FOLDER" "$EVENT_OUTPUT_FOLDER" 2>/dev/null || print_warning "Could not change ownership of directories"

# Create the service file
print_status "Creating service file..."
cat > "${SYSTEMD_DIR}/${SERVICE_FILE}" << EOF
[Unit]
Description=Run Demo Service
After=multi-user.target network.target
Wants=multi-user.target

#
[Service]
Type=simple
ExecStart=/bin/bash -lic 'source ${ENV_FILE_PATH} && python ${PYTHON_FILE_PATH} 2>&1 | tee -a ${USER_HOME}/run_demob_service.log'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# User and Group
User=$ACTUAL_USER
Group=$ACTUAL_USER

# Working Directory
WorkingDirectory=${SCRIPT_DIR}

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions for the service file
chmod 644 "${SYSTEMD_DIR}/${SERVICE_FILE}"
print_status "Service file created: ${SYSTEMD_DIR}/${SERVICE_FILE}"

# Reload systemd to recognize the new service
print_status "Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service (start on boot)
print_status "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service
print_status "Starting the service..."
systemctl start "$SERVICE_NAME"

# Wait a moment for the service to start
sleep 2

# Check service status
print_status "Checking service status..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_status "Service is running successfully!"
else
    print_error "Service failed to start. Checking status..."
    systemctl status "$SERVICE_NAME" --no-pager
    exit 1
fi

# Show service information
echo
echo -e "${BLUE}=== Service Setup Complete ===${NC}"
echo -e "${GREEN}Service Name:${NC} $SERVICE_NAME"
echo -e "${GREEN}User:${NC} $ACTUAL_USER"
echo -e "${GREEN}Camera Images Folder:${NC} $CAMERA_IMAGE_FOLDER"
echo -e "${GREEN}Event Output Folder:${NC} $EVENT_OUTPUT_FOLDER"
echo -e "${GREEN}Service File:${NC} ${SYSTEMD_DIR}/${SERVICE_FILE}"
echo -e "${GREEN}Log Files:${NC} $USER_HOME/run_demob_service.log and $USER_HOME/run_demob_service_error.log"
echo

# Useful commands
echo -e "${BLUE}=== Useful Commands ===${NC}"
echo -e "${YELLOW}Check service status:${NC} sudo systemctl status $SERVICE_NAME"
echo -e "${YELLOW}View service logs:${NC} sudo journalctl -u $SERVICE_NAME -f"
echo -e "${YELLOW}View file logs:${NC} tail -f $USER_HOME/run_demob_service.log"
echo -e "${YELLOW}Stop service:${NC} sudo systemctl stop $SERVICE_NAME"
echo -e "${YELLOW}Start service:${NC} sudo systemctl start $SERVICE_NAME"
echo -e "${YELLOW}Restart service:${NC} sudo systemctl restart $SERVICE_NAME"
echo -e "${YELLOW}Disable service:${NC} sudo systemctl disable $SERVICE_NAME"
echo

# Show current status
echo -e "${BLUE}=== Current Service Status ===${NC}"
systemctl status "$SERVICE_NAME" --no-pager

print_status "Setup completed successfully!"
print_status "The service will automatically start on system boot."
print_status "Logs will be saved to both journalctl and $USER_HOME/run_demob_service.log"