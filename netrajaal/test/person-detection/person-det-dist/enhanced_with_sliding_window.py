import sensor
import ml
import time
import random
import gc

# --- Enhanced Configuration ---
MODEL_PATH = "/rom/person_detect.tflite"
CONFIDENCE_THRESHOLD = 0.7  # Increased for sliding window to reduce false positives
SLIDING_WINDOW_STRIDE = 64  # Increased from 16 to 64 for much better performance
MAX_WINDOWS_PER_FRAME = 25  # Limit total windows to process per frame
MIN_WINDOW_SIZE = 96  # Minimum window size to avoid tiny detections

# --- Global Variables ---
clock = time.clock()
image_count = 0
detection_count = 0
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

    print("\n--- SESSION STATS ---")
    print(f"Runtime: {elapsed_time:.1f}s")
    print(f"Images processed: {image_count}")
    print(f"Person detections: {detection_count}")
    print(f"Detection rate: {detection_rate:.1f}%")
    print(f"Avg FPS: {clock.fps():.2f}")
    print(f"Free memory: {gc.mem_free()} bytes")
    print("-" * 20)


def calculate_optimal_windows(
    img_width, img_height, model_w, model_h, max_windows=MAX_WINDOWS_PER_FRAME
):
    """
    Calculate optimal window positions to cover the image efficiently
    Returns list of (x, y) positions for windows
    """
    windows = []

    # Calculate how many windows we can fit in each dimension
    windows_x = min(
        max_windows // 2, (img_width - model_w) // SLIDING_WINDOW_STRIDE + 1
    )
    windows_y = min(
        max_windows // 2, (img_height - model_h) // SLIDING_WINDOW_STRIDE + 1
    )

    # Ensure we don't exceed max windows
    total_windows = windows_x * windows_y
    if total_windows > max_windows:
        # Reduce windows proportionally
        scale_factor = (max_windows / total_windows) ** 0.5
        windows_x = max(1, int(windows_x * scale_factor))
        windows_y = max(1, int(windows_y * scale_factor))

    # Generate window positions
    for y in range(0, img_height - model_h, SLIDING_WINDOW_STRIDE):
        if len(windows) >= max_windows:
            break
        for x in range(0, img_width - model_w, SLIDING_WINDOW_STRIDE):
            if len(windows) >= max_windows:
                break
            windows.append((x, y))

    return windows


def detect_person_with_sliding_window(img):
    """
    Optimized person detection using sliding window with limited windows and better performance.
    """
    global model_w, model_h
    start_time = time.ticks_ms()

    best_confidence = 0
    best_box = None
    person_detected = False

    # Calculate optimal window positions
    windows = calculate_optimal_windows(img.width(), img.height(), model_w, model_h)

    print(f"🔍 Processing {len(windows)} windows (stride: {SLIDING_WINDOW_STRIDE}px)")

    # Process each window
    for i, (x, y) in enumerate(windows):
        # Create a small image tile (Region of Interest) - more efficient than copy
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

        # Early termination if we find a very confident detection
        if best_confidence > 0.95:
            break

    inference_time = time.ticks_diff(time.ticks_ms(), start_time)
    person_detected = best_confidence >= CONFIDENCE_THRESHOLD

    # Print detection info
    status_emoji = "✅" if person_detected else "❌"
    print(
        f"{status_emoji} Best Person Confidence: {best_confidence:.3f} | Scan Time: {inference_time}ms | FPS: {clock.fps():.1f} | Windows: {len(windows)}"
    )

    return person_detected, best_confidence, best_box


# --- Main Detection Loop ---
def person_detection_loop():
    """Optimized main loop using the sliding window detector"""
    global image_count, detection_count

    while True:  # Removed MAX_IMAGES_PER_SESSION limit for continuous operation
        try:
            clock.tick()
            img = sensor.snapshot()
            image_count += 1

            # Detect person using the optimized sliding window function
            person_detected, confidence, box = detect_person_with_sliding_window(img)

            if person_detected and box:
                detection_count += 1
                # Draw the best bounding box on the image
                x, y, w, h = box
                img.draw_rectangle(x, y, w, h, color=(0, 255, 0), thickness=2)
                img.draw_string(
                    x, y - 12, f"PERSON: {confidence:.2f}", color=(0, 255, 0), scale=2
                )

            # Print stats every 10 frames instead of 50 for more frequent feedback
            if image_count % 10 == 0:
                print_session_stats()
                gc.collect()

            # Reduced sleep time for better responsiveness
            time.sleep_ms(50)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Loop error: {e}")
            time.sleep_ms(1000)
            continue

    print("\n🏁 Session complete.")
    print_session_stats()


# --- Initialization ---
def initialize_system():
    """Initialize camera and model with enhanced error handling"""
    global model, model_w, model_h

    print("🚀 Initializing Optimized Person Detection System...")

    try:
        print("📷 Setting up camera...")
        sensor.reset()
        sensor.set_pixformat(sensor.GRAYSCALE)
        sensor.set_framesize(sensor.QVGA)
        sensor.set_windowing(320, 320)
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

        print("⚙️ OPTIMIZED CONFIGURATION:")
        print(f"  Confidence threshold: {CONFIDENCE_THRESHOLD}")
        print(f"  Sliding Window Stride: {SLIDING_WINDOW_STRIDE}px (optimized)")
        print(f"  Max windows per frame: {MAX_WINDOWS_PER_FRAME}")
        print(f"  Model input size: {model_w}x{model_h}")
        print("✅ System ready!")

        return True

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    if initialize_system():
        print("\n🎯 Starting optimized person detection...")
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
