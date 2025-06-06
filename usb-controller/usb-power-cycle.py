#!/usr/bin/env python3

"""
USB Power Cycle and Image Transfer Script
This script cycles USB power using a MOSFET switch and moves images when device is connected
"""

import os
import time
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import RPi.GPIO as GPIO

# Configuration
POWER_PIN = 11  # GPIO pin connected to MOSFET trigger (GPIO 17)
OFF_TIME = 60  # Seconds to keep USB power off
MAX_MOUNT_WAIT = 10  # Maximum seconds to wait for device mount
DEST_DIR = "/home/pi/Documents/images"
LOG_FILE = "/var/log/usb-cycle.log"

# Image file extensions to move
IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 
    'webp', 'raw', 'cr2', 'nef', 'dng'
}

class USBCycleManager:
    def __init__(self):
        self.setup_logging()
        self.setup_gpio()
        self.setup_directories()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_gpio(self):
        """Setup GPIO for MOSFET control"""
        GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
        GPIO.setup(POWER_PIN, GPIO.OUT)
        GPIO.output(POWER_PIN, GPIO.LOW)  # Start with USB power OFF
        self.logger.info(f"GPIO {POWER_PIN} configured for MOSFET control")
        
    def setup_directories(self):
        """Create destination directory if it doesn't exist"""
        Path(DEST_DIR).mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Destination directory: {DEST_DIR}")
        
    def cleanup(self):
        """Cleanup GPIO on exit"""
        GPIO.cleanup()
        self.logger.info("GPIO cleaned up")
        
    def usb_power_on(self):
        """Turn on USB power via MOSFET"""
        self.logger.info("Powering ON USB via MOSFET")
        GPIO.output(POWER_PIN, GPIO.HIGH)
        time.sleep(2)  # Give power time to stabilize
        
    def usb_power_off(self):
        """Turn off USB power via MOSFET"""
        self.logger.info("Powering OFF USB via MOSFET")
        GPIO.output(POWER_PIN, GPIO.LOW)
        time.sleep(1)
        
    def get_usb_mount_points(self):
        """Find all mounted USB devices"""
        try:
            # Run findmnt to get mounted filesystems
            result = subprocess.run(
                ['findmnt', '-lo', 'TARGET', '-t', 'vfat,ntfs,exfat,ext4'],
                capture_output=True, text=True, check=True
            )
            
            # Filter for USB mount points (typically under /media/ or /mnt/)
            mount_points = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and (line.startswith('/media/') or line.startswith('/mnt/')) and line != '/':
                    mount_points.append(line)
                    
            return mount_points
            
        except subprocess.CalledProcessError:
            return []
            
    def wait_for_usb_mount(self):
        """Wait for USB devices to mount with smart polling"""
        attempts = 0
        max_attempts = MAX_MOUNT_WAIT * 2  # Check every 0.5 seconds
        devices_found = False
        
        self.logger.info("Waiting for USB devices to mount...")
        
        while attempts < max_attempts:
            mount_points = self.get_usb_mount_points()
            
            if mount_points:
                devices_found = True
                wait_time = attempts * 0.5
                self.logger.info(f"USB device(s) detected after {wait_time:.1f}s")
                time.sleep(0.5)  # Give filesystem time to stabilize
                break
                
            time.sleep(0.5)
            attempts += 1
            
        if not devices_found:
            self.logger.info(f"No USB devices detected after {MAX_MOUNT_WAIT}s timeout")
            
        return devices_found
        
    def is_image_file(self, filepath):
        """Check if file is an image based on extension"""
        return filepath.suffix.lower().lstrip('.') in IMAGE_EXTENSIONS
        
    def generate_unique_filename(self, extension):
        """Generate unique filename with timestamp"""
        timestamp = int(time.time())
        extension = extension.lower()
        
        counter = 1
        while True:
            if counter == 1:
                filename = f"{timestamp}.{extension}"
            else:
                filename = f"{timestamp}_{counter}.{extension}"
                
            dest_path = Path(DEST_DIR) / filename
            if not dest_path.exists():
                return filename
                
            counter += 1
            
    def move_images_from_mount(self, mount_point):
        """Move all images from a specific mount point"""
        mount_path = Path(mount_point)
        image_count = 0
        
        self.logger.info(f"Checking USB device at: {mount_point}")
        
        try:
            # Find all image files recursively
            for file_path in mount_path.rglob('*'):
                if file_path.is_file() and self.is_image_file(file_path):
                    try:
                        original_filename = file_path.name
                        extension = file_path.suffix.lstrip('.')
                        
                        # Generate unique destination filename
                        new_filename = self.generate_unique_filename(extension)
                        dest_path = Path(DEST_DIR) / new_filename
                        
                        # Move the file
                        shutil.move(str(file_path), str(dest_path))
                        self.logger.info(f"Moved: {original_filename} -> {new_filename}")
                        image_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"ERROR: Failed to move {file_path.name}: {e}")
                        
        except PermissionError:
            self.logger.error(f"Permission denied accessing {mount_point}")
        except Exception as e:
            self.logger.error(f"Error processing {mount_point}: {e}")
            
        return image_count
        
    def move_images(self):
        """Find and move images from all mounted USB devices"""
        self.logger.info("Looking for mounted USB devices...")
        
        mount_points = self.get_usb_mount_points()
        
        if not mount_points:
            self.logger.info("No USB devices found mounted")
            return 0
            
        total_moved = 0
        for mount_point in mount_points:
            moved_count = self.move_images_from_mount(mount_point)
            self.logger.info(f"Moved {moved_count} images from {mount_point}")
            total_moved += moved_count
            
        return total_moved
        
    def run_cycle(self):
        """Run one complete USB power cycle"""
        # Power on USB
        self.usb_power_on()
        
        # Wait for devices to mount
        if self.wait_for_usb_mount():
            # Move images
            self.logger.info("Starting image transfer...")
            start_time = time.time()
            total_moved = self.move_images()
            end_time = time.time()
            transfer_time = end_time - start_time
            self.logger.info(f"Image transfer completed in {transfer_time:.1f}s - moved {total_moved} images")
        else:
            self.logger.info("No USB devices detected, skipping image transfer")
            
        # Brief delay to ensure all operations complete
        time.sleep(1)
        
        # Power off USB immediately after transfer
        self.usb_power_off()
        
        # Wait for OFF period
        self.logger.info(f"USB will remain OFF for {OFF_TIME} seconds")
        time.sleep(OFF_TIME)
        
    def run(self):
        """Main loop"""
        self.logger.info("Starting USB cycle service")
        self.logger.info(f"Configuration: OFF={OFF_TIME}s, Destination={DEST_DIR}")
        
        try:
            while True:
                self.run_cycle()
                
        except KeyboardInterrupt:
            self.logger.info("Service stopped by user")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    # Ensure running as root for GPIO access
    if os.geteuid() != 0:
        print("This script must be run as root for GPIO access")
        print("Try: sudo python3 usb_power_cycle.py")
        return 1
        
    try:
        manager = USBCycleManager()
        manager.run()
        return 0
    except Exception as e:
        print(f"Failed to start USB cycle manager: {e}")
        return 1

if __name__ == "__main__":
    exit(main())