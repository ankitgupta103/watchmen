import sensor
import ml
import time
import random
import utime
import gc

# --- Enhanced Configuration ---
MODEL_PATH = "/rom/person_detect.tflite"
IMG_DIR = "/sdcard/images1/"
CONFIDENCE_THRESHOLD = 0.7  # Increased for sliding window to reduce false positives
SAVE_COOLDOWN = 5000  # milliseconds between saves
AUTOFOCUS_INTERVAL = 10  # frames between autofocus attempts
SAVE_ALL_IMAGES = False  # Set to True to save all images, False to save only detections
MAX_IMAGES_PER_SESSION = 1000  # Prevent storage overflow
SLIDING_WINDOW_STRIDE = 16  # How many pixels to jump for the next window. Smaller is more thorough but slower.

# --- Global Variables ---
clock = time.clock()
image_count = 0
detection_count = 0
last_save_time = 0
autofocus_counter = 0
session_start_time = time.ticks_ms()
model = None  # Will be initialized later
model_w, model_h = 0, 0  # Model dimensions


# --- Utility Functions ---
def get_rand(n):
    """Generate random alphanumeric string of length n"""
    rstr = ""
    for i in range(n):
        rstr += chr(65 + random.randint(0, 25))
    return rstr


def get_model_info():
    """Print detailed model information"""
    print("=" * 50)
    print("MODEL INFORMATION:")
    print("  Path:", MODEL_PATH)
    print("  Input shape:", model.input_shape)
    print("  Output shape:", model.output_shape)
    print("  Labels:", model.labels)
    print("=" * 50)


def print_session_stats():
    """Print session statistics"""
    elapsed_time = time.ticks_diff(time.ticks_ms(), session_start_time) / 1000
    detection_rate = (detection_count / image_count * 100) if image_count > 0 else 0

    print(f"\n--- SESSION STATS ---")
    print(f"Runtime: {elapsed_time:.1f}s")
    print(f"Images processed: {image_count}")
    print(f"Person detections: {detection_count}")
    print(f"Detection rate: {detection_rate:.1f}%")
    print(f"Avg FPS: {clock.fps():.2f}")
    print(f"Free memory: {gc.mem_free()} bytes")
    print("-" * 20)


def trigger_autofocus():
    """Attempt to trigger autofocus with error handling"""
    try:
        sensor.__write_reg(0x3022, 0x03)
        print("📷 Autofocus triggered")
        return True
    except Exception as e:
        print(f"⚠️ Autofocus failed: {e}")
        return False


def detect_person_with_sliding_window(img):
    """
    Detects a person using a sliding window to find the best bounding box.
    This replaces the simple classifier with a basic object detector.
    """
    global model_w, model_h
    start_time = time.ticks_ms()

    best_confidence = 0
    best_box = None
    person_detected = False

    # Loop over the image, creating small tiles to test
    for y in range(0, img.height() - model_h, SLIDING_WINDOW_STRIDE):
        for x in range(0, img.width() - model_w, SLIDING_WINDOW_STRIDE):
            # Create a small image tile (Region of Interest)
            tile = img.copy(roi=(x, y, model_w, model_h))

            # Run the classifier on this small tile
            prediction = model.predict([tile])[0].flatten().tolist()
            scores = sorted(
                zip(model.labels, prediction), key=lambda item: item[1], reverse=True
            )
            label, confidence = scores[0]

            # If this is the best 'person' detection so far, save it
            if label == "person" and confidence > best_confidence:
                best_confidence = confidence
                best_box = (x, y, model_w, model_h)

    inference_time = time.ticks_diff(time.ticks_ms(), start_time)
    person_detected = best_confidence >= CONFIDENCE_THRESHOLD

    # Print detection info
    status_emoji = "✅" if person_detected else "❌"
    print(
        f"{status_emoji} Best Person Confidence: {best_confidence:.3f} | Scan Time: {inference_time}ms | FPS: {clock.fps():.1f}"
    )

    return person_detected, best_confidence, best_box


def save_image(img, person_detected, confidence):
    """Save image with enhanced naming and error handling"""
    global last_save_time

    current_time = time.ticks_ms()

    if time.ticks_diff(current_time, last_save_time) < SAVE_COOLDOWN:
        return False  # Cooldown active

    rand_str = get_rand(4)
    timestamp = utime.time()
    filename = f"img_{timestamp}_{rand_str}_{person_detected}_{confidence:.3f}.jpg"
    file_path = f"{IMG_DIR}{filename}"

    try:
        print(f"💾 Saving: {filename}")
        img.save(file_path, quality=95)
        last_save_time = current_time
        print(f"✅ Saved successfully")
        return True
    except Exception as e:
        print(f"❌ Save failed: {e}")
        return False


# --- Main Detection Loop ---
def person_detection_loop():
    """Enhanced main loop using the sliding window detector"""
    global image_count, detection_count, autofocus_counter

    while image_count < MAX_IMAGES_PER_SESSION:
        try:
            clock.tick()

            if autofocus_counter % AUTOFOCUS_INTERVAL == 0:
                trigger_autofocus()
            autofocus_counter += 1

            img = sensor.snapshot()
            image_count += 1

            # Detect person using the new sliding window function
            person_detected, confidence, box = detect_person_with_sliding_window(img)

            if person_detected and box:
                detection_count += 1
                # Draw the best bounding box on the image
                x, y, w, h = box
                img.draw_rectangle(x, y, w, h, color=(0, 255, 0), thickness=2)
                img.draw_string(
                    x, y - 12, f"PERSON: {confidence:.2f}", color=(0, 255, 0), scale=2
                )

            if SAVE_ALL_IMAGES or (person_detected and box):
                save_image(img, person_detected, confidence)

            if image_count % 50 == 0:
                print_session_stats()
                gc.collect()

            time.sleep_ms(100)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Loop error: {e}")
            time.sleep_ms(1000)
            continue

    print(f"\n🏁 Session complete. Max images ({MAX_IMAGES_PER_SESSION}) reached.")
    print_session_stats()


# --- Initialization ---
def initialize_system():
    """Initialize camera and model with enhanced error handling"""
    global model, model_w, model_h

    print("🚀 Initializing Enhanced Person Detection System...")

    try:
        print("📷 Setting up camera...")
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
        sensor.skip_frames(time=3000)
        sensor.set_auto_gain(False)
        sensor.set_auto_whitebal(False)
        sensor.set_auto_exposure(False)
        print("✅ Camera initialized")

        print("🧠 Loading ML model...")
        model = ml.Model(MODEL_PATH)
        # Get model input dimensions for the sliding window
        _, model_h, model_w, _ = model.input_shape[0]
        print("✅ Model loaded successfully")

        get_model_info()

        print("⚙️ CONFIGURATION:")
        print(f"  Confidence threshold: {CONFIDENCE_THRESHOLD}")
        print(f"  Sliding Window Stride: {SLIDING_WINDOW_STRIDE}px")
        print(f"  Save all images: {SAVE_ALL_IMAGES}")
        print("✅ System ready!")

        return True

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    if initialize_system():
        print("\n🎯 Starting person detection...")
        print("Press Ctrl+C to stop")
        print("-" * 50)

        try:
            person_detection_loop()
        except KeyboardInterrupt:
            print("\n👋 System stopped by user")
        except Exception as e:
            print(f"\n💥 System error: {e}")
        finally:
            print_session_stats()
            print("🔚 Session ended")
    else:
        print("💥 Failed to initialize system")
