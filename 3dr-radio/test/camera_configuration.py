import sensor
import image
import time
import pyb

# === CAMERA SETUP ===
sensor.reset()                         # Reset the sensor
sensor.set_pixformat(sensor.RGB565)   # Best color format for OpenMV (can also try GRAYSCALE for performance)
sensor.set_framesize(sensor.QVGA)     # 320x240 resolution for decent quality & performance
sensor.skip_frames(time = 2000)       # Give time to adjust
sensor.set_auto_gain(False)           # Turn off automatic gain for consistent results
sensor.set_auto_whitebal(False)       # Turn off white balance
sensor.set_brightness(0)              # Neutral brightness
sensor.set_saturation(1)              # Slightly increased color saturation
sensor.set_contrast(1)                # Better contrast for feature detection

clock = time.clock()

# === FACE DETECTION SETUP ===
face_cascade = image.HaarCascade("frontalface", stages=25)
print("Loaded face detection model.")

# === MOTION DETECTION SETUP ===
previous = sensor.snapshot()  # Initial frame for motion comparison

# === LED INDICATION ===
red_led = pyb.LED(1)
green_led = pyb.LED(2)

# === MAIN LOOP ===
while True:
    clock.tick()
    img = sensor.snapshot()

    # --- FACE DETECTION ---
    faces = img.find_features(face_cascade, threshold=0.75, scale=1.5)

    for r in faces:
        img.draw_rectangle(r, color=(255, 0, 0))
        img.draw_string(r[0], r[1] - 10, "Face", mono_space=False)
        red_led.on()
        print("[INFO] Face detected at:", r)
    if not faces:
        red_led.off()

    # --- MOTION DETECTION ---
    # Compare current image with the previous one
    diff = img.difference(previous)
    stats = diff.get_statistics()
    movement_level = stats.std()  # Standard deviation indicates motion

    if movement_level > 20:  # Tune this threshold for sensitivity
        green_led.on()
        print("[INFO] Movement detected. STD DEV:", movement_level)
    else:
        green_led.off()

    previous = img.copy()

    print("FPS:", clock.fps())
