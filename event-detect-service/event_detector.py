import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import random
import string

import cv2
from ultralytics import YOLO, YOLOWorld

# --- Constants and Configuration ---

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

# TODO: Old was yolo 8n.pt
# YOLO_MODEL_NAME = "yolov11n.pt"
# YOLO_MODEL_NAME = "yolov8s-world.pt"
YOLO_MODEL_NAME = "yolov8x-worldv2.pt"
POLL_INTERVAL_SECONDS = 60  # Time to wait between directory scans (changed from 5 to 60)

SEVERITY_LOW = 0
SEVERITY_MEDIUM = 1
SEVERITY_HIGH = 2
SEVERITY_CRITICAL = 3

DETECTION_CLASSES = [
    "person",
    "gun", "pistol", "firearm", "rifle",  # Various weapon terms
    "knife", "blade", "dagger",           # Knife variants
    "scissors",
    "baseball bat", "bat",
    "backpack", "bag", "handbag", "suitcase", "luggage"
]

POTENTIAL_WEAPONS = {"gun", "pistol", "firearm", "rifle", "knife", "blade", "dagger", "scissors", "baseball bat", "bat"}
BAG_OBJECTS = {"backpack", "bag", "handbag", "suitcase", "luggage"}

def generate_random_string(length: int = 3) -> str:
    """Generate a random alphanumeric string of given length (default 3)."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

class EventDetector:
    """
    A class to detect objects in images using a YOLO model and determine event severity.
    """

    def __init__(self, model_path: str = YOLO_MODEL_NAME):
        """
        Initializes the EventDetector with a YOLO model.

        Args:
            model_path (str): The path to the YOLO model file.
        """
        try:
            # self.model = YOLO(model_path)
            self.model = YOLOWorld(model_path)
            self.model.set_classes(DETECTION_CLASSES)

            logging.info(f"Successfully loaded model '{model_path}'")
        except Exception as e:
            logging.error(f"Failed to load YOLO model from '{model_path}'. Error: {e}")
            sys.exit(1)

    def detect_objects(self, image_path: Path) -> List[Dict[str, Any]]:
        """
        Detects target objects in a single image.

        Args:
            image_path (Path): The path to the image file.

        Returns:
            List[Dict[str, Any]]: A list of detected objects.
        """
        logging.debug(f"detect_objects() called with image_path={image_path}")
        if not image_path.is_file():
            logging.error(f"Image file not found during detection: {image_path}")
            return []

        try:
            image = cv2.imread(str(image_path))
            if image is None:
                logging.error(f"Could not read image file: {image_path}")
                return []
        except Exception as e:
            logging.error(f"Error reading image {image_path}: {e}")
            return []

        logging.debug(f"Running YOLO model on image: {image_path}")
        results = self.model(image)
        
        logging.info(f"Results: {results}")

        detected_boxes = []
        for r in results:
            for box in r.boxes:
                object_name = self.model.names[int(box.cls)]
                
                logging.info(f"Object name: {object_name} | Confidence: {box.conf}")

                detected_boxes.append({
                    'box': box.xyxy[0].cpu().numpy(),
                    'label': object_name,
                    'confidence': float(box.conf),
                })

        if detected_boxes:
            labels = {obj['label'] for obj in detected_boxes}
            logging.info(f"Found objects in {image_path.name}: {list(labels)}")

            all_classes = [(obj['label'], obj['confidence']) for obj in detected_boxes]
            logging.info(f"All detected classes in {image_path.name}: {all_classes}")
        else:
            logging.info(f"No objects found in {image_path.name}")

        logging.debug(f"detect_objects() returning {len(detected_boxes)} objects.")
        return detected_boxes

    @staticmethod
    def determine_severity(detected_objects: List[Dict[str, Any]]) -> int:
        """
        Determines a severity level for filename classification.

        Args:
            detected_objects (List[Dict[str, Any]]): A list of detected object data.

        Returns:
            int: The calculated severity level (0=low, 1=medium, 2=high, 3=critical).
        """
        logging.debug(f"determine_severity() called with detected_objects={detected_objects}")
        if not detected_objects:
            logging.info("No detected objects, returning SEVERITY_LOW.")
            return SEVERITY_LOW

        label_set = {obj['label'] for obj in detected_objects}
        logging.debug(f"Labels found: {label_set}")

        # No person detected = LOW severity
        if "person" not in label_set:
            logging.info("No person detected, returning SEVERITY_LOW.")
            return SEVERITY_LOW

        # Person detected - check for weapons and bags
        has_weapon = "gun" in label_set or "knife" in label_set or "scissors" in label_set or "baseball bat" in label_set
        has_bag = "backpack" in label_set or "handbag" in label_set or "suitcase" in label_set

        # Person + weapon = CRITICAL
        if has_weapon:
            logging.info("Person + weapon detected, returning SEVERITY_CRITICAL.")
            return SEVERITY_CRITICAL
        
        # Person + bag = HIGH
        if has_bag:
            logging.info("Person + bag detected, returning SEVERITY_HIGH.")
            return SEVERITY_HIGH
        
        logging.info("Person detected, returning SEVERITY_MEDIUM.")
        return SEVERITY_MEDIUM

class ProcessingService:
    """
    Manages the processing of images from a source directory to a destination.
    """
    def __init__(self, detector: EventDetector, source_dir: Path, processed_dir: Path):
        self.detector = detector
        self.source_dir = source_dir
        self.processed_dir = processed_dir
        self.critical_dir = processed_dir / "critical"
        self.is_running = False
        self.last_processed_timestamp = None  # Track the last processed timestamp

        # Create directories if they don't exist
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.critical_dir.mkdir(exist_ok=True)
        logging.info(f"Monitoring source directory: {self.source_dir}")
        logging.info(f"Processed images will be saved to: {self.processed_dir}")
        logging.info(f"Critical images (person + weapon/bag) will be saved to: {self.critical_dir}")
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig, frame):
            self.stop()
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def find_priority_object(self, detected_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        # First priority: person
        for obj in detected_objects:
            if obj['label'] == "person":
                return obj
            
        # Second priority: weapons
        for obj in detected_objects:
            if obj['label'] in POTENTIAL_WEAPONS:
                return obj
            
        # Last priority: bags
        for obj in detected_objects:
            if obj['label'] in BAG_OBJECTS:
                return obj
        return None

    def _extract_epoch_from_filename(self, filename: str) -> Optional[int]:
        """Extracts the epoch timestamp from the filename (expects format like 1718131200.jpg)."""
        try:
            base = filename.split(".")[0]
            return int(base)
        except Exception:
            return None

    def _get_latest_image(self, image_files: List[Path]) -> Optional[Path]:
        """
        Returns the latest image based on epoch timestamp in filename or file modification time.
        
        Args:
            image_files (List[Path]): List of image file paths
            
        Returns:
            Optional[Path]: The latest image file, or None if no images found
        """
        if not image_files:
            return None
            
        latest_image = None
        latest_timestamp = 0
        
        for image_path in image_files:
            # Try to get epoch from filename first
            epoch = self._extract_epoch_from_filename(image_path.name)
            
            if epoch is not None:
                timestamp = epoch
            else:
                # Fall back to file modification time
                timestamp = int(image_path.stat().st_mtime)
            
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
                latest_image = image_path
                
        return latest_image

    def _delete_stale_images(self, image_files: List[Path]):
        """
        Delete images that are more than 10 minutes older than the last processed timestamp.
        
        Args:
            image_files (List[Path]): List of image file paths to check
        """
        if self.last_processed_timestamp is None:
            return
            
        # stale_threshold = 600  # 10 minutes in seconds (changed from 900 to 600)
        stale_threshold = 5  # 5 seconds in seconds (changed from 900 to 600)

        
        for image_path in image_files:
            # Try to get epoch from filename first
            epoch = self._extract_epoch_from_filename(image_path.name)
            
            if epoch is not None:
                image_timestamp = epoch
            else:
                # Fall back to file modification time
                image_timestamp = int(image_path.stat().st_mtime)
            
            # Delete if image is more than 10 minutes older than last processed
            if self.last_processed_timestamp - image_timestamp > stale_threshold:
                logging.info(f"Deleting stale image {image_path.name} (timestamp {image_timestamp}) older than 10 min from last processed timestamp {self.last_processed_timestamp}.")
                try:
                    image_path.unlink()
                except OSError as e:
                    logging.error(f"Error deleting stale file {image_path}: {e}")

    def process_and_store_image(self, image_path: Path, image_timestamp: Optional[int] = None):
        """
        Processes a single image: detects objects, determines severity,
        saves files, and deletes the original.
        """
        logging.info(f"Processing latest file: {image_path.name} | Last processed timestamp: {self.last_processed_timestamp}")
        logging.debug(f"process_and_store_image() called with image_path={image_path}, image_timestamp={image_timestamp}")

        # Update last processed timestamp
        if image_timestamp is not None:
            self.last_processed_timestamp = image_timestamp
            logging.info(f"Updated last processed timestamp to: {self.last_processed_timestamp}")

        detected_objects = self.detector.detect_objects(image_path)
        logging.debug(f"Detected objects: {detected_objects}")

        if not detected_objects:
            logging.info(f"No objects to process in {image_path.name}. Deleting original.")
            try:
                image_path.unlink()
                logging.debug(f"Deleted original file: {image_path}")
            except OSError as e:
                logging.error(f"Error deleting original file {image_path}: {e}")
            return

        severity = self.detector.determine_severity(detected_objects)
        logging.info(f"Determined severity for {image_path.name}: {severity}")
        timestamp = time.strftime("%H%M%S", time.localtime())
        
        original_image = cv2.imread(str(image_path))
        if original_image is None:
            logging.error(f"Could not re-read image for saving: {image_path}")
            return

        detected_labels = {obj['label'] for obj in detected_objects}
        has_person = "person" in detected_labels
        has_bag = not detected_labels.isdisjoint(BAG_OBJECTS)
        has_weapon = not detected_labels.isdisjoint(POTENTIAL_WEAPONS)
        is_critical = severity == SEVERITY_CRITICAL or severity == SEVERITY_HIGH or has_person
        
        logging.debug(f"Image {image_path.name}: has_person={has_person}, has_bag={has_bag}, has_weapon={has_weapon}, is_critical={is_critical}")

        save_dir = self.critical_dir if is_critical else self.processed_dir
        uid = generate_random_string()
        
        if is_critical:
            critical_reasons = []
            if has_person and has_weapon:
                critical_reasons.append("person + weapon")
            elif has_person and has_bag:
                critical_reasons.append("person + bag")
            logging.warning(f"CRITICAL/HIGH SEVERITY DETECTED ({', '.join(critical_reasons)}). Saving to critical folder: {save_dir}")
        else:
            logging.info(f"No critical content detected. Saving to standard folder: {save_dir}")

        # 1. Save the full image to the determined directory.
        full_image_name = f"{severity}_{timestamp}_{uid}_f.jpg"
        full_save_path = save_dir / full_image_name
        cv2.imwrite(str(full_save_path), original_image)
        logging.info(f"Saved full image to: {full_save_path}")

        # 2. Save ONE cropped version if there's a weapon or bag
        priority_object = self.find_priority_object(detected_objects)
        logging.debug(f"Priority object for cropping: {priority_object}")
        
        if priority_object:
            cropped_image_name = f"{severity}_{timestamp}_{uid}_c.jpg"
            cropped_save_path = save_dir / cropped_image_name

            box = priority_object['box']
            x1, y1, x2, y2 = map(int, box)

            h, w = original_image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            cropped_image = original_image[y1:y2, x1:x2]

            if cropped_image.size > 0:
                cv2.imwrite(str(cropped_save_path), cropped_image)
                logging.info(f"Saved cropped {priority_object['label']} to: {cropped_save_path}")
            else:
                logging.warning(f"Skipping empty crop for {priority_object['label']} in {image_path.name}")

        # 3. Delete the original file
        try:
            image_path.unlink()
            logging.info(f"Successfully processed and deleted original: {image_path.name}")
        except OSError as e:
            logging.error(f"Error deleting original file {image_path}: {e}")

    def start_service_loop(self):
        logging.info("Entered ProcessingService.start_service_loop(). Beginning monitoring loop.")
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
        while self.is_running:
            try:
                logging.debug(f"Scanning directory: {self.source_dir}")
                image_files = [
                    p for p in self.source_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in image_extensions
                ]
                logging.debug(f"Found image files: {[str(p) for p in image_files]}")

                if not image_files:
                    logging.info(f"No images found. Waiting for {POLL_INTERVAL_SECONDS}s... | Last processed timestamp: {self.last_processed_timestamp}")
                else:
                    # Get the latest image
                    latest_image = self._get_latest_image(image_files)
                    logging.debug(f"Latest image selected: {latest_image}")
                    
                    if latest_image:
                        # Get timestamp for the latest image
                        epoch = self._extract_epoch_from_filename(latest_image.name)
                        if epoch is None:
                            epoch = int(latest_image.stat().st_mtime)
                        logging.debug(f"Processing image {latest_image.name} with epoch {epoch}")
                        # Process only the latest image
                        self.process_and_store_image(latest_image, image_timestamp=epoch)
                        
                        # After processing, delete any stale images
                        remaining_files = [
                            p for p in self.source_dir.iterdir()
                            if p.is_file() and p.suffix.lower() in image_extensions
                        ]
                        logging.debug(f"Checking for stale images in: {[str(p) for p in remaining_files]}")
                        self._delete_stale_images(remaining_files)

                time.sleep(POLL_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logging.info("Service stopped by user.")
                break
            except Exception as e:
                logging.error(f"An unexpected error occurred in the monitoring loop: {e}", exc_info=True)
                time.sleep(POLL_INTERVAL_SECONDS * 2) # Wait longer after an error
        logging.info("Exiting ProcessingService.start_service_loop().")

    def start(self):
        """
        Starts the continuous monitoring loop.
        """
        logging.info("ProcessingService.start() called. Starting service thread.")
        try:
            self.is_running = True
            thread = threading.Thread(target=self.start_service_loop)
            thread.start()
            logging.debug("Service thread started.")
        except Exception as e:
            logging.error(f"An unexpected error occurred in the monitoring loop: {e}", exc_info=True)
            sys.exit(1)
    
    def stop(self):
        """
        Stops the continuous monitoring loop.
        """
        self.is_running = False

def main():
    """Main function to parse arguments and run the service."""
    logging.info("Starting main()")
    parser = argparse.ArgumentParser(
        description="A service to monitor a directory for images, process them, and store the results.",
        epilog="Example: python event_detector.py /path/to/watch --output /path/to/save"
    )

    parser.add_argument(
        "source_directory",
        type=Path,
        help="The directory to monitor for new image files."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.home() / "Documents" / "processed_images",
        help="The directory where processed images will be stored. Defaults to ~/processed_images."
    )

    args = parser.parse_args()
    logging.info(f"Parsed arguments: source_directory={args.source_directory}, output={args.output}")

    if not args.source_directory.is_dir():
        logging.error(f"Source directory does not exist or is not a directory: {args.source_directory}")
        sys.exit(1)

    logging.info("Instantiating EventDetector...")
    detector = EventDetector()
    logging.info("Instantiating ProcessingService...")
    service = ProcessingService(
        detector=detector,
        source_dir=args.source_directory,
        processed_dir=args.output
    )

    logging.info("Starting ProcessingService...")
    service.start()
    print("Service started")
    while service.is_running:
        time.sleep(1)
    logging.info("Service loop exited. main() complete.")

if __name__ == "__main__":
    main()
