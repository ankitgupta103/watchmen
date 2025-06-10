import sys
import os
import cv2
from ultralytics import YOLO

YOLOMODELNAME = "yolov8n.pt"

# Predefined detection categories
DETECTION_CATEGORIES = {
    "people": ["person"],
    "suspicious_items": ["backpack", "handbag", "suitcase", "knife", "scissors", "bottle"],
    "bags": ["backpack", "handbag", "suitcase"],
    "potential_weapons": ["knife", "scissors", "baseball bat", "gun"],
    "vehicles": ["car", "motorcycle", "bicycle", "bus", "truck"],
    "electronics": ["laptop", "cell phone"],
    "all": [] 
}

def has_target_objects_and_get_boxes(results, target_objects):
    """Return True if target objects found and list of their bounding boxes with labels"""
    detected_boxes = []
    for r in results:
        x = r.summary()
        print(f"Box xyxy = {r.boxes.xyxy}")
        for i, o in enumerate(x):
            object_name = o['name']
            print(f"detected object = {object_name}")
            
            # Check if this object is in our target list
            if not target_objects or object_name in target_objects:
                # Get the bounding box coordinates (xyxy format)
                box = r.boxes.xyxy[i].cpu().numpy()  # Convert to numpy array
                confidence = o.get('confidence', 0.0)
                detected_boxes.append({
                    'box': box, 
                    'label': object_name, 
                    'confidence': confidence
                })
    return len(detected_boxes) > 0, detected_boxes

def is_image_file(file_path):
    return file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))

class Detector:
    def __init__(self):
        self.modelname = YOLOMODELNAME
        self.model = YOLO(self.modelname)
        self.model.info()
        self.debug_mode = False
        self.target_objects = ["person"]  # Default to person detection

    def set_debug_mode(self):
        self.debug_mode = True

    def set_detection_category(self, category):
        """Set detection category using predefined categories"""
        if category in DETECTION_CATEGORIES:
            self.target_objects = DETECTION_CATEGORIES[category]
            print(f"Detection set to category '{category}': {self.target_objects}")
        else:
            print(f"Unknown category '{category}'. Available categories: {list(DETECTION_CATEGORIES.keys())}")

    def set_custom_objects(self, objects):
        """Set custom list of objects to detect"""
        self.target_objects = objects
        print(f"Detection set to custom objects: {self.target_objects}")

    def get_available_classes(self):
        """Get all classes that the YOLO model can detect"""
        return list(self.model.names.values())

    def ImageHasTargetObjects(self, fname, crop_objects=False):
        fpath = fname
        # Read original image (don't resize yet for better crop quality)
        original_image = cv2.imread(fpath)
        if original_image is None:
            print(f"Error: Could not read image {fname}")
            return False
            
        original_height, original_width = original_image.shape[:2]
        
        # Resize for detection
        resized_image = cv2.resize(original_image, (640, 640))
        results = self.model(resized_image)
        
        has_objects, detected_objects = has_target_objects_and_get_boxes(results, self.target_objects)
        
        if has_objects:
            print(f"Target objects found in image {fname}")
            print(f"Detected: {[obj['label'] for obj in detected_objects]}")
            
            if crop_objects:
                # Calculate scale factors to map coordinates back to original image
                scale_x = original_width / 640
                scale_y = original_height / 640
                
                for i, obj_data in enumerate(detected_objects):
                    box = obj_data['box']
                    label = obj_data['label']
                    confidence = obj_data['confidence']
                    
                    # Scale coordinates back to original image size
                    x1, y1, x2, y2 = box
                    x1_orig = int(x1 * scale_x)
                    y1_orig = int(y1 * scale_y)
                    x2_orig = int(x2 * scale_x)
                    y2_orig = int(y2 * scale_y)
                    
                    # Ensure coordinates are within image bounds
                    x1_orig = max(0, x1_orig)
                    y1_orig = max(0, y1_orig)
                    x2_orig = min(original_width, x2_orig)
                    y2_orig = min(original_height, y2_orig)
                    
                    # Crop the object from original image
                    cropped_object = original_image[y1_orig:y2_orig, x1_orig:x2_orig]
                    
                    # Save cropped image
                    base_name = os.path.splitext(os.path.basename(fname))[0]
                    crop_filename = f"{base_name}_{label}_{i+1}_conf{confidence:.2f}_cropped.jpg"
                    cv2.imwrite(crop_filename, cropped_object)
                    print(f"Cropped {label} {i+1} saved as: {crop_filename}")
                    print(f"Crop coordinates: ({x1_orig}, {y1_orig}) to ({x2_orig}, {y2_orig})")
                    print(f"Confidence: {confidence:.2f}")
            
            if self.debug_mode:
                for r in results:
                    r.show()
        else:
            print(f"No target objects found in image {fname}")
        
        return has_objects

    def crop_all_objects_from_image(self, fname):
        """Dedicated method to crop all detected target objects from an image"""
        return self.ImageHasTargetObjects(fname, crop_objects=True)

def eval_dir(detector, dname, crop_objects=False):
    filenames = os.listdir(dname)
    image_files = []
    for f in filenames:
        fpath = os.path.join(dname, f)
        if os.path.isfile(fpath) and is_image_file(fpath):
            image_files.append(fpath)
        else:
            print("Not an image file : " + fpath)
    
    print(f"Found {len(image_files)} image files.")
    detected_images = []
    
    for imf in image_files:
        has_objects = detector.ImageHasTargetObjects(imf, crop_objects=crop_objects)
        if has_objects:
            detected_images.append(imf)
    
    print("\nSummary:")
    for f in detected_images:
        print(f"  {f}")
    print(f"Found target objects in {len(detected_images)} out of {len(image_files)} images.")

def print_usage():
    print("Usage: python detect.py <image_path> [options]")
    print("\nOptions:")
    print("  --crop                    Crop detected objects")
    print("  --category <name>         Use predefined category")
    print("  --objects <obj1,obj2>     Detect custom objects (comma-separated)")
    print("  --list-classes            Show all detectable classes")
    print("  --list-categories         Show predefined categories")
    print("  --dir <directory>         Process all images in directory")
    print("\nExamples:")
    print("  python detect.py image.jpg --category suspicious_items --crop")
    print("  python detect.py image.jpg --objects person,backpack,knife")
    print("  python detect.py --dir /path/to/images --category people")

def main():
    detector = Detector()
    
    if len(sys.argv) < 2:
        print_usage()
        return
    
    # Parse command line arguments
    args = sys.argv[1:]
    image_path = None
    directory_path = None
    crop_flag = False
    category = None
    custom_objects = None
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == "--crop":
            crop_flag = True
        elif arg == "--category" and i + 1 < len(args):
            category = args[i + 1]
            i += 1
        elif arg == "--objects" and i + 1 < len(args):
            custom_objects = args[i + 1].split(',')
            i += 1
        elif arg == "--dir" and i + 1 < len(args):
            directory_path = args[i + 1]
            i += 1
        elif arg == "--list-classes":
            print("Available classes:")
            classes = detector.get_available_classes()
            for cls in sorted(classes):
                print(f"  {cls}")
            return
        elif arg == "--list-categories":
            print("Available categories:")
            for cat, objects in DETECTION_CATEGORIES.items():
                print(f"  {cat}: {objects}")
            return
        elif not arg.startswith("--") and image_path is None:
            image_path = arg
        
        i += 1
    
    # Set detection targets
    if category:
        detector.set_detection_category(category)
    elif custom_objects:
        detector.set_custom_objects(custom_objects)
    
    # Enable debug mode
    detector.set_debug_mode()
    
    # Process images
    if directory_path:
        if crop_flag:
            print("Directory processing with cropping enabled")
        eval_dir(detector, directory_path, crop_objects=crop_flag)
    elif image_path:
        if crop_flag:
            print("Cropping mode enabled - will save cropped object images")
            detector.crop_all_objects_from_image(image_path)
        else:
            detector.ImageHasTargetObjects(image_path)
    else:
        print("Error: No image or directory specified")
        print_usage()

if __name__ == "__main__":
    main()