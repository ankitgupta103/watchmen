#!/bin/bash

# =============================================================================
# Image Copy Script
# This script copies an image file multiple times to a specified folder
# =============================================================================

# --- CONFIGURATION (Edit these paths) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_IMAGE="${SCRIPT_DIR}/testdata/forest_man_2.jpg"      
DESTINATION_FOLDER="/home/ankit/Documents/images"     
NUM_COPIES=1000                                # Number of copies to make
INTERVAL=10                                    # Interval between copies (in seconds)
# ----------------------------------------

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
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
        print_status "Copy $i/$NUM_COPIES: Created '$NEW_NAME'"
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