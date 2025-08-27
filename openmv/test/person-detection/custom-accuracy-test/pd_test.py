# Fixed Unified Evaluation Script for OpenMV RT1062
# This script evaluates a TFLite model on images from SD card folders
# Generates comprehensive metrics and CSV logs

import os
import ml
from ml.postprocessing import yolo_lc_postprocess
import image
import time
import gc

# --- SCRIPT MODE ---
# Step 1: Set RUN_MODE to 1 and run the script. This will create file lists.
# Step 2: After Step 1 is done, set RUN_MODE to 2 and run the script again.
RUN_MODE = 2  # 1 = List Files, 2 = Evaluate Model

# --- CONFIGURATION ---
MODEL_PATH = "/rom/st_yolo_lc_v1_256_int8.tflite"  # Update with your model path
TARGET_LABEL = "person"
ALL_IMAGES_DIR = (
    "/sdcard/netrajaal/totalfiles"  # Folder with all images (positive + negative)
)
PERSON_ONLY_DIR = (
    "/sdcard/netrajaal/totalpeople"  # Folder with only person images (ground truth)
)
OUTPUT_DIR = "/sdcard/results"

# Model input size - check your model requirements
MODEL_INPUT_SIZE = 96  # Change to 128 if your model needs 128x128

# File paths for the generated lists
ALL_IMAGES_LIST = "/sdcard/all_images.txt"
PERSON_IMAGES_LIST = "/sdcard/person_images.txt"


# --- HELPER FUNCTIONS ---
def read_file_lines(filepath):
    """Read all lines from a file - compatible with MicroPython"""
    lines = []
    try:
        with open(filepath, "r") as f:
            # Read entire file at once if small enough
            content = f.read()
            lines = [line.strip() for line in content.split("\n") if line.strip()]
    except MemoryError:
        # If file too large, read line by line
        try:
            with open(filepath, "r") as f:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        lines.append(line)
        except Exception as e:
            print(f"Error reading file line by line: {e}")
    except Exception as e:
        print(f"Error reading file: {e}")

    return lines


def check_sd_card():
    """Check if SD card is properly mounted"""
    print("🔍 Checking SD card status...")
    try:
        sdcard_contents = os.listdir("/sdcard")
        print(f"  ✅ SD card accessible. Found {len(sdcard_contents)} items")
        return True
    except OSError as e:
        print(f"  ❌ SD card not accessible: {e}")
        return False


def verify_file_contents(filepath, max_lines=5):
    """Verify a file exists and show its first few lines"""
    print(f"\n📄 Verifying file: {filepath}")
    try:
        os.stat(filepath)
        print(f"  ✅ File exists")

        line_count = 0
        with open(filepath, "r") as f:
            print(f"  First {max_lines} lines:")
            while line_count < max_lines:
                line = f.readline()
                if not line:
                    break
                print(
                    f"    Line {line_count+1}: {line.strip()[:50]}..."
                )  # Show first 50 chars
                line_count += 1

        # Count total lines
        total = 0
        with open(filepath, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    total += 1

        print(f"  Total lines in file: {total}")
        return True

    except OSError as e:
        print(f"  ❌ File error: {e}")
        return False


# --- MODE 1: FILE LISTING ---
def create_file_lists():
    """Create lists of image files from directories"""
    print("=" * 60)
    print("MODE 1: CREATING FILE LISTS")
    print("=" * 60)

    if not check_sd_card():
        print("❌ SD card not accessible. Please check SD card mounting.")
        return

    def list_images(directory_path, output_file):
        """List all image files in a directory"""
        print(f"\n📂 Scanning: {directory_path}")

        valid_extensions = (".jpg", ".jpeg", ".bmp", ".png")
        count = 0

        try:
            # Check directory exists
            try:
                os.stat(directory_path)
            except OSError:
                print(f"  ❌ Directory not found: {directory_path}")
                return 0

            # Open output file
            with open(output_file, "w") as f:
                # List files
                clean_path = directory_path.rstrip("/")

                try:
                    files = os.listdir(clean_path)
                    print(f"  Found {len(files)} entries")

                    for filename in files:
                        if filename.lower().endswith(valid_extensions):
                            full_path = clean_path + "/" + filename
                            f.write(full_path + "\n")
                            count += 1

                            if count % 50 == 0:
                                print(f"    Processed {count} images...")
                                gc.collect()

                except OSError as e:
                    print(f"  ❌ Error listing directory: {e}")
                    return 0

            print(f"  ✅ Found {count} images -> {output_file}")
            return count

        except OSError as e:
            print(f"  ❌ Failed to create output file: {e}")
            return 0

    # Create lists
    all_count = list_images(ALL_IMAGES_DIR, ALL_IMAGES_LIST)
    gc.collect()
    person_count = list_images(PERSON_ONLY_DIR, PERSON_IMAGES_LIST)

    print("\n" + "=" * 60)
    print(f"✅ File listing complete!")
    print(f"    Total images: {all_count}")
    print(f"    Person images: {person_count}")
    print(f"    Non-person images: {all_count - person_count}")
    print("\n⚠️  Now set RUN_MODE = 2 and run again for evaluation")
    print("=" * 60)


def evaluate_model():
    """Evaluate model on all images and calculate metrics"""
    print("=" * 60)
    print("MODE 2: MODEL EVALUATION")
    print("=" * 60)

    # Create output directory
    try:
        os.mkdir(OUTPUT_DIR)
    except OSError:
        pass  # Directory already exists

    # Load model
    print("\n🧠 Loading model...")
    try:
        model = ml.Model(MODEL_PATH)
        print(f"{model}")
        print(f"  ✅ Model loaded successfully")
        print(f"  Input size: {MODEL_INPUT_SIZE}x{MODEL_INPUT_SIZE}")
    except Exception as e:
        print(f"  ❌ Failed to load model: {e}")
        return

    # Load ground truth (person images)
    print("\n📋 Loading ground truth...")
    person_images = set()

    # Read person image paths
    person_paths = read_file_lines(PERSON_IMAGES_LIST)
    if not person_paths:
        print(f"  ❌ Could not load person images from {PERSON_IMAGES_LIST}")
        print(f"  Please run with RUN_MODE=1 first!")
        return

    # --- CHANGE 1 of 2: Store only the FILENAME for ground truth ---
    # Instead of the full path, we store just the filename (e.g., "person1.jpg").
    for path in person_paths:
        img_filename = path.split('/')[-1]
        person_images.add(img_filename)
    # ----------------------------------------------------------------

    print(f"  ✅ Loaded {len(person_images)} person image names")
    if len(person_images) > 0:
        sample = list(person_images)[:3]
        print(f"  Sample names: {sample}")

    # Initialize metrics
    metrics = {
        "tp": 0,  # True Positives
        "fp": 0,  # False Positives
        "tn": 0,  # True Negatives
        "fn": 0,  # False Negatives
        "total": 0,
        "errors": 0,
    }

    # Process threshold
    confidence_threshold = 0.5

    # Load all image paths
    print("\n📂 Loading all image paths...")
    all_image_paths = read_file_lines(ALL_IMAGES_LIST)
    if not all_image_paths:
        print(f"  ❌ Could not load image paths from {ALL_IMAGES_LIST}")
        print(f"  Please run with RUN_MODE=1 first!")
        return

    print(f"  ✅ Found {len(all_image_paths)} images to process")

    csv_path = f"{OUTPUT_DIR}/evaluation_results.csv"
    try:
        with open(csv_path, "w") as f:
            f.write("filename,ground_truth,confidence_score,predicted,result\n")
    except OSError as e:
        print(f"  ❌ Could not create CSV file: {e}")
        return

    # Process each image
    print(f"\n🔄 Processing images (threshold={confidence_threshold})...")
    print("-" * 50)

    start_time = time.ticks_ms()
    processed = 0
    total_images = len(all_image_paths)

    for img_path in all_image_paths:
        if not img_path:
            continue

        # --- CHANGE 2 of 2: Check using the FILENAME ---
        # We extract the filename from the current path and check against our set.
        img_filename = img_path.split('/')[-1]
        is_person_image = img_filename in person_images
        # ------------------------------------------------

        processed += 1

        # Debug first few images
        if processed <= 3:
            print(f"  Processing: {img_filename} (Person: {is_person_image})")

        # Process image
        score = process_single_image(model, img_path, MODEL_INPUT_SIZE)

        current_result = {}
        if score is None:
            metrics["errors"] += 1
            current_result = {
                "filename": img_filename,
                "ground_truth": is_person_image,
                "score": 0.0,
                "predicted": False,
                "status": "ERROR",
            }
        else:
            predicted_person = score >= confidence_threshold
            metrics["total"] += 1
            status = "UNKNOWN"
            if is_person_image and predicted_person:
                metrics["tp"] += 1
                status = "TP"
            elif not is_person_image and predicted_person:
                metrics["fp"] += 1
                status = "FP"
            elif is_person_image and not predicted_person:
                metrics["fn"] += 1
                status = "FN"
            else:
                metrics["tn"] += 1
                status = "TN"

            current_result = {
                "filename": img_filename,
                "ground_truth": is_person_image,
                "score": score,
                "predicted": predicted_person,
                "status": status,
            }

        # Append the new data to the CSV file
        try:
            with open(csv_path, "a") as f:
                r = current_result
                gt = "person" if r["ground_truth"] else "no_person"
                pred = "person" if r["predicted"] else "no_person"
                # Log the clean filename instead of the full path
                f.write(f"{r['filename']},{gt},{r['score']:.4f},{pred},{r['status']}\n")
        except OSError as e:
            print(f"  ❌ Error writing to CSV: {e}")

        # Progress update
        if processed % 20 == 0 or processed == total_images:
            elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000
            print(
                f"  Processed: {processed}/{total_images} | Time: {elapsed:.1f}s | "
                f"TP:{metrics['tp']} FP:{metrics['fp']} "
                f"TN:{metrics['tn']} FN:{metrics['fn']}"
            )
            gc.collect()

    # Calculate final metrics
    total_time = time.ticks_diff(time.ticks_ms(), start_time) / 1000

    print("\n" + "=" * 60)
    print("📊 EVALUATION RESULTS")
    print("=" * 60)

    # Basic counts
    print("\n📈 Detection Summary:")
    print(f"  Total images processed: {processed}")
    print(f"  Successful evaluations: {metrics['total']}")
    print(f"  Processing errors: {metrics['errors']}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Average time per image: {total_time/max(processed,1):.3f}s")

    # Confusion Matrix
    print(f"\n📋 Confusion Matrix:")
    print(f"  {'':12} {'Predicted':^20}")
    print(f"  {'Actual':12} {'Person':>10} {'No Person':>10}")
    print(f"  {'Person':12} {metrics['tp']:>10} {metrics['fn']:>10}")
    print(f"  {'No Person':12} {metrics['fp']:>10} {metrics['tn']:>10}")

    # Calculate performance metrics
    if metrics["total"] > 0:
        accuracy = (metrics["tp"] + metrics["tn"]) / metrics["total"]

        if metrics["tp"] + metrics["fp"] > 0:
            precision = metrics["tp"] / (metrics["tp"] + metrics["fp"])
        else:
            precision = 0.0

        if metrics["tp"] + metrics["fn"] > 0:
            recall = metrics["tp"] / (metrics["tp"] + metrics["fn"])
        else:
            recall = 0.0

        if precision + recall > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0

        if metrics["tn"] + metrics["fp"] > 0:
            specificity = metrics["tn"] / (metrics["tn"] + metrics["fp"])
        else:
            specificity = 0.0

        print(f"\n🎯 Performance Metrics:")
        print(
            f"  Accuracy:    {accuracy:.3f} ({metrics['tp']+metrics['tn']}/{metrics['total']})"
        )
        print(f"  Precision:   {precision:.3f} (TP/(TP+FP))")
        print(f"  Recall:      {recall:.3f} (TP/(TP+FN))")
        print(f"  Specificity: {specificity:.3f} (TN/(TN+FP))")
        print(f"  F1-Score:    {f1_score:.3f}")
    save_results_csv(metrics, total_time, processed)

    print("\n" + "=" * 60)
    print("✅ EVALUATION COMPLETE!")
    print(f"📁 Results saved to: {OUTPUT_DIR}")
    print("=" * 60)


# def process_single_image(model, img_path, target_size):
#     """
#     Process a single image and return confidence score.
#     Returns None if processing fails.
#     """
#     try:
#         # --- FIX: RESIZING LOGIC ---
#         # Reverted to using the correct 'scale' and 'crop' methods to fix the error.
#         img = image.Image(img_path, copy_to_fb=False)

#         # Get original dimensions
#         w = img.width()
#         h = img.height()

#         # Determine scale factor to fit the image inside the target square, maintaining aspect ratio
#         if w > h:
#             scale_factor = target_size / h
#         else:
#             scale_factor = target_size / w

#         # The scale() method returns a new, scaled image object.
#         img = img.scale(x_scale=scale_factor, y_scale=scale_factor, hint=image.BICUBIC)

#         # Perform a center crop to get the final square image
#         x_offset = (img.width() - target_size) // 2
#         y_offset = (img.height() - target_size) // 2
#         img = img.crop(roi=(x_offset, y_offset, target_size, target_size))

#         # --- CORRECT INFERENCE LOGIC (from previous fix) ---
#         # Run inference to get the raw prediction tensor
#         prediction_tensor = model.predict([img])
#         del img
#         gc.collect()

#         # Parse the raw tensor to find the confidence score for "person"
#         scores = zip(model.labels, prediction_tensor[0].flatten().tolist())
#         person_confidence = 0.0
#         for label, confidence in scores:
#             if label == TARGET_LABEL:
#                 person_confidence = confidence
#                 break # Exit loop once the "person" score is found

#         return person_confidence

#     except Exception as e:
#         print(f"  ❌ Failed processing {img_path}: {e}")
#         gc.collect()
#         return None

def process_single_image(model, img_path, target_size):
    """
    Process a single image with YOLO model and return confidence score.
    Returns None if processing fails.
    """
    try:
        # Import YOLO postprocessing function
        from ml.postprocessing import yolo_lc_postprocess

        # Load and preprocess image (same as before)
        img = image.Image(img_path, copy_to_fb=False)

        # Get original dimensions
        w = img.width()
        h = img.height()

        # Determine scale factor to fit the image inside the target square, maintaining aspect ratio
        if w > h:
            scale_factor = target_size / h
        else:
            scale_factor = target_size / w

        # The scale() method returns a new, scaled image object.
        img = img.scale(x_scale=scale_factor, y_scale=scale_factor, hint=image.BICUBIC)

        # Perform a center crop to get the final square image
        x_offset = (img.width() - target_size) // 2
        y_offset = (img.height() - target_size) // 2
        img = img.crop(roi=(x_offset, y_offset, target_size, target_size))

        # --- CORRECTED YOLO INFERENCE LOGIC ---
        # Use YOLO postprocessing with a low threshold to get all detections
        boxes = model.predict([img], callback=yolo_lc_postprocess(threshold=0.1))
        del img
        gc.collect()

        # boxes is a list of lists per class
        # For "person" class (index 0), get the highest confidence detection
        person_confidence = 0.0

        if len(boxes) > 0 and len(boxes[0]) > 0:
            # boxes[0] contains detections for "person" class
            # Each detection is ((x, y, w, h), score)
            person_detections = boxes[0]

            if person_detections:
                # Find the detection with highest confidence
                max_score = 0.0
                for detection in person_detections:
                    bbox, score = detection  # Unpack (x,y,w,h) and score
                    if score > max_score:
                        max_score = score

                person_confidence = max_score

        return person_confidence

    except Exception as e:
        print(f"  ❌ Failed processing {img_path}: {e}")
        gc.collect()
        return None

# --- MODIFICATION --- This function now only saves the summary text file.
def save_results_csv(metrics, total_time, total_processed):
    """Save summary metrics to a text file."""
    # The detailed CSV is now saved incrementally, so that part is removed from this function.

    # Save summary metrics
    summary_path = f"{OUTPUT_DIR}/evaluation_summary.txt"
    try:
        with open(summary_path, "w") as f:
            f.write("MODEL EVALUATION SUMMARY\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Model: {MODEL_PATH}\n")
            f.write(f"Total Images: {total_processed}\n")
            f.write(f"Processing Time: {total_time:.1f}s\n\n")

            f.write("CONFUSION MATRIX:\n")
            f.write(f"  True Positives:  {metrics['tp']}\n")
            f.write(f"  False Positives: {metrics['fp']}\n")
            f.write(f"  True Negatives:  {metrics['tn']}\n")
            f.write(f"  False Negatives: {metrics['fn']}\n\n")

            if metrics["total"] > 0:
                acc = (metrics["tp"] + metrics["tn"]) / metrics["total"]
                prec = metrics["tp"] / max(metrics["tp"] + metrics["fp"], 1)
                rec = metrics["tp"] / max(metrics["tp"] + metrics["fn"], 1)
                f1 = 2 * prec * rec / max(prec + rec, 0.001)

                f.write("PERFORMANCE METRICS:\n")
                f.write(f"  Accuracy:    {acc:.3f}\n")
                f.write(f"  Precision:   {prec:.3f}\n")
                f.write(f"  Recall:      {rec:.3f}\n")
                f.write(f"  F1-Score:    {f1:.3f}\n")

        print(f"\n💾 Saved summary to {summary_path}")

    except OSError as e:
        print(f"  ❌ Failed to save summary: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("OPENMV RT1062 MODEL EVALUATION SYSTEM")
    print("🚀" * 30 + "\n")

    if RUN_MODE == 1:
        create_file_lists()
    elif RUN_MODE == 2:
        # Verify files exist before running evaluation
        print("🔍 Verifying required files...")

        if verify_file_contents(ALL_IMAGES_LIST, 3):
            print("  ✅ All images list verified")
        else:
            print("  ❌ All images list not found or empty!")
            print("  Please run with RUN_MODE=1 first")

        if verify_file_contents(PERSON_IMAGES_LIST, 3):
            print("  ✅ Person images list verified")
        else:
            print("  ❌ Person images list not found or empty!")
            print("  Please run with RUN_MODE=1 first")

        # Run evaluation
        evaluate_model()
    else:
        print("❌ Invalid RUN_MODE. Please set to 1 or 2.")
