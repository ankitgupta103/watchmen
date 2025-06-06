import os
import time
import shutil
import logging
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import RPi.GPIO as GPIO

# Local imports
from detect import Detector
from vyomcloudbridge.services.queue_writer_json import QueueWriterJson

# Configuration
POWER_PIN = 11  # GPIO pin connected to MOSFET trigger (GPIO 17)
OFF_TIME = 60  # Seconds to keep USB power off
MAX_MOUNT_WAIT = 10  # Maximum seconds to wait for device mount
PROCESSED_DIR = "/tmp/camera_captures"
ARCHIVE_DIR = "/tmp/camera_archive"
LOG_FILE = "/var/log/usb-camera.log"

# Image file extensions to process
IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 
    'webp', 'raw', 'cr2', 'nef', 'dng'
}

# Health event types mapping
HEALTH_EVENT_TYPES = {
    'offline': 'offline',
    'usb_failure': 'hardware_failure',
    'mount_failure': 'hardware_failure',
    'detection_failure': 'hardware_failure',
    'power_failure': 'hardware_failure'
}

# Suspicious event types mapping
SUSPICIOUS_EVENT_TYPES = {
    'person': 'human_detection',
    'weapon': 'weapon_detection',
    'unusual': 'unusual_activity'
}

class USBCamera:
    def __init__(self, devid: str, mission_id: str = "watchmen_surveillance"):
        self.devid = devid
        self.mission_id = mission_id
        self.setup_logging()
        self.setup_gpio()
        self.setup_directories()
        self.setup_detector()
        self.setup_mqtt_writer()
        
        # Statistics
        self.image_count = 0
        self.detection_count = 0
        self.health_events = []
        self.suspicious_events = []
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_gpio(self):
        """Setup GPIO for MOSFET control"""
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(POWER_PIN, GPIO.OUT)
            GPIO.output(POWER_PIN, GPIO.LOW)  # Start with USB power OFF
            self.logger.info(f"GPIO {POWER_PIN} configured for MOSFET control")
        except Exception as e:
            self.logger.error(f"GPIO setup failed: {e}")
            self._record_health_event('hardware_failure', 'high', f"GPIO setup failed: {e}")
            
    def setup_directories(self):
        """Create necessary directories"""
        for directory in [PROCESSED_DIR, ARCHIVE_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Directories configured - Processed: {PROCESSED_DIR}, Archive: {ARCHIVE_DIR}")
        
    def setup_detector(self):
        """Initialize AI detector"""
        try:
            self.detector = Detector()
            self.logger.info("AI detector initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize detector: {e}")
            self.detector = None
            self._record_health_event('hardware_failure', 'critical', f"AI detector initialization failed: {e}")
            
    def setup_mqtt_writer(self):
        """Initialize MQTT writer"""
        try:
            self.writer = QueueWriterJson()
            self.logger.info("MQTT writer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MQTT writer: {e}")
            self.writer = None
            self._record_health_event('offline', 'high', f"MQTT writer initialization failed: {e}")
            
    def cleanup(self):
        """Cleanup GPIO and resources on exit"""
        try:
            GPIO.cleanup()
            if self.writer:
                self.writer.cleanup()
            self.logger.info("Resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            
    def _record_health_event(self, event_type: str, severity: str, details: str = ""):
        """Record a health event"""
        health_event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "severity": severity,
            "details": details,
            "machine_id": self.devid
        }
        self.health_events.append(health_event)
        self.logger.warning(f"Health event recorded: {event_type} ({severity}) - {details}")
        
        # Send health event via MQTT
        self._publish_health_event(health_event)
        
    def _record_suspicious_event(self, event_type: str, confidence: float, image_path: str, details: Dict = None):
        """Record a suspicious event"""
        suspicious_event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "confidence": confidence,
            "url": image_path,
            "marked": "unreviewed",
            "machine_id": self.devid,
            "details": details or {}
        }
        self.suspicious_events.append(suspicious_event)
        self.detection_count += 1
        self.logger.info(f"Suspicious event recorded: {event_type} (confidence: {confidence:.2f}) - {image_path}")
        
        # Send suspicious event via MQTT
        self._publish_suspicious_event(suspicious_event)
        
    def usb_power_on(self):
        """Turn on USB power via MOSFET"""
        try:
            self.logger.info("Powering ON USB via MOSFET")
            GPIO.output(POWER_PIN, GPIO.HIGH)
            time.sleep(2)  # Give power time to stabilize
        except Exception as e:
            self.logger.error(f"Failed to power on USB: {e}")
            self._record_health_event('power_failure', 'high', f"USB power on failed: {e}")
            
    def usb_power_off(self):
        """Turn off USB power via MOSFET"""
        try:
            self.logger.info("Powering OFF USB via MOSFET")
            GPIO.output(POWER_PIN, GPIO.LOW)
            time.sleep(1)
        except Exception as e:
            self.logger.error(f"Failed to power off USB: {e}")
            self._record_health_event('power_failure', 'medium', f"USB power off failed: {e}")
            
    def get_usb_mount_points(self) -> List[str]:
        """Find all mounted USB devices"""
        try:
            result = subprocess.run(
                ['findmnt', '-lo', 'TARGET', '-t', 'vfat,ntfs,exfat,ext4'],
                capture_output=True, text=True, check=True
            )
            
            mount_points = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and (line.startswith('/media/') or line.startswith('/mnt/')) and line != '/':
                    mount_points.append(line)
                    
            return mount_points
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get USB mount points: {e}")
            self._record_health_event('usb_failure', 'medium', f"Failed to detect USB devices: {e}")
            return []
            
    def wait_for_usb_mount(self) -> bool:
        """Wait for USB devices to mount with smart polling"""
        attempts = 0
        max_attempts = MAX_MOUNT_WAIT * 2
        devices_found = False
        
        self.logger.info("Waiting for USB devices to mount...")
        
        while attempts < max_attempts:
            mount_points = self.get_usb_mount_points()
            
            if mount_points:
                devices_found = True
                wait_time = attempts * 0.5
                self.logger.info(f"USB device(s) detected after {wait_time:.1f}s: {mount_points}")
                time.sleep(0.5)  # Give filesystem time to stabilize
                break
                
            time.sleep(0.5)
            attempts += 1
            
        if not devices_found:
            self.logger.warning(f"No USB devices detected after {MAX_MOUNT_WAIT}s timeout")
            self._record_health_event('usb_failure', 'medium', f"No USB devices detected after {MAX_MOUNT_WAIT}s")
            
        return devices_found
        
    def is_image_file(self, filepath: Path) -> bool:
        """Check if file is an image based on extension"""
        return filepath.suffix.lower().lstrip('.') in IMAGE_EXTENSIONS
        
    def generate_unique_filename(self, original_name: str) -> str:
        """Generate unique filename with timestamp and device ID"""
        timestamp = int(time.time() * 1000000)  # Microsecond precision
        extension = Path(original_name).suffix
        filename = f"capture_{self.devid}_{timestamp}{extension}"
        
        counter = 1
        while True:
            if counter == 1:
                final_filename = filename
            else:
                name_part = filename.rsplit('.', 1)[0]
                ext_part = filename.rsplit('.', 1)[1] if '.' in filename else ''
                final_filename = f"{name_part}_{counter}.{ext_part}" if ext_part else f"{name_part}_{counter}"
                
            dest_path = Path(PROCESSED_DIR) / final_filename
            if not dest_path.exists():
                return final_filename
                
            counter += 1
            
    def process_image(self, image_path: Path) -> Tuple[str, str]:
        """Process a single image with AI detection"""
        try:
            # Move image to processed directory
            new_filename = self.generate_unique_filename(image_path.name)
            dest_path = Path(PROCESSED_DIR) / new_filename
            shutil.copy2(str(image_path), str(dest_path))
            
            self.image_count += 1
            self.logger.info(f"Processing image: {image_path.name} -> {new_filename}")
            
            # Run AI detection if detector is available
            detection_result = ""
            if self.detector:
                try:
                    has_person = self.detector.ImageHasPerson(str(dest_path))
                    if has_person:
                        confidence = 0.85  # Default confidence, could be enhanced to get actual confidence
                        self._record_suspicious_event(
                            'human_detection', 
                            confidence, 
                            str(dest_path),
                            {"original_filename": image_path.name}
                        )
                        detection_result = f"Person detected (confidence: {confidence:.2f})"
                    else:
                        detection_result = "No person detected"
                        
                except Exception as e:
                    self.logger.error(f"Detection failed for {new_filename}: {e}")
                    self._record_health_event('detection_failure', 'medium', f"AI detection failed: {e}")
                    detection_result = f"Detection failed: {e}"
            else:
                detection_result = "Detector not available"
                
            # Archive original image
            archive_path = Path(ARCHIVE_DIR) / new_filename
            shutil.move(str(image_path), str(archive_path))
            
            return str(dest_path), detection_result
            
        except Exception as e:
            self.logger.error(f"Failed to process image {image_path.name}: {e}")
            return "", f"Processing failed: {e}"
            
    def transfer_and_process_images(self, mount_point: str) -> int:
        """Transfer and process all images from a USB mount point"""
        mount_path = Path(mount_point)
        processed_count = 0
        
        self.logger.info(f"Processing images from USB device at: {mount_point}")
        
        try:
            # Find all image files recursively
            for file_path in mount_path.rglob('*'):
                if file_path.is_file() and self.is_image_file(file_path):
                    try:
                        processed_path, result = self.process_image(file_path)
                        if processed_path:
                            processed_count += 1
                            self.logger.info(f"Processed {file_path.name}: {result}")
                        else:
                            self.logger.error(f"Failed to process {file_path.name}: {result}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path.name}: {e}")
                        
        except PermissionError:
            error_msg = f"Permission denied accessing {mount_point}"
            self.logger.error(error_msg)
            self._record_health_event('usb_failure', 'medium', error_msg)
        except Exception as e:
            error_msg = f"Error processing {mount_point}: {e}"
            self.logger.error(error_msg)
            self._record_health_event('usb_failure', 'medium', error_msg)
            
        return processed_count
        
    def _publish_health_event(self, health_event: Dict):
        """Store health event locally - MQTT publishing disabled for individual devices"""
        # Individual devices don't publish to MQTT - only log locally
        # Central device will collect and publish these events
        self.logger.info(f"Health event recorded locally: {health_event}")
        
    def _publish_suspicious_event(self, suspicious_event: Dict):
        """Store suspicious event locally - MQTT publishing disabled for individual devices"""
        # Individual devices don't publish to MQTT - only log locally  
        # Central device will collect and publish these events
        self.logger.info(f"Suspicious event recorded locally: {suspicious_event}")
        
    def _publish_activity_summary(self):
        """Store activity summary locally - MQTT publishing disabled for individual devices"""
        # Individual devices don't publish to MQTT - only log locally
        # Central device will collect and publish these summaries
        summary = {
            "event_type": "activity_summary",
            "machine_id": self.devid,
            "machine_name": f"Camera_{self.devid}",
            "timestamp": datetime.now().isoformat(),
            "total_images_processed": self.image_count,
            "total_detections": self.detection_count,
            "health_events_count": len(self.health_events),
            "suspicious_events_count": len(self.suspicious_events),
            "mission_id": self.mission_id,
            "uptime_hours": time.time() / 3600
        }
        self.logger.info(f"Activity summary recorded locally: {summary}")
        
    def get_events_for_central(self) -> Dict:
        """Get all events for central device to publish via MQTT"""
        return {
            "device_id": self.devid,
            "timestamp": datetime.now().isoformat(),
            "health_events": self.health_events.copy(),
            "suspicious_events": self.suspicious_events.copy(),
            "activity_summary": {
                "total_images_processed": self.image_count,
                "total_detections": self.detection_count,
                "health_events_count": len(self.health_events),
                "suspicious_events_count": len(self.suspicious_events),
                "mission_id": self.mission_id
            }
        }
            
    def take_picture(self) -> Tuple[str, str]:
        """Main method to trigger USB image collection and processing (replaces original take_picture)"""
        try:
            # Power on USB
            self.usb_power_on()
            
            # Wait for devices to mount
            if self.wait_for_usb_mount():
                # Process images from all mounted USB devices
                self.logger.info("Starting image transfer and processing...")
                start_time = time.time()
                
                mount_points = self.get_usb_mount_points()
                total_processed = 0
                
                for mount_point in mount_points:
                    processed_count = self.transfer_and_process_images(mount_point)
                    total_processed += processed_count
                    self.logger.info(f"Processed {processed_count} images from {mount_point}")
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                self.logger.info(f"Image processing completed in {processing_time:.1f}s - processed {total_processed} images")
                
                # Return summary information
                if total_processed > 0:
                    summary = f"Processed {total_processed} images, {self.detection_count} detections found"
                    return f"{PROCESSED_DIR}/latest_batch", summary
                else:
                    return "", "No images found for processing"
                    
            else:
                self.logger.info("No USB devices detected, skipping image processing")
                self._record_health_event('usb_failure', 'low', "No USB devices detected")
                return "", "No USB devices detected"
                
        except Exception as e:
            error_msg = f"Image capture cycle failed: {e}"
            self.logger.error(error_msg)
            self._record_health_event('hardware_failure', 'high', error_msg)
            return "", error_msg
            
        finally:
            # Always power off USB after processing
            time.sleep(1)
            self.usb_power_off()
            
    def start(self):
        """Initialize the camera system"""
        self.logger.info(f"Starting USB Camera system for device {self.devid}")
        self.logger.info(f"Configuration: OFF_TIME={OFF_TIME}s, Mission={self.mission_id}")
        
    def run_continuous_cycle(self, cycle_interval: int = 300):
        """Run continuous monitoring cycle"""
        self.logger.info(f"Starting continuous monitoring cycle (interval: {cycle_interval}s)")
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                self.logger.info(f"Starting cycle #{cycle_count}")
                
                # Run image capture and processing
                filepath, result = self.take_picture()
                self.logger.info(f"Cycle #{cycle_count} result: {result}")
                
                # Publish activity summary every 10 cycles
                if cycle_count % 10 == 0:
                    self._publish_activity_summary()
                
                # Wait for next cycle
                self.logger.info(f"Waiting {cycle_interval}s before next cycle...")
                time.sleep(cycle_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Continuous monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Continuous monitoring failed: {e}")
            self._record_health_event('hardware_failure', 'critical', f"System failure: {e}")
        finally:
            self.cleanup()

def main():
    """Main entry point for testing"""
    if os.geteuid() != 0:
        print("This script must be run as root for GPIO access")
        print("Try: sudo python3 camera.py")
        return 1
        
    try:
        # Create camera instance
        camera = USBCamera("TEST_CAM_001", "test_mission")
        camera.start()
        
        # Run a single capture cycle for testing
        filepath, result = camera.take_picture()
        print(f"Capture result: {result}")
        
        # Optionally run continuous monitoring
        # camera.run_continuous_cycle(cycle_interval=120)
        
        return 0
        
    except Exception as e:
        print(f"Failed to start USB camera: {e}")
        return 1

if __name__ == "__main__":
    exit(main())