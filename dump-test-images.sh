#!/bin/bash

# =============================================================================
# Image Copy Script - Cron Compatible
# This script copies an image file multiple times to a specified folder
# Designed to work with cron jobs
# =============================================================================

# --- CONFIGURATION (Edit these paths) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_IMAGE="${SCRIPT_DIR}/testdata/forest_man_2.jpg"      
DESTINATION_FOLDER="/home/ankit/Documents/images"     
NUM_COPIES=1                                  # Number of copies to make
INTERVAL=1                                    # Interval between copies (in seconds)
LOG_FILE="/var/log/image_copy.log"            # Log file for cron output (optional)
# ----------------------------------------

# Set PATH for cron compatibility
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Colors for output (only use if running in terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Function to print colored output and log
print_status() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
    echo -e "${GREEN}${message}${NC}"
    [ -n "$LOG_FILE" ] && echo "$message" >> "$LOG_FILE"
}

print_warning() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $1"
    echo -e "${YELLOW}${message}${NC}"
    [ -n "$LOG_FILE" ] && echo "$message" >> "$LOG_FILE"
}

print_error() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1"
    echo -e "${RED}${message}${NC}"
    [ -n "$LOG_FILE" ] && echo "$message" >> "$LOG_FILE"
}

# Check if source image exists
if [ ! -f "$SOURCE_IMAGE" ]; then
    print_error "Source image '$SOURCE_IMAGE' does not exist!"
    exit 1
fi

# Create destination folder if it doesn't exist
if [ ! -d "$DESTINATION_FOLDER" ]; then
    print_warning "Destination folder '$DESTINATION_FOLDER' does not exist. Creating it..."
    mkdir -p "$DESTINATION_FOLDER"
    if [ $? -eq 0 ]; then
        print_status "Destination folder created successfully."
    else
        print_error "Failed to create destination folder!"
        exit 1
    fi
fi

# Get the base name and extension of the source image
IMAGE_NAME=$(basename "$SOURCE_IMAGE")
IMAGE_BASE="${IMAGE_NAME%.*}"
IMAGE_EXT="${IMAGE_NAME##*.}"

print_status "Starting to copy '$IMAGE_NAME' to '$DESTINATION_FOLDER'"
print_status "Making $NUM_COPIES copies with $INTERVAL second interval..."

# Copy the image multiple times
for i in $(seq 1 $NUM_COPIES); do
    # Create unique filename with timestamp and counter
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    NEW_NAME="${IMAGE_BASE}_copy_${i}_${TIMESTAMP}.${IMAGE_EXT}"
    DEST_PATH="$DESTINATION_FOLDER/$NEW_NAME"
    
    # Copy the file
    cp "$SOURCE_IMAGE" "$DEST_PATH"
    
    if [ $? -eq 0 ]; then
        # Ensure the copied file is deletable by setting proper permissions
        chmod 644 "$DEST_PATH"
        print_status "Copy $i/$NUM_COPIES: Created '$NEW_NAME' (deletable)"
    else
        print_error "Failed to copy image (attempt $i/$NUM_COPIES)"
    fi
    
    # Wait for the specified interval before next copy (except for the last copy)
    if [ $i -lt $NUM_COPIES ]; then
        print_status "Waiting $INTERVAL seconds before next copy..."
        sleep $INTERVAL
    fi
done

print_status "Copying completed! $NUM_COPIES copies created in '$DESTINATION_FOLDER'"

# Optional: Show the contents of the destination folder
echo
print_status "Contents of destination folder:"
ls -la "$DESTINATION_FOLDER" | grep "$IMAGE_BASE"