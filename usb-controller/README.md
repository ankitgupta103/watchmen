# USB Power Cycle and Image Transfer Service

A systemd service for automated USB power cycling and image transfer operations on Raspberry Pi systems.

## Overview

This service automatically manages USB power cycling and image transfer operations. It runs as a systemd service with automatic restart capabilities and comprehensive logging.

## Prerequisites

- Have `uhubctl` installed
  - `sudo apt update`
  - `sudo apt install uhubctl`

## Installation

### 1. Create the Service File

Create the systemd service configuration:

```bash
sudo nano /etc/systemd/system/usb-cycle.service
```

### 2. Service Configuration

Copy and paste the following configuration:

```ini
[Unit]
Description=USB Power Cycle and Image Transfer Service
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
ExecStart=/home/pi/Documents/watchmen/usb-controller/usb-camera-power-cycle.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
User=root
Group=root

# Security and Permissions
PrivilegeEscalation=yes
NoNewPrivileges=no

# Environment Configuration
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="HOME=/root"

# Working Directory
WorkingDirectory=/home/pi/Documents # Path to your script's directory

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start the Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start at boot
sudo systemctl enable usb-cycle.service

# Start the service immediately
sudo systemctl start usb-cycle.service
```

## Service Management

### Basic Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start usb-cycle.service` | Start the service |
| `sudo systemctl stop usb-cycle.service` | Stop the service |
| `sudo systemctl restart usb-cycle.service` | Restart the service |
| `sudo systemctl reload usb-cycle.service` | Reload service configuration |
| `sudo systemctl status usb-cycle.service` | Check service status |
| `sudo systemctl enable usb-cycle.service` | Enable auto-start at boot |
| `sudo systemctl disable usb-cycle.service` | Disable auto-start at boot |

### Check Service Status

```bash
# Detailed status information
sudo systemctl status usb-cycle.service

# Check if service is active
sudo systemctl is-active usb-cycle.service

# Check if service is enabled
sudo systemctl is-enabled usb-cycle.service
```

## Monitoring and Logs

### View Live Logs

```bash
# Follow logs in real-time
sudo journalctl -u usb-cycle.service -f

# Follow logs with timestamps
sudo journalctl -u usb-cycle.service -f --no-hostname
```

### Historical Logs

```bash
# View all logs for the service
sudo journalctl -u usb-cycle.service

# View logs from last boot
sudo journalctl -u usb-cycle.service -b

# View logs from last hour
sudo journalctl -u usb-cycle.service --since "1 hour ago"

# View logs from specific date
sudo journalctl -u usb-cycle.service --since "2024-01-01" --until "2024-01-02"

# Export logs to file
sudo journalctl -u usb-cycle.service > usb-cycle-logs.txt
```
