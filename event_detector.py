import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import cv2
from ultralytics import YOLO

# --- Constants and Configuration ---

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

YOLO_MODEL_NAME = "yolov8n.pt"
POLL_INTERVAL_SECONDS = 5  # Time to wait between directory scans

SEVERITY_LOW = 0
SEVERITY_MEDIUM = 1
SEVERITY_HIGH = 2
SEVERITY_CRITICAL = 3

POTENTIAL_WEAPONS = {"knife", "scissors", "baseball bat", "gun"}
BAG_OBJECTS = {"backpack", "handbag", "suitcase"}


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
            self.model = YOLO(model_path)
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

        results = self.model(image)

        detected_boxes = []
        for r in results:
            for box in r.boxes:
                object_name = self.model.names[int(box.cls)]
                detected_boxes.append({
                    'box': box.xyxy[0].cpu().numpy(),
                    'label': object_name,
                    'confidence': float(box.conf),
                })

        if detected_boxes:
            labels = {obj['label'] for obj in detected_boxes}
            logging.info(f"Found objects in {image_path.name}: {list(labels)}")
        else:
            logging.info(f"No objects found in {image_path.name}")

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
        if not detected_objects:
            return SEVERITY_LOW

        label_set = {obj['label'] for obj in detected_objects}

        # Level 3 (Critical): Presence of a potential weapon.
        if not label_set.isdisjoint(POTENTIAL_WEAPONS):
            return SEVERITY_CRITICAL

        # Level 2 (High): Presence of any person.
        if "person" in label_set:
            return SEVERITY_HIGH

        # Level 1 (Medium): Presence of a bag without a person.
        if not label_set.isdisjoint(BAG_OBJECTS):
            return SEVERITY_MEDIUM

        # Level 0 (Low): Default for any other detected object(s).
        return SEVERITY_LOW

class ProcessingService:
    """
    Manages the processing of images from a source directory to a destination.
    """
    def __init__(self, detector: EventDetector, source_dir: Path, processed_dir: Path):
        self.detector = detector
        self.source_dir = source_dir
        self.processed_dir = processed_dir
        self.critical_dir = processed_dir / "critical"

        # Create directories if they don't exist
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.critical_dir.mkdir(exist_ok=True)
        logging.info(f"Monitoring source directory: {self.source_dir}")
        logging.info(f"Processed images will be saved to: {self.processed_dir}")
        logging.info(f"Critical images (person/bag/weapon) will be saved to: {self.critical_dir}")


    def process_and_store_image(self, image_path: Path):
        """
        Processes a single image: detects objects, determines severity,
        saves files, and deletes the original.
        """
        logging.info(f"Processing new file: {image_path.name}")

        detected_objects = self.detector.detect_objects(image_path)

        if not detected_objects:
            logging.info(f"No objects to process in {image_path.name}. Deleting original.")
            try:
                image_path.unlink()
            except OSError as e:
                logging.error(f"Error deleting original file {image_path}: {e}")
            return

        severity = self.detector.determine_severity(detected_objects)
        timestamp = time.strftime("%H%M%S", time.localtime())
        
        original_image = cv2.imread(str(image_path))
        if original_image is None:
            logging.error(f"Could not re-read image for saving: {image_path}")
            return

        detected_labels = {obj['label'] for obj in detected_objects}
        has_person = "person" in detected_labels
        has_bag = not detected_labels.isdisjoint(BAG_OBJECTS)
        has_weapon = not detected_labels.isdisjoint(POTENTIAL_WEAPONS)
        is_critical = has_person or has_bag or has_weapon
        save_dir = self.critical_dir if is_critical else self.processed_dir
        
        if is_critical:
            critical_reasons = []
            if has_person:
                critical_reasons.append("person")
            if has_bag:
                critical_reasons.append("bag")
            if has_weapon:
                critical_reasons.append("weapon")
            logging.warning(f"CRITICAL CONTENT DETECTED ({', '.join(critical_reasons)}). Saving to critical folder: {save_dir}")
        else:
            logging.info(f"No critical content detected. Saving to standard folder: {save_dir}")


        # 1. Save the full image to the determined directory.
        full_image_name = f"{severity}_{timestamp}_f.jpg"
        full_save_path = save_dir / full_image_name
        cv2.imwrite(str(full_save_path), original_image)
        logging.info(f"Saved full image to: {full_save_path}")

        # 2. Save cropped versions to the SAME directory.
        for i, obj_data in enumerate(detected_objects):
            cropped_image_name = f"{severity}_{timestamp}_c_{i+1}.jpg"
            cropped_save_path = save_dir / cropped_image_name

            box = obj_data['box']
            x1, y1, x2, y2 = map(int, box)

            h, w = original_image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            cropped_image = original_image[y1:y2, x1:x2]

            if cropped_image.size > 0:
                cv2.imwrite(str(cropped_save_path), cropped_image)
                logging.info(f"Saved cropped image to: {cropped_save_path}")
            else:
                logging.warning(f"Skipping empty crop for object {i+1} in {image_path.name}")

        # 3. Delete the original file
        try:
            image_path.unlink()
            logging.info(f"Successfully processed and deleted original: {image_path.name}")
        except OSError as e:
            logging.error(f"Error deleting original file {image_path}: {e}")

    def run(self):
        """
        Starts the continuous monitoring loop.
        """
        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}

        while True:
            try:
                image_files = [
                    p for p in self.source_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in image_extensions
                ]

                if not image_files:
                    logging.info(f"No new images found. Waiting for {POLL_INTERVAL_SECONDS}s...")
                else:
                    for image_path in image_files:
                        self.process_and_store_image(image_path)

                time.sleep(POLL_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logging.info("Service stopped by user.")
                break
            except Exception as e:
                logging.error(f"An unexpected error occurred in the monitoring loop: {e}", exc_info=True)
                time.sleep(POLL_INTERVAL_SECONDS * 2) # Wait longer after an error

def main():
    """Main function to parse arguments and run the service."""
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
        help="The directory where processed images will be stored. Defaults to ~/Documents/processed_images."
    )

    args = parser.parse_args()

    if not args.source_directory.is_dir():
        logging.error(f"Source directory does not exist or is not a directory: {args.source_directory}")
        sys.exit(1)

    detector = EventDetector()
    service = ProcessingService(
        detector=detector,
        source_dir=args.source_directory,
        processed_dir=args.output
    )

    service.run()

if __name__ == "__main__":
    main()