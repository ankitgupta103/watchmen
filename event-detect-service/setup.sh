#!/bin/bash

# Event Detector Service Setup Script
# This script sets up the event detection service as a systemd service

set -e  # Exit on any error

# Function to validate input with retries
validate_input() {
    local prompt="$1"
    local var_name="$2"
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        read -p "$prompt" input_value
        if [ -n "$input_value" ]; then
            eval "$var_name='$input_value'"
            return 0
        fi
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo "Error: Input cannot be empty. Please try again. ($((max_retries - retry_count)) attempts remaining)"
        fi
    done
    
    echo "Error: Maximum retries reached. Input cannot be empty."
    return 1
}

# Validate camera images folder
if ! validate_input "Enter the complete path to the camera images folder: " "CAMERA_IMAGE_FOLDER"; then
    echo "Error: Failed to get valid camera images folder path"
    exit 1
fi

# Validate events output folder
if ! validate_input "Enter the complete path to the events output folder: " "EVENT_OUTPUT_FOLDER"; then
    echo "Error: Failed to get valid events output folder path"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="event-detector"
SERVICE_FILE="${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_FILE_PATH="${SCRIPT_DIR}/event_detector.py"
SYSTEMD_DIR="/etc/systemd/system"
# CAMERA_IMAGE_FOLDER="/home/ankit/Documents/images" # input folder
# EVENT_OUTPUT_FOLDER="/home/ankit/Documents/processed_images"  # output folder

echo -e "${BLUE}=== Event Detector Service Setup ===${NC}"

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

# Check if required Python packages are available
print_status "Checking Python dependencies..."
python3 -c "import cv2, ultralytics" 2>/dev/null || {
    print_warning "Required Python packages (opencv-python, ultralytics) may not be installed"
    print_warning "Install them with: pip3 install opencv-python ultralytics"
}

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p "$CAMERA_IMAGE_FOLDER" "$EVENT_OUTPUT_FOLDER"
chown ankit:ankit "$CAMERA_IMAGE_FOLDER" "$EVENT_OUTPUT_FOLDER" 2>/dev/null || print_warning "Could not change ownership of directories"

# Create the service file
print_status "Creating service file..."
# Validate environment file path
if ! validate_input "Enter the complete filepath to source the environment: " "ENV_FILE_PATH"; then
    print_error "Failed to get valid environment file path"
    exit 1
fi

cat > "${SYSTEMD_DIR}/${SERVICE_FILE}" << EOF
[Unit]
Description=Event Detection Service - YOLO Object Detection for Image Monitoring
After=multi-user.target network.target
Wants=multi-user.target

# 
[Service]
Type=simple
ExecStart=/bin/bash -lic 'source ${ENV_FILE_PATH} && python ${PYTHON_FILE_PATH} ${CAMERA_IMAGE_FOLDER} --output ${EVENT_OUTPUT_FOLDER}'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# User and Group
User=ankit
Group=ankit

# Working Directory
WorkingDirectory=${SCRIPT_DIR}

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions for the service file
chmod 644 "${SYSTEMD_DIR}/${SERVICE_FILE}"
print_status "Service file created: ${SYSTEMD_DIR}/${SERVICE_FILE}"

# Make Python script executable
chmod +x "$PYTHON_FILE_PATH"
print_status "Made Python script executable"

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
echo -e "${GREEN}Camera Images Folder:${NC} $CAMERA_IMAGE_FOLDER"
echo -e "${GREEN}Output Folder:${NC} $EVENT_OUTPUT_FOLDER"
echo -e "${GREEN}Service File:${NC} ${SYSTEMD_DIR}/${SERVICE_FILE}"
echo

# Useful commands
echo -e "${BLUE}=== Useful Commands ===${NC}"
echo -e "${YELLOW}Check service status:${NC} sudo systemctl status $SERVICE_NAME"
echo -e "${YELLOW}View service logs:${NC} sudo journalctl -u $SERVICE_NAME -f"
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
print_status "Place images in: $CAMERA_IMAGE_FOLDER"
print_status "Processed images will be saved to: $EVENT_OUTPUT_FOLDER"