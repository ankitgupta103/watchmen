import os
import glob
from detect_enhanced import Detector

class ImageProcessor:
    def __init__(self, image_directory="/home/pi/Documents/images"):
        self.detector = Detector()
        self.detector.set_detection_category("all")
        self.image_directory = image_directory
        
    def get_image_files(self):
        """Get all image files from the specified directory"""
        image_extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff', '*.tif',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.GIF', '*.TIFF', '*.TIF'
        ]
        image_files = []
        
        if not os.path.exists(self.image_directory):
            print(f"Warning: Image directory {self.image_directory} does not exist")
            return []
        
        print(f"Scanning for images in: {self.image_directory}")
        
        for extension in image_extensions:
            pattern = os.path.join(self.image_directory, extension)  # Direct files in directory
            found_files = glob.glob(pattern)
            if found_files:
                print(f"   Found {len(found_files)} {extension} files")
            image_files.extend(found_files)
            
            # Also check subdirectories
            pattern_recursive = os.path.join(self.image_directory, '**', extension)
            found_files_recursive = glob.glob(pattern_recursive, recursive=True)
            # Remove duplicates already found in direct search
            new_files = [f for f in found_files_recursive if f not in found_files]
            image_files.extend(new_files)
            
        # Remove duplicates and sort
        image_files = sorted(list(set(image_files)))
        print(f"Total image files found: {len(image_files)}")
        
        return image_files

    def process_image_with_detector(self, image_path):
        """
        Process image with enhanced detector and return results
        
        Returns:
            dict: Detection results with has_detection, cropped_files, original_file
        """
        try:
            print(f"Processing image with AI detector: {os.path.basename(image_path)}")
            
            # Run detection
            has_objects = self.detector.ImageHasTargetObjects(image_path, crop_objects=True)
            
            if has_objects:
                # Get cropped object files (they're saved in the same directory with modified names)
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                crop_pattern = f"{base_name}_*_cropped.jpg"
                crop_dir = os.path.dirname(image_path)
                cropped_files = glob.glob(os.path.join(crop_dir, crop_pattern))
                
                print(f"✅ Detection found! Generated {len(cropped_files)} cropped images")
                
                return {
                    "has_detection": True,
                    "cropped_files": cropped_files,
                    "original_file": image_path
                }
            else:
                print(f"❌ No objects detected in image")
                return {
                    "has_detection": False,
                    "cropped_files": [],
                    "original_file": image_path
                }
                
        except Exception as e:
            print(f"💥 Error processing image {image_path}: {e}")
            return {
                "has_detection": False,
                "cropped_files": [],
                "original_file": image_path,
                "error": str(e)
            }

    def extract_objects_from_cropped_files(self, cropped_files):
        """
        Extract detected objects and highest confidence from cropped files
        
        Returns:
            tuple: (detected_objects_list, max_confidence)
        """
        detected_objects = []
        max_confidence = 0.85
        
        for cropped_file in cropped_files:
            filename = os.path.basename(cropped_file)
            if "_cropped.jpg" in filename:
                parts = filename.replace("_cropped.jpg", "").split("_")
                if len(parts) >= 3:
                    obj_name = parts[-2]
                    if obj_name not in detected_objects:
                        detected_objects.append(obj_name)
                    try:
                        conf = float(parts[-1].replace("conf", ""))
                        max_confidence = max(max_confidence, conf)
                    except:
                        pass
                        
        return detected_objects, max_confidence

    def is_detector_healthy(self):
        """Check if AI detector is functioning properly"""
        try:
            return hasattr(self.detector, 'model') and self.detector.model is not None
        except Exception:
            return False