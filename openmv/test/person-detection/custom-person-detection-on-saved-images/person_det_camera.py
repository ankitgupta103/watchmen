# === Import required modules ===
import sensor     # Camera sensor control (capture, resolution, etc.)
import time       # Timing and delays
import ml         # Machine learning module (TFLite inference)
import os         # File system access (to save images)
import image      # Image drawing and manipulation

# === CONFIGURATION PARAMETERS ===
MODEL_PATH = "/rom/person_detect.tflite"  # Path to built-in MobileNet person detection model
SAVE_DIR = "/person_logs"                 # Folder to store captured images
CONFIDENCE_THRESHOLD = 0.6                # Minimum confidence to count detection
MAX_IMAGES = 1000                         # Stop after saving this many images (to prevent memory overflow)

# === CAMERA INITIALIZATION ===
sensor.reset()                      # Reset and initialize the camera
sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (color)
sensor.set_framesize(sensor.HD)     # Set frame size to HD (1280x720) for better spatial resolution
sensor.skip_frames(time=2000)       # Allow the camera to adjust settings for 2 seconds

# === CREATE DIRECTORY FOR SAVING IMAGES ===
try:
    os.mkdir(SAVE_DIR)              # Try to create the save directory
except OSError:
    pass                            # Ignore error if the folder already exists

# === LOAD MACHINE LEARNING MODEL ===
model = ml.Model(MODEL_PATH)        # Load the TFLite person detection model
print(" Model loaded:", model)    # Confirm successful model load

# === START FPS CLOCK ===
clock = time.clock()                # Used to measure frames per second
image_count = 0                     # Counter to keep track of saved images

# === PERSON DETECTION LOGIC FUNCTION ===
def detect_person(img, prediction):
    global image_count

    # Zip the model's labels with the prediction values and sort by confidence
    scores = zip(model.labels, prediction[0].flatten().tolist())
    scores = sorted(scores, key=lambda x: x[1], reverse=True)  # Highest confidence first

    label, confidence = scores[0]   # Take the top prediction

    # If the top label is "person" and above confidence threshold
    if label == "person" and confidence >= CONFIDENCE_THRESHOLD:
        print(f" Person detected with confidence: {confidence:.2f}")

        # # File paths to save raw and annotated images
        # raw_path = f"{SAVE_DIR}/raw_{image_count}.jpg"
        # processed_path = f"{SAVE_DIR}/processed_{image_count}.jpg"

        # img.save(raw_path)  # Save raw image before drawing

        # Draw visual annotations on the image
        img.draw_rectangle((0, 0, img.width(), img.height()), color=(255, 0, 0), thickness=2)  # Full image border
        img.draw_string(4, 4, f"Person: {confidence:.2f}", color=(255, 255, 255), scale=2)      # Label text

        # img.save(processed_path)  # Save image with annotations

        # image_count += 1  # Increment image counter
        # if image_count >= MAX_IMAGES:
        #     print(" Max image count reached.")  # Safety exit to prevent memory overuse
        #     raise SystemExit

# === MAIN LOOP ===
while True:
    clock.tick()                       # Start measuring time for this frame
    img = sensor.snapshot()           # Capture image from camera
    prediction = model.predict([img]) # Run ML model inference on the image
    detect_person(img, prediction)    # Process the prediction and save if necessary
    print(f"FPS: {clock.fps():.2f}")  # Print current frame rate
