#!/bin/bash

# ==============================================================================
# Setup Script for Camera Capture Service
# ==============================================================================
# This script installs and configures the USB power cycling and image
# transfer service for a camera. It must be run with root privileges.
# ==============================================================================

# Get the actual user (not root when using sudo)
if [[ -n "$SUDO_USER" ]]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER="$USER"
fi

# Set user-specific paths
USER_HOME="/home/$ACTUAL_USER"

# --- Configuration ---
# The user who will own the created directories (not the user running the service)
OWNER_USER="$ACTUAL_USER"

# Directory where the main script will be stored
SCRIPT_DIR="$USER_HOME/watchmen/camera-capture-service"
SCRIPT_PATH="$SCRIPT_DIR/usb-camera-power-cycle.sh"

# Directory where images will be saved
IMAGE_DIR="$USER_HOME/images"

# Path for the systemd service file
SERVICE_NAME="camera-capture.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

CAMERA_IMAGE_FOLDER="$USER_HOME/images"

# Path for the log file
LOG_FILE="/var/log/camera-capture.log"

# 1. Check for Root Privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root. Please use 'sudo ./setup.sh'"
  exit 1
fi

echo "--- Starting Camera Capture Service Setup ---"
echo "Setting up service for user: $ACTUAL_USER"
echo "User home directory: $USER_HOME"

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
chown -R "$OWNER_USER:$OWNER_USER" "$IMAGE_DIR"
if [ -d "$USER_HOME/watchmen" ]; then
    chown -R "$OWNER_USER:$OWNER_USER" "$USER_HOME/watchmen"
fi
echo "Directories created and permissions set."

# 4. Create the main USB control script
echo "[3/6] Creating the USB control script at $SCRIPT_PATH..."

# Use a heredoc to write the provided script to the file
cat > "$SCRIPT_PATH" << EOF
#!/bin/bash

# GPIO Power Cycle and Image Transfer Script
# This script uses GPIO to cycle power to a device, waits for it to mount,
# moves all image files, and then unmounts and powers it off.

# --- Configuration ---
# GPIO pin for power control
GPIO_PIN=17

# Time in seconds to keep the device powered OFF between cycles
OFF_TIME=60

# Destination directory for moved files
DEST_DIR="/home/$ACTUAL_USER/images"

# Log file path
LOG_FILE="/var/log/camera-capture.log"

# Time to wait for the device to stabilize after power on before checking for mount
POWER_ON_STABILIZATION_TIME=5

# Maximum time to wait for the device to be mounted by the system
MAX_MOUNT_WAIT=10

# Supported image file extensions (case insensitive)
IMAGE_EXTENSIONS="jpg jpeg png gif bmp tiff tif raw cr2 nef arw dng"

# --- Script Logic ---

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Cleanup function to run on script exit (e.g., Ctrl+C)
cleanup() {
    log_message "Stopping script and powering OFF device..."
    pinctrl set ${GPIO_PIN} op dl
    log_message "GPIO pin ${GPIO_PIN} set to LOW (OFF). Script terminated."
    exit 0
}

# Set up signal trap for graceful shutdown
trap cleanup SIGINT SIGTERM

# Function to power on the device via GPIO
device_power_on() {
    log_message "Powering ON device via GPIO pin ${GPIO_PIN}"
    pinctrl set ${GPIO_PIN} op dh # Set pin to HIGH
}

# Function to power off the device via GPIO
device_power_off() {
    log_message "Powering OFF device via GPIO pin ${GPIO_PIN}"
    pinctrl set ${GPIO_PIN} op dl # Set pin to LOW
}

# Function to safely eject all mounted USB/external media
eject_usb_devices() {
    log_message "Unmounting all external media..."
    sync # Ensure all pending writes are completed

    # Look for mounted devices in common mount locations
    local mount_points=$(findmnt -ln -o TARGET,SOURCE -t vfat,ntfs,exfat,ext4,ext3,ext2 | grep -E "^(/media/|/mnt/|/run/media/)")

    if [ -z "$mount_points" ]; then
        log_message "No mounted devices found to unmount."
        return 0
    fi

    local unmount_success=true
    while IFS= read -r line; do
        local mount_point=$(echo "$line" | awk '{print $1}')
        if [ -n "$mount_point" ] && [ -d "$mount_point" ]; then
            log_message "Unmounting: $mount_point"
            if umount "$mount_point" 2>>"$LOG_FILE"; then
                log_message "Successfully unmounted: $mount_point"
            else
                log_message "WARNING: Failed to unmount $mount_point. Attempting force unmount..."
                if umount -f "$mount_point" 2>>"$LOG_FILE"; then
                    log_message "Force unmount successful for $mount_point."
                else
                    log_message "ERROR: Force unmount also failed for $mount_point."
                    unmount_success=false
                fi
            fi
        fi
    done <<< "$mount_points"

    sleep 2 # Give the system time to process unmounts

    if [ "$unmount_success" = true ]; then
        log_message "All detected media unmounted successfully."
    else
        log_message "WARNING: Some media could not be unmounted."
    fi
}

# Function to check and prepare the destination directory
check_destination() {
    if ! mkdir -p "$DEST_DIR" 2>>"$LOG_FILE"; then
        log_message "ERROR: Cannot create destination directory $DEST_DIR"
        return 1
    fi
    
    if ! chown $ACTUAL_USER:$ACTUAL_USER "$DEST_DIR" 2>>"$LOG_FILE"; then
        log_message "WARNING: Could not change ownership of $DEST_DIR"
    fi
    
    if [ ! -w "$DEST_DIR" ]; then
        log_message "ERROR: Destination directory $DEST_DIR is not writable."
        return 1
    fi
    
    log_message "Destination directory ready: $DEST_DIR"
    return 0
}

# Function to get file size (compatible with different systems)
get_file_size() {
    local file="$1"
    if command -v stat >/dev/null 2>&1; then
        # Try GNU stat first (Linux)
        stat -c%s "$file" 2>/dev/null || \
        # Try BSD stat (macOS)
        stat -f%z "$file" 2>/dev/null || \
        # Fallback to ls
        ls -l "$file" | awk '{print $5}'
    else
        ls -l "$file" | awk '{print $5}'
    fi
}

# Function to check available space
check_available_space() {
    local dest_dir="$1"
    # Get available space in bytes, handle scientific notation
    df "$dest_dir" | awk 'NR==2 {printf "%.0f\n", $4*1024}'
}

# Function to build find command for image extensions
build_find_expression() {
    local expr=""
    local first=true
    
    for ext in $IMAGE_EXTENSIONS; do
        if [ "$first" = true ]; then
            expr="\( -iname \"*.$ext\""
            first=false
        else
            expr="$expr -o -iname \"*.$ext\""
        fi
    done
    expr="$expr \)"
    echo "$expr"
}

# Function to move image files from mounted devices
move_image_files() {
    log_message "Looking for mounted devices to move image files from..."
    
    if ! check_destination; then
        log_message "ERROR: Destination check failed. Aborting file transfer."
        return 1
    fi

    # Find mounted devices
    local mount_points=$(findmnt -ln -o TARGET -t vfat,ntfs,exfat,ext4,ext3,ext2 | grep -E "^(/media/|/mnt/|/run/media/)")
    
    if [ -z "$mount_points" ]; then
        log_message "No mounted devices found for file transfer."
        return 0
    fi

    local total_moved=0
    local total_failed=0
    local available_space=$(check_available_space "$DEST_DIR")

    while IFS= read -r mount_point; do
        log_message "Checking device at: $mount_point"
        
        # Check if mount point is accessible
        if [ ! -r "$mount_point" ]; then
            log_message "ERROR: Cannot read from $mount_point"
            continue
        fi

        local device_moved=0
        local device_failed=0
        
        # Build find expression for image files
        local find_expr=\$(build_find_expression)
        
        # Find image files and process them
        while IFS= read -r -d '' source_file; do
            # Generate a unique filename based on the current epoch timestamp
            local ext="${source_file##*.}"
            local base_epoch=`date +%s`
            local epoch=$base_epoch
            local dest_file="$DEST_DIR/$epoch.$ext"
            # Ensure uniqueness by incrementing epoch if file exists
            while [ -f "$dest_file" ]; do
                epoch=$((epoch + 1))
                dest_file="$DEST_DIR/$epoch.$ext"
            done
            local filename=$(basename "$source_file")
            
            # Skip if source file is not readable
            if [ ! -r "$source_file" ]; then
                log_message "ERROR: Cannot read source file $filename"
                device_failed=$((device_failed + 1))
                continue
            fi
            
            # Check file size and available space
            local file_size=$(get_file_size "$source_file")
            
            # Ensure we have valid numbers (no scientific notation)
            if ! [[ "$file_size" =~ ^[0-9]+$ ]]; then
                log_message "WARNING: Invalid file size for $filename, skipping space check"
                file_size=0
            fi
            
            if ! [[ "$available_space" =~ ^[0-9]+$ ]]; then
                log_message "WARNING: Invalid available space value, refreshing..."
                available_space=$(check_available_space "$DEST_DIR")
                if ! [[ "$available_space" =~ ^[0-9]+$ ]]; then
                    log_message "WARNING: Cannot determine available space, proceeding anyway"
                    available_space=999999999999  # Large fallback value
                fi
            fi
            
            if [ "$file_size" -gt 0 ] && [ "$file_size" -gt "$available_space" ]; then
                log_message "ERROR: Not enough space to move $filename (${file_size} bytes needed, ${available_space} available)"
                device_failed=$((device_failed + 1))
                continue
            fi
            
            # Move the file (atomic operation)
            log_message "Moving: $filename (${file_size} bytes)"
            if mv "$source_file" "$dest_file" 2>>"$LOG_FILE"; then
                log_message "SUCCESS: Moved $filename"
                # Update ownership
                chown $ACTUAL_USER:$ACTUAL_USER "$dest_file" 2>/dev/null || log_message "WARNING: Could not change ownership of $filename"
                device_moved=$((device_moved + 1))
                # Update available space (only if we have valid numbers)
                if [[ "$available_space" =~ ^[0-9]+$ ]] && [[ "$file_size" =~ ^[0-9]+$ ]] && [ "$file_size" -gt 0 ]; then
                    available_space=$((available_space - file_size))
                fi
            else
                log_message "ERROR: Failed to move $filename"
                device_failed=$((device_failed + 1))
            fi
            
        done < <(eval "find \"$mount_point\" -type f $find_expr -print0" 2>/dev/null)
        
        log_message "Transfer complete for $mount_point: $device_moved files moved, $device_failed failed."
        total_moved=$((total_moved + device_moved))
        total_failed=$((total_failed + device_failed))
        
    done <<< "$mount_points"
    
    log_message "Overall transfer summary: $total_moved files moved, $total_failed failed."
    return 0
}

# Function to wait for a device to mount
wait_for_usb_mount() {
    local attempts=0
    local max_attempts=$((MAX_MOUNT_WAIT * 2)) # Poll every 0.5s

    log_message "Waiting for device to mount (max ${MAX_MOUNT_WAIT}s)..."
    
    while [ $attempts -lt $max_attempts ]; do
        local mounted_devices=$(findmnt -ln -o TARGET -t vfat,ntfs,exfat,ext4,ext3,ext2 | grep -E "^(/media/|/mnt/|/run/media/)")
        
        if [ -n "$mounted_devices" ]; then
            log_message "Device(s) detected as mounted:"
            echo "$mounted_devices" | while read -r mount_point; do
                log_message "  - $mount_point"
            done
            sleep 2 # Allow filesystem to stabilize
            return 0
        fi
        
        sleep 0.5
        attempts=$((attempts + 1))
        
        # Show progress every 5 seconds
        if [ $((attempts % 10)) -eq 0 ]; then
            log_message "Still waiting... (${attempts}/2 seconds elapsed)"
        fi
    done

    log_message "Timeout: No device mounted after ${MAX_MOUNT_WAIT} seconds."
    return 1
}

# --- Main Loop ---
log_message "Starting device power cycle and image transfer service."
log_message "Destination: $DEST_DIR, OFF Time: ${OFF_TIME}s"
log_message "Supported image extensions: $IMAGE_EXTENSIONS"

# Ensure log file is writable
touch "$LOG_FILE" 2>/dev/null || {
    echo "ERROR: Cannot write to log file $LOG_FILE"
    exit 1
}

# Set GPIO pin as output and initialize to LOW (OFF)
if ! pinctrl set ${GPIO_PIN} op dl 2>>"$LOG_FILE"; then
    log_message "ERROR: Failed to initialize GPIO pin $GPIO_PIN"
    exit 1
fi

log_message "GPIO pin $GPIO_PIN initialized to LOW (OFF)"

# Main processing loop
while true; do
    log_message "--- Starting new cycle ---"
    
    # 1. Power ON
    device_power_on
    log_message "Device powered on. Waiting ${POWER_ON_STABILIZATION_TIME}s for initialization..."
    sleep $POWER_ON_STABILIZATION_TIME

    # 2. Wait for Mount
    if wait_for_usb_mount; then
        # 3. Move image files if mount was successful
        start_time=$(date +%s)
        move_image_files
        end_time=$(date +%s)
        transfer_time=$((end_time - start_time))
        log_message "Image transfer process completed in ${transfer_time}s."
    else
        log_message "No device mounted, skipping file transfer."
    fi

    # 4. Unmount Media (always attempt this)
    eject_usb_devices

    # 5. Power OFF
    device_power_off

    # 6. Wait for the specified OFF duration
    log_message "Device powered off. Waiting for $OFF_TIME seconds before next cycle..."
    log_message "--- Cycle complete ---"
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
WorkingDirectory=$USER_HOME

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
echo "User: $ACTUAL_USER"
echo "Images directory: $IMAGE_DIR"
echo "Script location: $SCRIPT_PATH"
echo "To check the status of the service, run: sudo systemctl status $SERVICE_NAME"
echo "To view the service logs, run: sudo journalctl -u $SERVICE_NAME -f"
echo "To view the script's specific log file, run: tail -f $LOG_FILE"