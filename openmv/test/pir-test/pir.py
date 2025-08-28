# PIR Thermal Body Detection with SD Card Logging for OpenMV RT1062
# PANASONIC EKMB1306112K PIR SENSOR - Continuous thermal body presence detection

import sensor, image, time, machine
from machine import Pin
import os
import json

# Initialize camera
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)  # 320x240
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# Initialize PIR sensor pin (adjust pin number based on your wiring)
# Connect PIR sensor output to a digital pin
PIR_PIN = Pin('P13', Pin.IN, Pin.PULL_DOWN)  # Adjust pin as needed

p1_pin = Pin('P14', Pin.OUT)  # Configure as output
p1_pin.on()                  # Make it HIGH
# or
p1_pin.value(1)             # Alternative way to make it HIGH

# Initialize LED pins for status indication
red_led = Pin('P1', Pin.OUT)     # Thermal body detected
green_led = Pin('P2', Pin.OUT)   # System ready
blue_led = Pin('P3', Pin.OUT)    # System active

# SD Card initialization
try:
    # os.mount("/sdcard", "/sdcard")
    # print("SD card mounted successfully")
    os.listdir('/sdcard')
    print("SD card available")
    sd_available = True
except:
    print("SD card not available or not inserted")
    sd_available = False

# Configuration
CAPTURE_INTERVAL = 1000        # Capture image every 1 second when thermal body detected
CONTINUOUS_CAPTURE = True      # Capture continuously while body is present
LOG_SAVE_ENABLED = True

# Create directories if they don't exist
if sd_available:
    try:
        os.mkdir("thermal_logs")
    except:
        pass
    try:
        os.mkdir("thermal_images")
    except:
        pass

def get_timestamp():
    """Get current timestamp as string"""
    rtc = machine.RTC()
    datetime = rtc.datetime()
    return "{:04d}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}".format(
        datetime[0], datetime[1], datetime[2],
        datetime[4], datetime[5], datetime[6]
    )

def save_thermal_log(timestamp, pir_status, image_count=0):
    """Save thermal body detection log to SD card"""
    if not sd_available or not LOG_SAVE_ENABLED:
        return

    log_data = {
        "timestamp": timestamp,
        "thermal_body_present": pir_status,
        "images_captured": image_count,
        "sensor_type": "PANASONIC_EKMB1306112K",
        "detection_range": "17m"
    }

    try:
        # Append to daily log file
        date_str = timestamp.split('_')[0]
        log_filename = "/sdcard/thermal_logs/thermal_log_{}.json".format(date_str)

        # Read existing logs
        logs = []
        try:
            with open(log_filename, 'r') as f:
                content = f.read()
                if content.strip():  # Check if file has content
                    logs = json.loads(content)
        except:
            logs = []

        # Add new log entry
        logs.append(log_data)

        # Write back to file
        with open(log_filename, 'w') as f:
            f.write(json.dumps(logs))

        print("Thermal log saved: {}".format(timestamp))

    except Exception as e:
        print("Error saving thermal log:", str(e))

def save_thermal_image(img, timestamp, sequence_num=0):
    """Save captured image when thermal body is detected"""
    if not sd_available:
        return False

    try:
        if sequence_num > 0:
            filename = "/sdcard/thermal_images/thermal_{}_{:03d}.jpg".format(timestamp, sequence_num)
        else:
            filename = "/sdcard/thermal_images/thermal_{}.jpg".format(timestamp)

        img.save(filename, quality=90)
        print("Thermal image saved: {}".format(filename))
        return True
    except Exception as e:
        print("Error saving image:", e)
        return False

def check_thermal_body():
    """Check if thermal body is present in PIR sensor path"""
    return PIR_PIN.value()

# Main loop variables
last_capture_time = 0
thermal_body_present = False
previous_state = False
detection_session_start = None
session_image_count = 0
total_detections = 0

print("PIR Thermal Body Detection System Started")
print("PIR Sensor: PANASONIC EKMB1306112K")
print("Detection Range: 17m")
print("Mode: Continuous thermal body presence detection")
print("SD Card Status:", "Available" if sd_available else "Not Available")
print("Scanning for thermal bodies...")

# Status indication
green_led.on()  # System ready
time.sleep_ms(1000)
green_led.off()

try:
    while True:
        # Capture image
        img = sensor.snapshot()

        # Check for thermal body presence
        thermal_body_present = check_thermal_body()
        current_time = time.ticks_ms()

        # Thermal body detection logic
        if thermal_body_present:
            # Thermal body is present in sensor path
            red_led.on()  # Indicate detection

            # Start new detection session if this is first detection
            if not previous_state:
                detection_session_start = get_timestamp()
                session_image_count = 0
                total_detections += 1
                print("THERMAL BODY DETECTED! Session: {}".format(total_detections))
                print("Starting continuous capture...")

            # Capture image at specified intervals while body is present
            if CONTINUOUS_CAPTURE and time.ticks_diff(current_time, last_capture_time) >= CAPTURE_INTERVAL:
                session_image_count += 1
                timestamp = get_timestamp()

                # Save image with sequence number for continuous capture
                image_saved = save_thermal_image(img, detection_session_start, session_image_count)

                if image_saved:
                    print("Captured image {}: thermal body present".format(session_image_count))

                last_capture_time = current_time

            # Add text overlay to current image
            img.draw_string(10, 10, "THERMAL BODY PRESENT", color=(255, 0, 0), scale=2)
            img.draw_string(10, 30, "Session: {}".format(total_detections), color=(255, 0, 0))
            img.draw_string(10, 50, "Images: {}".format(session_image_count), color=(255, 255, 0))
            if detection_session_start:
                img.draw_string(10, 70, detection_session_start, color=(255, 255, 255))

        else:
            # No thermal body detected
            red_led.off()

            # End detection session if body was previously present
            if previous_state:
                end_timestamp = get_timestamp()
                print("Thermal body left sensor range")
                print("Session ended - {} images captured".format(session_image_count))

                # Save session log
                save_thermal_log(end_timestamp, False, session_image_count)

        # Update previous state
        previous_state = thermal_body_present

        # Display status on image
        status_color = (255, 0, 0) if thermal_body_present else (0, 255, 0)
        status_text = "BODY DETECTED" if thermal_body_present else "SCANNING"

        img.draw_string(10, img.height() - 60, "PIR: {}".format(status_text),
                       color=status_color, scale=2)
        img.draw_string(10, img.height() - 40, "Range: 17m", color=(255, 255, 255))
        img.draw_string(10, img.height() - 20, "Sessions: {}".format(total_detections),
                       color=(255, 255, 255))

        # Blue LED blinks when system is active
        if current_time % 2000 < 100:  # Blink every 2 seconds
            blue_led.on()
        else:
            blue_led.off()

        time.sleep_ms(100)  # Small delay for stability

except KeyboardInterrupt:
    print("\nSystem stopped by user")

except Exception as e:
    print("System error:", e)

finally:
    # Cleanup
    red_led.off()
    green_led.off()
    blue_led.off()

    # Save final session summary
    if sd_available:
        try:
            summary = {
                "session_end": get_timestamp(),
                "total_detection_sessions": total_detections,
                "sensor_model": "PANASONIC_EKMB1306112K",
                "detection_range": "17m",
                "mode": "continuous_thermal_presence"
            }

            with open("/sdcard/thermal_logs/session_summary.json", 'w') as f:
                f.write(json.dumps(summary))

        except:
            pass

    print("Final detection sessions: {}".format(total_detections))
    print("System shutdown complete")
