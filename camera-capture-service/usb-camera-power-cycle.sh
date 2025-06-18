#!/bin/bash

# GPIO Power Cycle and File Transfer Script
# This script uses GPIO to cycle power to a device, waits for it to mount,
# copies all files, and then unmounts and powers it off.

# --- Configuration ---
# GPIO pin for power control
GPIO_PIN=17

# Time in seconds to keep the device powered OFF between cycles
OFF_TIME=60

# Destination directory for copied files
DEST_DIR="/home/vyom/images"

# Log file path
LOG_FILE="/var/log/gpio-cycle.log"

# Time to wait for the device to stabilize after power on before checking for mount
POWER_ON_STABILIZATION_TIME=5

# Maximum time to wait for the device to be mounted by the system
MAX_MOUNT_WAIT=10

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

    MOUNT_POINTS=$(findmnt -lo TARGET,SOURCE -t vfat,ntfs,exfat,ext4 | grep -E "^/media/|^/mnt/")

    if [ -z "$MOUNT_POINTS" ]; then
        log_message "No mounted devices found to unmount."
        return 0
    fi

    local unmount_success=true
    while IFS= read -r line; do
        mount_point=$(echo "$line" | awk '{print $1}')
        if [ -n "$mount_point" ] && [ -d "$mount_point" ]; then
            log_message "Unmounting: $mount_point"
            if ! umount "$mount_point" 2>>"$LOG_FILE"; then
                log_message "WARNING: Failed to unmount $mount_point. Attempting force unmount..."
                if ! umount -f "$mount_point" 2>>"$LOG_FILE"; then
                    log_message "ERROR: Force unmount also failed for $mount_point."
                    unmount_success=false
                else
                    log_message "Force unmount successful for $mount_point."
                fi
            else
                log_message "Successfully unmounted: $mount_point"
            fi
        fi
    done <<< "$MOUNT_POINTS"

    sleep 1 # Give the system a moment to process unmounts

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
    if ! chown vyom:vyom "$DEST_DIR" 2>>"$LOG_FILE"; then
        log_message "WARNING: Could not change ownership of $DEST_DIR"
    fi
    if [ ! -w "$DEST_DIR" ]; then
        log_message "ERROR: Destination directory $DEST_DIR is not writable."
        return 1
    fi
    return 0
}

# Fixed version of the copy_files function
copy_files() {
    log_message "Looking for mounted devices to copy files from..."
    if ! check_destination; then
        log_message "ERROR: Destination check failed. Aborting file copy."
        return 1
    fi

    MOUNT_POINTS=$(findmnt -lo TARGET -t vfat,ntfs,exfat,ext4 | grep -E "^/media/|^/mnt/")
    if [ -z "$MOUNT_POINTS" ]; then
        log_message "No mounted devices found for file transfer."
        return
    fi

    while IFS= read -r mount_point; do
        log_message "Checking device at: $mount_point"
        local copy_count=0
        local fail_count=0
        local temp_file=$(mktemp)

        # Use process substitution instead of pipeline to avoid subshell
        while IFS= read -r -d '' source_file; do
            local filename=$(basename "$source_file")
            local dest_file="$DEST_DIR/$filename"

            if [ -f "$dest_file" ]; then
                log_message "SKIP: $filename already exists in destination."
                continue
            fi

            # Capture error output and show it in the log
            if cp_output=$(cp -p "$source_file" "$dest_file" 2>&1); then
                log_message "COPIED: $filename"
                chown vyom:vyom "$dest_file" 2>/dev/null
                copy_count=$((copy_count + 1))
            else
                log_message "ERROR: Failed to copy $filename. Error: $cp_output"
                fail_count=$((fail_count + 1))
            fi
        done < <(find "$mount_point" -type f -print0)
        
        rm -f "$temp_file"
        log_message "Transfer complete for $mount_point: $copy_count files copied, $fail_count failed."
    done <<< "$MOUNT_POINTS"
}

# Alternative version with better error handling and debugging
copy_files_debug() {
    log_message "Looking for mounted devices to copy files from..."
    if ! check_destination; then
        log_message "ERROR: Destination check failed. Aborting file copy."
        return 1
    fi

    MOUNT_POINTS=$(findmnt -lo TARGET -t vfat,ntfs,exfat,ext4 | grep -E "^/media/|^/mnt/")
    if [ -z "$MOUNT_POINTS" ]; then
        log_message "No mounted devices found for file transfer."
        return
    fi

    while IFS= read -r mount_point; do
        log_message "Checking device at: $mount_point"
        local copy_count=0
        local fail_count=0

        # Check if mount point is accessible
        if [ ! -r "$mount_point" ]; then
            log_message "ERROR: Cannot read from $mount_point"
            continue
        fi

        # Use a more robust approach with explicit file handling
        local file_list=$(find "$mount_point" -type f 2>/dev/null)
        if [ -z "$file_list" ]; then
            log_message "No files found in $mount_point"
            continue
        fi

        echo "$file_list" | while IFS= read -r source_file; do
            local filename=$(basename "$source_file")
            local dest_file="$DEST_DIR/$filename"

            # Skip if file already exists
            if [ -f "$dest_file" ]; then
                log_message "SKIP: $filename already exists in destination."
                continue
            fi

            # Check source file permissions
            if [ ! -r "$source_file" ]; then
                log_message "ERROR: Cannot read source file $filename (permissions)"
                continue
            fi

            # Check available space (basic check)
            local file_size=$(stat -f%z "$source_file" 2>/dev/null || stat -c%s "$source_file" 2>/dev/null)
            local available_space=$(df "$DEST_DIR" | awk 'NR==2 {print $4*1024}')
            
            if [ "$file_size" -gt "$available_space" ]; then
                log_message "ERROR: Not enough space to copy $filename"
                continue
            fi

            # Attempt copy with verbose error reporting
            log_message "Attempting to copy: $filename (${file_size} bytes)"
            if cp -p "$source_file" "$dest_file" 2>&1; then
                log_message "SUCCESS: Copied $filename"
                chown vyom:vyom "$dest_file" 2>/dev/null || log_message "WARNING: Could not change ownership of $filename"
                copy_count=$((copy_count + 1))
            else
                local error_msg=$(cp -p "$source_file" "$dest_file" 2>&1)
                log_message "ERROR: Failed to copy $filename. Detailed error: $error_msg"
                fail_count=$((fail_count + 1))
            fi
        done
        
        log_message "Transfer complete for $mount_point: $copy_count files copied, $fail_count failed."
    done <<< "$MOUNT_POINTS"
}

# Function to wait for a device to mount
wait_for_usb_mount() {
    local attempts=0
    local max_attempts=$((MAX_MOUNT_WAIT * 2)) # Poll every 0.5s

    log_message "Waiting for device to mount (max ${MAX_MOUNT_WAIT}s)..."
    while [ $attempts -lt $max_attempts ]; do
        if [ -n "$(findmnt -lo TARGET -t vfat,ntfs,exfat,ext4 | grep -E '^/media/|^/mnt/')" ]; then
            log_message "Device detected as mounted. Proceeding with file transfer."
            sleep 1 # Allow filesystem to stabilize
            return 0
        fi
        sleep 0.5
        attempts=$((attempts + 1))
    done

    log_message "Timeout: No device mounted after ${MAX_MOUNT_WAIT} seconds."
    return 1
}

# --- Main Loop ---
log_message "Starting device power cycle and copy service."
log_message "Destination: $DEST_DIR, OFF Time: ${OFF_TIME}s"

# Set GPIO pin as output and initialize to LOW (OFF)
pinctrl set ${GPIO_PIN} op dl

while true; do
    # 1. Power ON
    device_power_on
    log_message "Device powered on. Waiting ${POWER_ON_STABILIZATION_TIME}s for it to initialize..."
    sleep $POWER_ON_STABILIZATION_TIME

    # 2. Wait for Mount
    if wait_for_usb_mount; then
        # 3. Copy files if mount was successful
        start_time=$(date +%s)
        copy_files
        end_time=$(date +%s)
        transfer_time=$((end_time - start_time))
        log_message "File copy process finished in ${transfer_time}s."
    fi

    # 4. Unmount Media
    eject_usb_devices

    # 5. Power OFF
    device_power_off

    # 6. Wait for the specified OFF duration
    log_message "Device powered off. Waiting for $OFF_TIME seconds..."
    sleep $OFF_TIME
done