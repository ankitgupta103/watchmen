import sensor
import ml
import time
import random
import utime
import gc

# --- Enhanced Configuration ---
MODEL_PATH = "/rom/person_detect.tflite"
IMG_DIR = "/sdcard/images/"
CONFIDENCE_THRESHOLD = 0.8
SAVE_COOLDOWN = 5000  # milliseconds between saves
AUTOFOCUS_INTERVAL = 10  # frames between autofocus attempts
SAVE_ALL_IMAGES = False  # Set to True to save all images, False to save only detections
MAX_IMAGES_PER_SESSION = 1000  # Prevent storage overflow

# --- Global Variables ---
clock = time.clock()
image_count = 0
detection_count = 0
last_save_time = 0
autofocus_counter = 0
session_start_time = time.ticks_ms()
best_confidence_session = 0.0  # New variable to track the best confidence


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
    """Print session statistics, now including best confidence"""
    elapsed_time = time.ticks_diff(time.ticks_ms(), session_start_time) / 1000
    detection_rate = (detection_count / image_count * 100) if image_count > 0 else 0

    print("\n--- SESSION STATS ---")
    print(f"Runtime: {elapsed_time:.1f}s")
    print(f"Images processed: {image_count}")
    print(f"Person detections: {detection_count}")
    print(f"Detection rate: {detection_rate:.1f}%")
    print(
        f"Best Confidence Achieved: {best_confidence_session:.3f}"
    )  # Display best confidence
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


def detect_person(img):
    """Enhanced person detection with timing and detailed output"""
    start = time.ticks_ms()
    prediction = model.predict([img])
    inference_time = time.ticks_diff(time.ticks_ms(), start)

    # Process predictions
    scores = zip(model.labels, prediction[0].flatten().tolist())
    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    person_confidence = 0.0
    person_detected = False

    # Find person confidence
    for label, conf in scores:
        if label == "person":
            person_confidence = conf
            person_detected = conf >= CONFIDENCE_THRESHOLD
            break

    # Print detailed detection info
    status_emoji = "✅" if person_detected else "❌"
    print(
        f"{status_emoji} Person: {person_confidence:.3f} | Inference: {inference_time}ms | FPS: {clock.fps():.1f}"
    )

    return person_detected, person_confidence, inference_time


def save_image(img, person_detected, confidence):
    """Save image with enhanced naming and error handling"""
    global last_save_time, image_count

    current_time = time.ticks_ms()

    # Check cooldown period
    if time.ticks_diff(current_time, last_save_time) < SAVE_COOLDOWN:
        print("⏳ Cooldown active, skipping save")
        return False

    # Generate filename with timestamp and detection info
    rand_str = get_rand(4)
    timestamp = utime.time()
    filename = f"img_{timestamp}_{rand_str}_{person_detected}_{confidence:.3f}.jpg"
    file_path = f"{IMG_DIR}{filename}"

    try:
        print(f"💾 Saving: {filename}")
        img.save(file_path, quality=95)
        last_save_time = current_time
        print("✅ Saved successfully")
        return True
    except Exception as e:
        print(f"❌ Save failed: {e}")
        return False


# --- Main Detection Loop ---
def person_detection_loop():
    """Enhanced main detection loop with better error handling"""
    global image_count, detection_count, autofocus_counter, best_confidence_session

    while image_count < MAX_IMAGES_PER_SESSION:
        try:
            clock.tick()

            # Periodic autofocus
            # if autofocus_counter % AUTOFOCUS_INTERVAL == 0:
            #     trigger_autofocus()
            # autofocus_counter += 1

            # Capture image
            img = sensor.snapshot()
            image_count += 1

            # Detect person
            person_detected, confidence, inference_time = detect_person(img)

            if person_detected:
                detection_count += 1

                # Update best confidence if the current one is higher
                if confidence > best_confidence_session:
                    best_confidence_session = confidence
                    print(f"🎉 New Best Confidence: {best_confidence_session:.3f}")

                # Draw detection indicator on image
                img.draw_string(
                    10, 10, f"PERSON: {confidence:.2f}", color=(0, 255, 0), scale=2
                )
                img.draw_rectangle((5, 5, 310, 30), color=(0, 255, 0), thickness=2)

            # Save image based on configuration
            should_save = SAVE_ALL_IMAGES or person_detected
            if should_save:
                save_image(img, person_detected, confidence)

            # Periodic stats update
            if image_count % 50 == 0:
                print_session_stats()
                gc.collect()  # Garbage collection

            # Brief pause to prevent overwhelming the system
            time.sleep_ms(100)

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Loop error: {e}")
            time.sleep_ms(1000)  # Longer pause on error
            continue

    print(f"\n🏁 Session complete. Max images ({MAX_IMAGES_PER_SESSION}) reached.")
    print_session_stats()


# --- Initialization ---
def initialize_system():
    """Initialize camera and model with enhanced error handling"""
    global model

    print("🚀 Initializing Enhanced Person Detection System...")

    try:
        # Camera setup
        print("📷 Setting up camera...")
        sensor.reset()
        sensor.set_pixformat(sensor.GRAYSCALE)
        sensor.set_framesize(sensor.VGA)  # 320x240 for best balance
        sensor.skip_frames(time=3000)
        sensor.set_auto_gain(False)
        sensor.set_auto_whitebal(False)
        sensor.set_auto_exposure(False)
        print("✅ Camera initialized")

        # Model loading
        print("🧠 Loading ML model...")
        model = ml.Model(MODEL_PATH)
        print("✅ Model loaded successfully")

        # Display model info
        get_model_info()

        # Configuration summary
        print("⚙️ CONFIGURATION:")
        print(f"  Confidence threshold: {CONFIDENCE_THRESHOLD}")
        print(f"  Save cooldown: {SAVE_COOLDOWN}ms")
        print(f"  Save all images: {SAVE_ALL_IMAGES}")
        print(f"  Max images: {MAX_IMAGES_PER_SESSION}")
        print(f"  Autofocus interval: {AUTOFOCUS_INTERVAL} frames")
        print("✅ System ready!")

        return True

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def run_camera_loop():
    clock = time.clock()
    frame_count = 0

    try:
        while True:
            clock.tick()
            sensor.snapshot()
            frame_count += 1
            print(
                f"🖼️ Frame {frame_count} | FPS: {clock.fps():.2f} | Free mem: {gc.mem_free()} bytes"
            )
            time.sleep_ms(100)
    except KeyboardInterrupt:
        print("\n🛑 Camera loop stopped by user")


# --- Main Execution ---
if __name__ == "__main__":
    if initialize_system():
        print("\n🎯 Starting person detection...")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        # run_camera_loop()

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
