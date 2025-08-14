import sensor
import time
import image

# === Camera Setup ===
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# === Config Parameters ===
motion_threshold = 25       # Change for sensitivity
min_blob_area = 300         # Minimum blob area to qualify as object
movement_frames_required = 3  # Number of frames with motion before confirming
movement_frames_lost = 5      # Number of frames without motion to reset

# === State Variables ===
prev_img = sensor.snapshot().copy()
motion_state = False           # True = movement ongoing, False = idle
motion_detected_count = 0
motion_lost_count = 0

clock = time.clock()

while True:
    clock.tick()
    curr_img = sensor.snapshot()
    diff_img = curr_img.difference(prev_img)
    stats = diff_img.statistics()

    if stats.max() > motion_threshold:
        # Potential motion detected
        blobs = curr_img.find_blobs([(50, 255)], pixels_threshold=200, area_threshold=min_blob_area)

        if blobs:
            motion_detected_count += 1
            motion_lost_count = 0  # Reset lost counter
            if not motion_state and motion_detected_count >= movement_frames_required:
                # Motion just started
                motion_state = True
                print("🚶 Brief Movement Detected!")
                for b in blobs:
                    curr_img.draw_rectangle(b.rect(), color=127)
                    curr_img.draw_cross(b.cx(), b.cy(), color=127)
                    print("Object at X=%d Y=%d" % (b.cx(), b.cy()))
        else:
            motion_detected_count = 0
    else:
        # No motion
        motion_lost_count += 1
        if motion_lost_count >= movement_frames_lost:
            # Reset state to allow next detection
            motion_state = False
            motion_detected_count = 0
            motion_lost_count = 0

    prev_img = curr_img.copy()
    time.sleep_ms(50)
