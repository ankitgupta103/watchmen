import sensor
import ml
import time
import gc

print("🚀 Initializing Optimized Person Detection System...")

# ===========================
# MEMORY & MODEL SETUP
# ===========================
print("📝 Step 1: Clearing memory and loading model...")
gc.collect()

# Model configuration
MODEL_PATH = "/sdcard/yolov8n_full_integer_quant.tflite"  # UPDATE THIS PATH
PERSON_CLASS_ID = 0  # COCO dataset: person = class 0
CONFIDENCE_THRESHOLD = 0.6  # Higher threshold for reliable person detection

try:
    # Clear any existing model
    try:
        del model
    except:
        pass
    gc.collect()

    # Load YOLOv8n model
    model = ml.Model(MODEL_PATH, load_to_fb=True)
    print(f"✅ Model loaded: {model.input_shape} -> {model.output_shape}")

    # Verify 128x128 input
    if model.input_shape[0][1] != 128:
        print(
            f"⚠️  Warning: Expected 128x128, got {model.input_shape[0][1]}x{model.input_shape[0][1]}"
        )

    # Check if model expects RGB (3 channels) with greyscale input (1 channel)
    if len(model.input_shape[0]) >= 4 and model.input_shape[0][3] == 3:
        print("ℹ️  Model expects RGB input - OpenMV will auto-convert greyscale")

except Exception as e:
    print(f"❌ Model loading failed: {e}")
    exit()

# ===========================
# CAMERA OPTIMIZATION
# ===========================
print("📷 Step 2: Optimizing camera for clear greyscale images...")

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)  # Greyscale for consistency and efficiency

# Use VGA for better field of view - model will resize to 128x128 internally
sensor.set_framesize(sensor.VGA)  # 640x480 for good field of view
print("📐 Camera: VGA (640x480) Greyscale -> Model resizes to 128x128")

# Camera stability settings
sensor.skip_frames(time=3000)  # Longer stabilization time

# Manual settings for consistent greyscale images
sensor.set_auto_gain(False)  # Disable auto gain for consistency
sensor.set_auto_whitebal(False)  # Disable auto white balance
sensor.set_auto_exposure(False)  # Disable auto exposure

# Manual settings for optimal greyscale clarity
# sensor.set_brightness(0)           # Neutral brightness (-3 to +3)
# sensor.set_contrast(2)             # Higher contrast for better edge detection (0 to +3)
# sensor.set_saturation(0)           # Not relevant for greyscale

# You can fine-tune these manual values:
# sensor.set_brightness(-1)        # Darker for bright environments
# sensor.set_contrast(3)           # Maximum contrast for better edges
# sensor.set_saturation(0)         # Always 0 for greyscale

print("✅ Camera optimized: Manual settings, Greyscale, VGA resolution")
print("💡 Tip: Adjust brightness/contrast manually for your lighting conditions")


# ===========================
# OPTIMIZED PERSON DETECTION
# ===========================
def detect_person_only(img):
    """Streamlined person-only detection"""

    # Step 1: Run inference
    start_time = time.ticks_ms()
    prediction = model.predict([img])
    inference_time = time.ticks_diff(time.ticks_ms(), start_time)

    # Step 2: Parse output for person class only
    output = prediction[0]

    max_person_confidence = 0.0
    person_detections = []
    boxes_processed = 0

    try:
        # Handle different output formats efficiently
        if len(output.shape) == 3:
            if output.shape[1] > output.shape[2]:
                # Format: (1, detections, features)
                num_detections = output.shape[1]
                for i in range(min(num_detections, 300)):  # Process up to 300 boxes
                    detection = output[0, i, :]
                    person_conf = extract_person_confidence(detection)
                    boxes_processed += 1

                    if person_conf > max_person_confidence:
                        max_person_confidence = person_conf

                    if person_conf > CONFIDENCE_THRESHOLD:
                        person_detections.append(person_conf)
            else:
                # Format: (1, features, detections)
                num_detections = output.shape[2]
                for i in range(min(num_detections, 300)):
                    detection = output[0, :, i]
                    person_conf = extract_person_confidence(detection)
                    boxes_processed += 1

                    if person_conf > max_person_confidence:
                        max_person_confidence = person_conf

                    if person_conf > CONFIDENCE_THRESHOLD:
                        person_detections.append(person_conf)

        elif len(output.shape) == 2:
            # Format: (detections, features)
            num_detections = output.shape[0]
            for i in range(min(num_detections, 300)):
                detection = output[i, :]
                person_conf = extract_person_confidence(detection)
                boxes_processed += 1

                if person_conf > max_person_confidence:
                    max_person_confidence = person_conf

                if person_conf > CONFIDENCE_THRESHOLD:
                    person_detections.append(person_conf)

    except Exception as e:
        print(f"⚠️  Detection parsing error: {e}")
        return False, 0.0, inference_time, 0

    person_detected = len(person_detections) > 0
    return person_detected, max_person_confidence, inference_time, boxes_processed


def extract_person_confidence(detection):
    """Extract person class confidence from detection"""
    try:
        if len(detection) >= 84:
            # Full YOLO format: [x, y, w, h] + 80 class scores
            person_score = detection[4 + PERSON_CLASS_ID]  # Person is class 0
        elif len(detection) >= 5:
            # Simplified format: [x, y, w, h, person_score]
            person_score = detection[4]
        else:
            return 0.0

        # Apply sigmoid activation
        person_conf = 1.0 / (1.0 + 2.718281828 ** (-person_score))
        return person_conf

    except:
        return 0.0


# ===========================
# OPTIMIZED DETECTION LOOP
# ===========================
def run_optimized_person_detection():
    """Clean, optimized detection workflow"""

    print("\n🎯 Starting Optimized Person Detection")
    print("📋 Workflow: Clear Memory -> Capture -> Process -> Results -> Repeat")
    print("🎛️  Settings: VGA Greyscale, Manual camera, 128x128 processing")
    print("=" * 70)

    capture_count = 0

    while True:
        try:
            capture_count += 1

            # ===== STEP 1: CLEAR MEMORY =====
            print(f"\n🔄 CYCLE #{capture_count}")
            print("🧹 Clearing memory...")
            gc.collect()

            # ===== STEP 2: CAPTURE CLEAR IMAGE =====
            print("📸 Capturing clear image...")

            # Take multiple frames to ensure freshness and focus
            for _ in range(4):  # More frames for better quality
                temp_img = sensor.snapshot()
                del temp_img
                time.sleep_ms(100)  # Allow sensor to adjust

            # Final capture for processing
            img = sensor.snapshot()
            print(f"✅ Image captured: {img.width()}x{img.height()}")

            # Quick image quality check (greyscale)
            center_pixel = img.get_pixel(img.width() // 2, img.height() // 2)
            brightness = center_pixel  # Greyscale pixel is single value
            print(f"📊 Image brightness: {brightness} (0-255)")

            # ===== STEP 3: PROCESS FOR PERSON =====
            print("🤖 Processing for person detection...")

            person_detected, max_confidence, inference_time, boxes_processed = (
                detect_person_only(img)
            )

            # ===== STEP 4: PRINT RESULTS =====
            print("📋 DETECTION RESULTS:")
            print(f"   ⏱️  Inference time: {inference_time}ms")
            print(f"   📦 Boxes processed: {boxes_processed}")
            print(f"   🎯 Max confidence: {max_confidence:.3f}")

            if person_detected:
                print(f"   🟢 PERSON DETECTED! (Confidence: {max_confidence:.3f})")

                # Optional: Save greyscale image when person detected
                # img_path = f"/sdcard/person_{capture_count}_{max_confidence:.2f}.jpg"
                # img.save(img_path)
                # print(f"   💾 Saved: {img_path}")

            else:
                print(f"   🔴 No person detected")

            # ===== STEP 5: CLEANUP =====
            del img
            gc.collect()

            # Wait before next cycle (can adjust this)
            print("⏳ Waiting 4 seconds before next detection...")
            for i in range(4, 0, -1):
                print(f"   Next in {i}s...")
                time.sleep(1)

        except Exception as cycle_error:
            print(f"❌ Cycle error: {cycle_error}")
            print("🔧 Recovering...")

            # Emergency cleanup
            try:
                del img
            except:
                pass
            gc.collect()
            time.sleep(3)

        except KeyboardInterrupt:
            print("\n🛑 Detection stopped by user")
            break


# ===========================
# SYSTEM STATUS & START
# ===========================
def print_system_status():
    """Display system configuration"""
    print("\n📊 SYSTEM STATUS:")
    print(f"   🎯 Target: Person detection only (COCO class {PERSON_CLASS_ID})")
    print(f"   🎥 Camera: VGA (640x480) Greyscale, Manual settings")
    print(f"   🤖 Model: 128x128 input YOLOv8n")
    print(f"   🎛️  Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"   💾 Memory: Aggressive cleanup between cycles")
    print(f"   🖼️  Focus: Consistent greyscale images, Manual control")


print_system_status()

# Start the optimized detection system
if __name__ == "__main__":
    try:
        run_optimized_person_detection()
    except Exception as main_error:
        print(f"❌ System error: {main_error}")
    finally:
        print("🧹 Final cleanup...")
        gc.collect()
        print("✅ System shutdown complete")
