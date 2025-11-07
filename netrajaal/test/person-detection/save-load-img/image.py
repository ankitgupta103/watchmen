import sensor
import time
import machine
import image  # Required to load image from file

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

led = machine.LED("LED_BLUE")

# Blink LED for 3 seconds
start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < 3000:
    sensor.snapshot()
    led.toggle()
    time.sleep_ms(100)

led.off()

# # Take final snapshot
# img = sensor.snapshot()

# # Save to SD card
# filename = "/sdcard/jack111.jpg"  # Always use absolute path for SD
# img.save(filename)

# # Load the saved image
# loaded_img = image.Image(filename, copy_to_fb=True) # Load as mutable image

# # Display it in OpenMV IDE
# sensor.flush()  # Clear previous frame
# print("Displaying saved image from SD card...")
# loaded_img.draw_string(10, 10, "Saved Image", color=(255, 0, 0))  # Optional annotation
# sensor.snapshot()  # Required to refresh display in IDE
# # Note: Displaying saved image requires a dummy snapshot or IDE may not refresh

# # Show the loaded image
# while True:
#     # Continuously display loaded image
#     sensor.flush()
#     loaded_img.draw_image(loaded_img, 0, 0)
#     time.sleep(200)





# Take and save final snapshot
img = sensor.snapshot()
filename = "/sdcard/image100/example.jpg"
img.save(filename)

# Load saved image as mutable
loaded_img = image.Image(filename, copy_to_fb=True)

# Draw something on it (optional)
loaded_img.draw_string(10, 10, "Saved Image", color=(255, 0, 0))

# Display in IDE (need to draw it back to framebuffer)
sensor.flush()
sensor.snapshot()  # Snapshot to refresh IDE display
