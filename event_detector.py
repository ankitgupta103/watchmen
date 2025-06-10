import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

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

# Predefined detection categories for easy access
DETECTION_CATEGORIES: Dict[str, List[str]] = {
    "people": ["person"],
    "suspicious_items": ["backpack", "handbag", "suitcase", "knife", "scissors", "bottle"],
    "bags": ["backpack", "handbag", "suitcase"],
    "potential_weapons": ["knife", "scissors", "baseball bat"], # Removed 'gun' as it is not in yolov8n.pt
    "vehicles": ["car", "motorcycle", "bicycle", "bus", "truck"],
    "electronics": ["laptop", "cell phone"],
    "all": [],  # Empty list means all objects will be detected
}

# --- Main Application Class ---

class EventDetector:
    """
    A class to detect objects in images using a YOLO model.
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
            logging.info(f"Available classes: {', '.join(self.get_available_classes())}")
        except Exception as e:
            logging.error(f"Failed to load YOLO model from '{model_path}'. Error: {e}")
            sys.exit(1)
            
        self.target_objects: List[str] = ["person"]  # Default to detecting persons

    def set_detection_category(self, category: str):
        """
        Sets the object detection filter using a predefined category.

        Args:
            category (str): The name of the category (e.g., 'people', 'vehicles').
        """
        if category in DETECTION_CATEGORIES:
            self.target_objects = DETECTION_CATEGORIES[category]
            target_str = f"'{category}': {self.target_objects}" if self.target_objects else "'all'"
            logging.info(f"Detection category set to {target_str}")
        else:
            logging.warning(
                f"Unknown category '{category}'. "
                f"Available categories: {list(DETECTION_CATEGORIES.keys())}"
            )

    def set_custom_objects(self, objects: List[str]):
        """
        Sets a custom list of objects to detect.

        Args:
            objects (List[str]): A list of class names to detect.
        """
        self.target_objects = objects
        logging.info(f"Detection set to custom objects: {self.target_objects}")

    def get_available_classes(self) -> List[str]:
        """
        Returns a list of all class names the loaded model can detect.
        
        Returns:
            List[str]: A sorted list of class names.
        """
        return sorted(list(self.model.names.values()))

    def detect_objects(self, image_path: Path) -> List[Dict[str, Any]]:
        """
        Detects target objects in a single image.

        Args:
            image_path (Path): The path to the image file.

        Returns:
            List[Dict[str, Any]]: A list of detected objects, where each object is a
                                 dictionary containing 'box', 'label', and 'confidence'.
                                 Returns an empty list if no objects are found or the
                                 image cannot be read.
        """
        if not image_path.is_file():
            logging.error(f"Image file not found: {image_path}")
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
            for i, box in enumerate(r.boxes):
                object_name = self.model.names[int(box.cls)]
                
                # Filter by target objects if a filter is set
                if not self.target_objects or object_name in self.target_objects:
                    detected_boxes.append({
                        'box': box.xyxy[0].cpu().numpy(),
                        'label': object_name,
                        'confidence': float(box.conf),
                    })
        
        if detected_boxes:
            labels = [obj['label'] for obj in detected_boxes]
            logging.info(f"Found objects in {image_path.name}: {labels}")
        else:
            logging.info(f"No target objects found in {image_path.name}")
            
        return detected_boxes

    def save_cropped_objects(self, image_path: Path, detected_objects: List[Dict[str, Any]]):
        """
        Crops and saves detected objects from the original image.

        Args:
            image_path (Path): Path to the original image file.
            detected_objects (List[Dict[str, Any]]): The list of detected objects from `detect_objects`.
        """
        try:
            original_image = cv2.imread(str(image_path))
            if original_image is None:
                logging.error(f"Cannot read original image for cropping: {image_path}")
                return
        except Exception as e:
            logging.error(f"Error reading original image {image_path} for cropping: {e}")
            return
            
        for i, obj_data in enumerate(detected_objects):
            box = obj_data['box']
            label = obj_data['label']
            confidence = obj_data['confidence']
            
            x1, y1, x2, y2 = map(int, box)
            
            # Ensure coordinates are within image bounds
            h, w = original_image.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # Crop the object
            cropped_image = original_image[y1:y2, x1:x2]
            
            if cropped_image.size == 0:
                logging.warning(f"Skipping empty crop for '{label}' at box [{x1},{y1},{x2},{y2}]")
                continue

            # Save the cropped image
            base_name = image_path.stem
            crop_filename = f"{base_name}_{label}_{i+1}_conf{confidence:.2f}.jpg"
            save_path = image_path.parent / crop_filename
            
            try:
                cv2.imwrite(str(save_path), cropped_image)
                logging.info(f"Saved cropped object to: {save_path}")
            except Exception as e:
                logging.error(f"Failed to save cropped image {save_path}: {e}")

    def process_directory(self, dir_path: Path, crop: bool = False):
        """
        Processes all images in a directory, optionally cropping detected objects.

        Args:
            dir_path (Path): The path to the directory of images.
            crop (bool): If True, crop and save detected objects.
        """
        if not dir_path.is_dir():
            logging.error(f"Directory not found: {dir_path}")
            return

        image_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}
        image_files = [p for p in dir_path.iterdir() if p.suffix.lower() in image_extensions]

        logging.info(f"Found {len(image_files)} image files in '{dir_path}'.")
        
        detection_count = 0
        for image_path in image_files:
            detected_objects = self.detect_objects(image_path)
            if detected_objects:
                detection_count += 1
                if crop:
                    self.save_cropped_objects(image_path, detected_objects)
        
        logging.info(
            f"\n--- Processing Summary ---\n"
            f"Target Objects: {self.target_objects or 'All'}\n"
            f"Found targets in {detection_count} out of {len(image_files)} images.\n"
            f"--------------------------"
        )


def main():
    """Main function to parse arguments and run the detector."""
    parser = argparse.ArgumentParser(
        description="Detect objects in images using a YOLO model.",
        epilog="Example: python event_detector.py --image my_image.jpg --category people --crop"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single image file.")
    group.add_argument("--dir", type=Path, help="Path to a directory of images.")
    group.add_argument("--list-classes", action="store_true", help="List all detectable object classes and exit.")
    group.add_argument("--list-categories", action="store_true", help="List all predefined detection categories and exit.")

    detection_group = parser.add_mutually_exclusive_group()
    detection_group.add_argument("--category", help="Use a predefined category of objects to detect.")
    detection_group.add_argument("--objects", help="Provide a comma-separated list of custom objects to detect.")

    parser.add_argument("--crop", action="store_true", help="Crop and save detected objects.")
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging.")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    detector = EventDetector()

    if args.list_classes:
        print("Available classes:")
        for cls in detector.get_available_classes():
            print(f"  - {cls}")
        return

    if args.list_categories:
        print("Available categories:")
        for cat, items in DETECTION_CATEGORIES.items():
            print(f"  - {cat}: {items}")
        return
    
    # Configure detector based on arguments
    if args.category:
        detector.set_detection_category(args.category)
    elif args.objects:
        custom_objects = [obj.strip() for obj in args.objects.split(',')]
        detector.set_custom_objects(custom_objects)

    # Run processing
    if args.dir:
        detector.process_directory(args.dir, crop=args.crop)
    elif args.image:
        detected_objects = detector.detect_objects(args.image)
        if args.crop and detected_objects:
            detector.save_cropped_objects(args.image, detected_objects)

if __name__ == "__main__":
    main()