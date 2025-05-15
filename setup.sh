#!/bin/bash
set -e

echo "Updating system..."
sudo apt update

echo "Installing system packages..."
sudo apt install -y \
    libcamera-apps \
    libcamera-dev \
    libcamera-tools \
    python3-picamera2 \
    python3-libcamera \
    python3-venv \
    python3-pip

echo "Creating venv and installing Python packages..."
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete ✅"
