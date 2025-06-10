#!/bin/bash

# ==============================================================================
# Setup Script for Camera Capture Service
# ==============================================================================
# This script installs and configures the USB power cycling and image
# transfer service for a camera. It must be run with root privileges.
# ==============================================================================

# --- Configuration ---
# The user who will own the created directories (not the user running the service)
OWNER_USER="pi"

# Directory where the main script will be stored
SCRIPT_DIR="/home/$OWNER_USER/Documents/watchmen/usb-controller"
SCRIPT_PATH="$SCRIPT_DIR/usb-camera-power-cycle.sh"

# Directory where images will be saved
IMAGE_DIR="/home/$OWNER_USER/Documents/images"

# Path for the systemd service file
SERVICE_NAME="camera-capture.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

# Path for the log file
LOG_FILE="/var/log/usb-cycle.log"


# --- Script Body ---

# 1. Check for Root Privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Please use 'sudo ./setup.sh'"
  exit 1
fi

echo "--- Starting Camera Capture Service Setup ---"

# 2. Install Dependencies
echo "[1/6] Installing dependencies (uhubctl)..."
apt-get update >/dev/null
if ! apt-get install -y uhubctl; then
    echo "ERROR: Failed to install 'uhubctl'. Please check your internet connection and package manager."
    exit 1
fi
echo "Dependencies installed successfully."

# 3. Create Directories and Set Ownership
echo "[2/6] Creating required directories..."
mkdir -p "$SCRIPT_DIR"
mkdir -p "$IMAGE_DIR"
chown -R "$OWNER_USER:$OWNER_USER" "/home/$OWNER_USER/Documents"
echo "Directories created and permissions set."

# 4. Create the main USB control script
echo "[3/6] Creating the USB control script at $SCRIPT_PATH..."
read -p "Enter the complete path to the camera images folder: " CAMERA_IMAGE_FOLDER

# Use a heredoc to write the provided script to the file
cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash

# USB Power Cycle and Image Transfer Script
# This script cycles USB power and moves images when device is connected

# Configuration
USB_HUB="1-1"
OFF_TIME=60
MAX_MOUNT_WAIT=10
DEST_DIR="$CAMERA_IMAGE_FOLDER" # INPUT
LOG_FILE="/var/log/usb-cycle.log"

# Image file extensions to move
IMAGE_EXTENSIONS="jpg jpeg png gif bmp tiff tif webp raw cr2 nef dng"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Function to safely eject all USB devices
eject_usb_devices() {
    log_message "Ejecting all USB devices..."
    
    # Find all mounted USB devices
    MOUNT_POINTS=$(findmnt -lo TARGET,SOURCE -t vfat,ntfs,exfat,ext4 | grep -E "^/media/|^/mnt/" | grep -v "^/$")
    
    if [ -z "$MOUNT_POINTS" ]; then
        log_message "No USB devices found to eject"
        return 0
    fi
    
    local eject_success=true
    
    # Process each mount point
    while IFS= read -r line; do
        # Extract mount point (first field) and device (second field)
        mount_point=$(echo "$line" | awk '{print $1}')
        device=$(echo "$line" | awk '{print $2}')
        
        if [ -n "$mount_point" ] && [ -d "$mount_point" ]; then
            log_message "Ejecting: $mount_point ($device)"
            
            # First try to sync any pending writes
            sync
            
            # Attempt to unmount the device
            if umount "$mount_point" 2>>"$LOG_FILE"; then
                log_message "Successfully ejected: $mount_point"
                
                # If it's a removable device, try to eject it as well
                if [ -n "$device" ] && [ -b "$device" ]; then
                    # Extract the base device (remove partition numbers)
                    base_device=$(echo "$device" | sed 's/[0-9]*$//')
                    if [ "$base_device" != "$device" ] && [ -b "$base_device" ]; then
                        eject "$base_device" 2>/dev/null || true
                        log_message "Sent eject command to: $base_device"
                    fi
                fi
            else
                log_message "WARNING: Failed to eject $mount_point"
                
                # Try to force unmount as a last resort
                log_message "Attempting force unmount of $mount_point"
                if umount -f "$mount_point" 2>>"$LOG_FILE"; then
                    log_message "Force unmount successful: $mount_point"
                else
                    log_message "ERROR: Force unmount failed: $mount_point"
                    eject_success=false
                fi
            fi
        fi
        
    done <<< "$MOUNT_POINTS"
    
    # Give a moment for the system to process the unmounts
    sleep 1
    
    if [ "$eject_success" = true ]; then
        log_message "All USB devices ejected successfully"
    else
        log_message "WARNING: Some USB devices could not be ejected properly"
    fi
    
    return 0
}

# Function to check and fix destination directory permissions
check_destination() {
    # Create destination directory if it doesn't exist
    if ! mkdir -p "$DEST_DIR" 2>>"$LOG_FILE"; then
        log_message "ERROR: Cannot create destination directory $DEST_DIR"
        return 1
    fi
    
    # Check if destination is writable
    if [ ! -w "$DEST_DIR" ]; then
        log_message "ERROR: Destination directory $DEST_DIR is not writable"
        log_message "Attempting to fix permissions..."
        chmod 755 "$DEST_DIR" 2>>"$LOG_FILE"
        if [ ! -w "$DEST_DIR" ]; then
            log_message "ERROR: Could not fix permissions for $DEST_DIR"
            return 1
        fi
    fi
    
    log_message "Destination directory $DEST_DIR is ready"
    return 0
}

# Function to find and move images from USB devices
move_images() {
    log_message "Looking for mounted USB devices..."
    
    # Check destination directory first
    if ! check_destination; then
        log_message "ERROR: Destination directory check failed, skipping image transfer"
        return 1
    fi
    
    # Find all mounted USB devices (typically under /media/pi/ or /mnt/)
    # Check common mount points
    MOUNT_POINTS=$(findmnt -lo TARGET -t vfat,ntfs,exfat,ext4 | grep -E "^(/media/|/mnt/)" | grep -v "^/$")
    
    if [ -z "$MOUNT_POINTS" ]; then
        log_message "No USB devices found mounted"
        return
    fi
    
    # Process each mount point
    while IFS= read -r mount_point; do
        log_message "Checking USB device at: $mount_point"
        
        # Check mount point accessibility
        if [ ! -r "$mount_point" ]; then
            log_message "ERROR: Cannot read from $mount_point - permission denied"
            continue
        fi
        
        # Check if mount point is read-only
        mount_info=$(mount | grep " $mount_point ")
        if echo "$mount_info" | grep -q "ro,"; then
            log_message "WARNING: $mount_point is mounted read-only"
        fi
        log_message "Mount info: $mount_info"
        
        # Count images before moving
        image_count=0
        failed_count=0
        
        # Build find command for all image extensions
        find_cmd="find \"$mount_point\" -type f \( "
        first=true
        for ext in $IMAGE_EXTENSIONS; do
            if [ "$first" = true ]; then
                find_cmd="$find_cmd -iname \"*.$ext\""
                first=false
            else
                find_cmd="$find_cmd -o -iname \"*.$ext\""
            fi
        done
        find_cmd="$find_cmd \)"
        
        # Find and copy/move images (use a more robust approach)
        eval "$find_cmd" -print0 | while IFS= read -r -d '' image_file; do
            if [ -f "$image_file" ]; then
                # Get original filename for logging
                original_filename=$(basename "$image_file")
                
                # Use original filename in destination
                dest_file="$DEST_DIR/$original_filename"
                
                # Skip if file already exists in destination
                if [ -f "$dest_file" ]; then
                    log_message "SKIP: $original_filename (already exists)"
                    continue
                fi
                
                # Check if file is readable
                if [ ! -r "$image_file" ]; then
                    log_message "ERROR: Cannot read $original_filename - permission denied"
                    failed_count=$((failed_count + 1))
                    continue
                fi
                
                # Try to copy first, then remove original if copy succeeds
                if cp "$image_file" "$dest_file" 2>>"$LOG_FILE"; then
                    # Copy successful, now remove original
                    if rm "$image_file" 2>>"$LOG_FILE"; then
                        log_message "Moved: $original_filename"
                        image_count=$((image_count + 1))
                    else
                        log_message "WARNING: Copied but could not remove original: $original_filename"
                        image_count=$((image_count + 1))
                    fi
                else
                    # Log detailed error information
                    error_msg=$(cp "$image_file" "$dest_file" 2>&1)
                    log_message "ERROR: Failed to copy $original_filename"
                    log_message "Copy error: $error_msg"
                    log_message "Source: $image_file"
                    log_message "Dest: $dest_file"
                    
                    # Check available space
                    df_output=$(df -h "$DEST_DIR" 2>/dev/null)
                    log_message "Destination space: $df_output"
                    
                    failed_count=$((failed_count + 1))
                fi
            fi
        done
        
        log_message "Transfer complete: $image_count moved, $failed_count failed from $mount_point"
        
    done <<< "$MOUNT_POINTS"
}

# Function to power on USB hub
usb_power_on() {
    log_message "Powering ON USB hub $USB_HUB"
    uhubctl -a on -l "$USB_HUB" >/dev/null 2>&1
}

# Function to power off USB hub (with safe ejection)
usb_power_off() {
    # First eject all USB devices safely
    eject_usb_devices
    
    # Ensure all file operations are completed
    sync
    sleep 2
    
    log_message "Powering OFF USB hub $USB_HUB"
    uhubctl -a off -l "$USB_HUB" >/dev/null 2>&1
}

# Function to wait for USB devices to mount
wait_for_usb_mount() {
    local attempts=0
    local max_attempts=20  # 20 attempts x 0.5s = 10s max
    local devices_found=false
    
    log_message "Waiting for USB devices to mount..."
    
    while [ $attempts -lt $max_attempts ]; do
        # Check for mounted USB devices
        MOUNT_POINTS=$(findmnt -lo TARGET -t vfat,ntfs,exfat,ext4 | grep -E "^(/media/|/mnt/)" | grep -v "^/$")
        
        if [ -n "$MOUNT_POINTS" ]; then
            devices_found=true
            local wait_time=$((attempts / 2))
            local wait_ms=$((attempts % 2 * 5))
            log_message "USB device(s) detected after ${wait_time}.${wait_ms}s"
            # Give a tiny bit more time for filesystem to stabilize
            sleep 0.5
            break
        fi
        
        sleep 0.5
        attempts=$((attempts + 1))
    done
    
    if [ "$devices_found" = false ]; then
        log_message "No USB devices detected after ${MAX_MOUNT_WAIT}s timeout"
    fi
}

# Main loop
log_message "Starting USB cycle service"
log_message "Configuration: OFF=${OFF_TIME}s, Destination=$DEST_DIR"

while true; do
    # Power on USB
    usb_power_on
    
    # Wait for devices to mount (smart polling)
    wait_for_usb_mount
    
    # Move images
    log_message "Starting image transfer..."
    start_time=$(date +%s)
    move_images
    end_time=$(date +%s)
    transfer_time=$((end_time - start_time))
    log_message "Image transfer completed in ${transfer_time}s"
    
    # Brief delay to ensure all operations complete
    sleep 1
    
    # Power off USB with safe ejection
    usb_power_off
    
    # Wait for OFF period
    log_message "USB will remain OFF for $OFF_TIME seconds"
    sleep $OFF_TIME
done
EOF

# 5. Set script permissions and create log file
echo "[4/6] Setting script permissions and creating log file..."
chmod +x "$SCRIPT_PATH"
touch "$LOG_FILE"
chmod 664 "$LOG_FILE"
echo "Permissions set."

# 6. Create the systemd service file
echo "[5/6] Creating systemd service file at $SERVICE_PATH..."
cat > "$SERVICE_PATH" << EOF
[Unit]
Description=USB Power Cycle and Image Transfer Service
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

# Ensure the service has necessary permissions
PrivilegeEscalation=yes
NoNewPrivileges=no

# Environment
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Working Directory
WorkingDirectory=/home/pi/Documents

[Install]
WantedBy=multi-user.target
EOF
echo "Service file created."

# 7. Enable and Start the Service
echo "[6/6] Reloading systemd, enabling and starting the service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
echo "Service enabled and started."

echo
echo "--- Setup Complete ---"
echo
echo "The camera capture service has been installed and started."
echo "To check the status of the service, run: sudo systemctl status $SERVICE_NAME"
echo "To view the service logs, run: sudo journalctl -u $SERVICE_NAME -f"
echo "To view the script's specific log file, run: tail -f $LOG_FILE"