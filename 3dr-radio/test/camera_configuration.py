import sensor    
import image     
import machine   
import time      

# === CAMERA CONFIGURATION ===
sensor.reset()  # Resets and initializes the camera sensor. Always call this first.

sensor.set_pixformat(sensor.RGB565)
# Sets image pixel format.
# Options:
# - sensor.RGB565 : Color image (2 bytes per pixel)
# - sensor.GRAYSCALE : Single-channel, faster for processing like face/motion detection

sensor.set_framesize(sensor.QVGA)
# Sets the frame size (resolution).
# Common options:
# - sensor.QQVGA : 160x120 (faster, lower detail)
# - sensor.QVGA  : 320x240 (balance of speed and quality)
# - sensor.VGA   : 640x480 (high resolution, slower FPS)
# - sensor.SVGA  : 800x600 (higher resolution, even slower FPS)
# - sensor.XGA   : 1024x768 (highest resolution, very slow FPS)
# - sensor.SXGA  : 1280x960 (highest resolution, very slow FPS)
# - sensor.HD     : 1920x1080 (Full HD, very slow FPS)

sensor.skip_frames(time=2000)
# Waits ~2 seconds to allow auto-adjustment of exposure and settings.

sensor.set_auto_gain(False)
# Disable automatic gain (brightness boost). Recommended to fix lighting.
# If enabled, it can cause flickering in changing light conditions.
# Options:
# - True  : Automatic gain control (default, can cause flickering)  
# - False : Manual control (recommended for consistent lighting)


sensor.set_auto_whitebal(False)
# Disable automatic white balance. Fixes color in consistent lighting.
# Options:
# - True  : Automatic white balance (default, can cause color shifts)   
# - False : Manual control (recommended for consistent color)


sensor.set_brightness(50)
# Set brightness manually. Range: -3 to +3 (or 0-100 depending on firmware).
# Higher values increase brightness, lower values decrease it.
# Default is 0 (no change).
# sensor.set_brightness(50) sets brightness to 50% of maximum.
# sensor.set_brightness(0) would leave it unchanged.
# sensor.set_brightness(-3) would set it to minimum brightness.
# sensor.set_brightness(3) would set it to maximum brightness.

sensor.set_contrast(1)
# Adjust contrast. Range: -3 (less contrast) to +3 (more contrast)
# sensor.set_contrast(1) sets contrast to 1 (default is 0).
# sensor.set_contrast(-3) would set it to minimum contrast.
# sensor.set_contrast(3) would set it to maximum contrast.


sensor.set_saturation(1)
# Adjust color saturation. Range: -3 (less color) to +3 (more color)
# sensor.set_saturation(1) sets saturation to 1 (default is 0).
# sensor.set_saturation(-3) would set it to minimum saturation.
# sensor.set_saturation(3) would set it to maximum saturation.

# === CLOCK FOR FPS MEASUREMENT ===
clock = time.clock()
# Measures frames per second. Call clock.tick() each loop iteration.
# It provides clock.fps() to get the current FPS.
# It is useful for performance monitoring and debugging.


# === LED SETUP ===
led = machine.LED("LED_RED")
# Initializes the red LED on the OpenMV board.
# Options: "LED_RED", "LED_GREEN", "LED_BLUE"

# === LOAD HAAR CASCADE FOR FACE DETECTION ===
face_cascade = image.HaarCascade("/rom/haarcascade_frontalface.cascade", stages=25)
# Haar cascade classifier for detecting frontal human faces.
# stages=25 loads all 25 stages (more accurate, slower).
# Available cascades: frontalface, eyes, smile, etc.

# === CREATE FOLDER IF NEEDED ===
# if "snapshots" not in os.listdir():
#     os.mkdir("snapshots")
# Use this if you want to create a directory to store images.
# You can also create "people", "motion", etc. as folders.

# === MAIN LOOP ===
while True:
    clock.tick()                 # Start measuring frame duration
    img = sensor.snapshot()     # Capture a frame from the camera

    # --- FACE DETECTION ---
    faces = img.find_features(face_cascade, threshold=0.6, scale_factor=1.5)
    # Detects faces using Haar cascade
    # - threshold: confidence (0.0 to 1.0). Lower → more detections (and false positives)
    # - scale_factor: controls size of object detected (higher → detect smaller objects)

    if faces:
        for r in faces:
            img.draw_rectangle(r)                        # Draw a box around the face
            img.draw_string(r[0], r[1] - 10, "Face")     # Label the rectangle

        led.on()  # Turn on red LED to indicate face detected

        filename = "/people/face_%d.jpg" % time.ticks_ms()
        # Generate a unique filename using current time in milliseconds.
        # Save to the "/people/" directory 

        try:
            img.save(filename)  # Save the current image to SD card
            print("[INFO] Saved image:", filename)
        except Exception as e:
            print("[ERROR] Could not save image:", e)

        led.off()  # Turn off LED after saving

    # --- MOTION DETECTION ---
    # If you want to detect motion instead of or in addition to face,
    # you can use frame differencing like this:
    #
    # bg = sensor.snapshot()               # Save background image
    # time.sleep_ms(500)
    # current = sensor.snapshot()
    # diff = current.difference(bg)       # Calculate difference image
    # stats = diff.statistics()
    # if stats[5] > threshold:            # If lighting difference > threshold
    #     print("Motion detected!")

