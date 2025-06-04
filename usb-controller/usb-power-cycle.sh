#!/bin/bash

# USB Power Cycle and Image Transfer Script
# This script cycles USB power and moves images when device is connected

# Configuration
USB_HUB="1-1"
OFF_TIME=60
MAX_MOUNT_WAIT=10
# Destination directory for images
DEST_DIR="/tmp/camera_captures"
LOG_FILE="/var/log/usb-cycle.log"

# Image file extensions to move
IMAGE_EXTENSIONS="jpg jpeg png gif bmp tiff tif webp raw cr2 nef dng"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Function to find and move images from USB devices
move_images() {
    log_message "Looking for mounted USB devices..."
    
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
        
        # Count images before moving
        image_count=0
        
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
        
        # Find and move images
        eval "$find_cmd" | while IFS= read -r image_file; do
            if [ -f "$image_file" ]; then
                # Get original filename for logging
                original_filename=$(basename "$image_file")
                
                # Get file extension
                ext="${original_filename##*.}"
                # Convert extension to lowercase for consistency
                ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
                
                # Get current epoch timestamp
                timestamp=$(date +%s)
                
                # Create new filename with epoch timestamp
                new_filename="${timestamp}.${ext}"
                dest_file="$DEST_DIR/$new_filename"
                
                # Handle duplicates (if multiple files processed in same second)
                counter=1
                while [ -f "$dest_file" ]; do
                    new_filename="${timestamp}_${counter}.${ext}"
                    dest_file="$DEST_DIR/$new_filename"
                    counter=$((counter + 1))
                done
                
                # Move the file
                if mv "$image_file" "$dest_file" 2>>"$LOG_FILE"; then
                    log_message "Moved: $original_filename -> $new_filename"
                    image_count=$((image_count + 1))
                else
                    log_message "ERROR: Failed to move $original_filename"
                fi
            fi
        done
        
        log_message "Moved $image_count images from $mount_point"
        
    done <<< "$MOUNT_POINTS"
}

# Function to power on USB hub
usb_power_on() {
    log_message "Powering ON USB hub $USB_HUB"
    uhubctl -a off -l "$USB_HUB" >/dev/null 2>&1
    sleep 3
    uhubctl -a on -l "$USB_HUB" >/dev/null 2>&1
}

# Function to power off USB hub
usb_power_off() {
    log_message "Powering OFF USB hub $USB_HUB"
    uhubctl -a off -l "$USB_HUB" >/dev/null 2>&1
    sleep 1
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
    
    # Power off USB immediately after transfer
    usb_power_off
    
    # Wait for OFF period
    log_message "USB will remain OFF for $OFF_TIME seconds"
    sleep $OFF_TIME
done
