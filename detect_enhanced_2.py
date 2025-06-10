import sys
import os
import cv2
import numpy as np
from ultralytics import YOLO
import argparse

# The name of the YOLO model to use.
YOLOMODELNAME = "yolov8n.pt"

# Predefined detection categories for convenience.
DETECTION_CATEGORIES = {
    "people": ["person"],
    "suspicious_items": ["backpack", "handbag", "suitcase", "knife", "scissors", "bottle"],
    "bags": ["backpack", "handbag", "suitcase"],
    "potential_weapons": ["knife", "scissors", "baseball bat"],
    "vehicles": ["car", "motorcycle", "bicycle", "bus", "truck"],
    "electronics": ["laptop", "cell phone"],
    "all": [] 
}

class Detector:
    def __init__(self, model_name=YOLOMODELNAME):
        self.model = YOLO(model_name)
        self.target_objects = {"person"} # Default target
        print("YOLO model loaded successfully.")
        self.model.info()

    def set_detection_targets(self, category=None, custom_objects=None):
        if category:
            if category in DETECTION_CATEGORIES:
                self.target_objects = set(DETECTION_CATEGORIES[category])
                print(f"Detection category set to '{category}': {self.target_objects}")
            else:
                print(f"Warning: Unknown category '{category}'. Using default.")
        elif custom_objects:
            self.target_objects = set(custom_objects)
            print(f"Detection set to custom objects: {self.target_objects}")

    def get_available_classes(self):
        """Returns a list of all class names the model can detect."""
        return list(self.model.names.values())

    def detect(self, image_path):
        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"Error: Could not read image at {image_path}")
            return None

        annotated_image = original_image.copy()
        
        resized_image = cv2.resize(original_image, (640, 640))
        
        results = self.model(resized_image)

        detected_items = []
        original_height, original_width = original_image.shape[:2]
        scale_x = original_width / 640
        scale_y = original_height / 640

        for r in results:
            for i, box in enumerate(r.boxes):
                object_name = self.model.names[int(box.cls)]
                
                if not self.target_objects or object_name in self.target_objects:
                    confidence = float(box.conf)
                    
                    # Get bounding box and scale it to original image size
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1_orig = int(xyxy[0] * scale_x)
                    y1_orig = int(xyxy[1] * scale_y)
                    x2_orig = int(xyxy[2] * scale_x)
                    y2_orig = int(xyxy[3] * scale_y)

                    # Ensure coordinates are within image bounds
                    x1_orig = max(0, x1_orig)
                    y1_orig = max(0, y1_orig)
                    x2_orig = min(original_width, x2_orig)
                    y2_orig = min(original_height, y2_orig)

                    cropped_object_img = original_image[y1_orig:y2_orig, x1_orig:x2_orig]
                    
                    label = f"{object_name} {confidence:.2f}"
                    cv2.rectangle(annotated_image, (x1_orig, y1_orig), (x2_orig, y2_orig), (0, 255, 0), 2)
                    cv2.putText(annotated_image, label, (x1_orig, y1_orig - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                    detected_items.append({
                        'label': object_name,
                        'confidence': confidence,
                        'box': [x1_orig, y1_orig, x2_orig, y2_orig],
                        'cropped_image': cropped_object_img
                    })
        
        print(f"Found {len(detected_items)} target objects in {os.path.basename(image_path)}.")
        return {
            'annotated_image': annotated_image,
            'detections': detected_items
        }

def process_directory(detector, dir_path, save_crops=False, output_dir="output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    for filename in os.listdir(dir_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            image_path = os.path.join(dir_path, filename)
            process_single_image(detector, image_path, save_crops, output_dir)

def process_single_image(detector, image_path, save_crops=False, output_dir="output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    results = detector.detect(image_path)

    if results and results['detections']:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Save the annotated image
        annotated_filename = os.path.join(output_dir, f"{base_name}_annotated.jpg")
        cv2.imwrite(annotated_filename, results['annotated_image'])
        print(f"Saved annotated image to: {annotated_filename}")

        # Save cropped images if requested
        if save_crops:
            for i, detection in enumerate(results['detections']):
                crop_filename = os.path.join(
                    output_dir,
                    f"{base_name}_{detection['label']}_{i+1}_conf{detection['confidence']:.2f}.jpg"
                )
                cv2.imwrite(crop_filename, detection['cropped_image'])
                print(f"  - Saved cropped object to: {crop_filename}")

def main():
    parser = argparse.ArgumentParser(description="Object detection using YOLOv8.")
    parser.add_argument("path", nargs='?', help="Path to a single image or a directory of images.")
    parser.add_argument("--crop", action="store_true", help="Save cropped images of detected objects.")
    parser.add_argument("--category", help=f"Use a predefined detection category. Choices: {list(DETECTION_CATEGORIES.keys())}")
    parser.add_argument("--objects", help="Detect a custom comma-separated list of objects (e.g., 'person,car').")
    parser.add_argument("--output-dir", default="output", help="Directory to save output files.")
    parser.add_argument("--list-classes", action="store_true", help="List all detectable object classes and exit.")
    
    args = parser.parse_args()
    
    detector = Detector()

    if args.list_classes:
        print("Available classes for detection:")
        for cls in sorted(detector.get_available_classes()):
            print(f"  - {cls}")
        return

    if not args.path:
        parser.error("The 'path' argument (image or directory) is required.")

    custom_objects = args.objects.split(',') if args.objects else None
    detector.set_detection_targets(category=args.category, custom_objects=custom_objects)
    
    if os.path.isdir(args.path):
        print(f"\nProcessing directory: {args.path}")
        process_directory(detector, args.path, args.crop, args.output_dir)
    elif os.path.isfile(args.path):
        print(f"\nProcessing image: {args.path}")
        process_single_image(detector, args.path, args.crop, args.output_dir)
    else:
        print(f"Error: Path not found at '{args.path}'")

if __name__ == "__main__":
    main()