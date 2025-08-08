import sensor
import os
import time
import machine

# --- Configuration ---
LOCATION_ID = "LOC_005"  # An identifier for the camera's location
PERSON_PRESENT_GROUND_TRUTH = False
CAPTURE_INTERVAL_MS = 4000  # e.g., 4000ms = 4 seconds

# Motion Detection Parameters
TRIGGER_THRESHOLD = 35  # The minimum difference value to be considered 'motion'
BG_UPDATE_FRAMES = 50  # How many frames pass before the background is updated
BG_UPDATE_BLEND = 128  # How much to blend the new frame into the background (0-256)

# File and Directory Paths
IMAGE_DIR = "/sdcard/images"
LOG_FILE_PATH = "/sdcard/datalog.csv"

# --- Initialization ---
sensor.reset()  # Initialize the camera sensor
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
sensor.skip_frames(time=2000)  # Allow settings to stabilize
sensor.set_auto_whitebal(False)  # Disable auto white balance for consistent imaging
led = machine.LED("LED_RED")

# --- CSV Logging Setup ---
header = (
    "timestamp_ms,location_id,diff_value,motion_detected,person_present_ground_truth\n"
)
print(f"{header}")
try:
    file_info = os.stat(LOG_FILE_PATH)
    write_header = file_info[6] == 0
except OSError:
    write_header = True

log_file = open(LOG_FILE_PATH, "a")

if write_header:
    # Write header to file
    log_file.write(header)
    log_file.flush()
    # Also print header to console
    print(header.strip())
    print(f"-> Created new log file: {LOG_FILE_PATH}")
else:
    # If file exists, still print header to console for context during a new session
    print(header.strip())
    print(f"-> Appending to existing log file: {LOG_FILE_PATH}")


# --- Background Image Setup ---
extra_fb = sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.RGB565)
print("Capturing initial background image...")
sensor.skip_frames(time=2000)
extra_fb.replace(sensor.snapshot())
print("Background captured. Starting interval capture loop.")
# -----------------------------

frame_count = 0
while True:
    img = sensor.snapshot()

    frame_count += 1
    # --- Background Maintenance ---
    if frame_count > BG_UPDATE_FRAMES:
        frame_count = 0
        img.blend(extra_fb, alpha=(256 - BG_UPDATE_BLEND))
        extra_fb.replace(img)

    # --- Motion Detection ---
    original_img = img.copy()
    img.difference(extra_fb)
    hist = img.get_histogram()
    diff_value = (
        hist.get_percentile(0.99).l_value() - hist.get_percentile(0.90).l_value()
    )
    motion_detected = diff_value > TRIGGER_THRESHOLD

    # Get a timestamp for the event
    timestamp = time.ticks_ms()

    # --- Image Saving (Runs every interval) ---
    led.on()
    image_filename = f"{IMAGE_DIR}/{LOCATION_ID}-{timestamp}-{motion_detected}.jpg"
    original_img.save(image_filename, quality=90)
    led.off()

    # --- Log Data to File and Console ---
    # Create the log entry as a CSV-formatted string
    log_entry = f"{timestamp},{LOCATION_ID},{diff_value},{motion_detected},{PERSON_PRESENT_GROUND_TRUTH}\n"

    # Write the entry to the file
    log_file.write(log_entry)
    log_file.flush()

    # Print the exact same entry to the console (without the newline character)
    print(log_entry.strip())

    # --- Interval Delay ---
    # Pause the script to create a fixed interval between captures
    time.sleep_ms(CAPTURE_INTERVAL_MS)
