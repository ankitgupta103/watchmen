import sensor
import image
import time
from machine import Pin, LED

# Initialize camera sensor
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)  # You can change this to other sizes like sensor.VGA, sensor.HD, etc.
sensor.skip_frames(time=2000)  # Allow the camera to adjust

# Configure pin 7 as input with pull-down resistor
# On OpenMV RT1062, pins are accessed using string names like "P7"
# Change to Pin.PULL_UP if your signal is active low
trigger_pin = Pin("P7", Pin.IN, Pin.PULL_DOWN)

# Configure LED (using machine.LED)
led = LED("LED_BLUE")

# Variable to track previous pin state (for edge detection)
previous_state = False
image_counter = 0

print("Image capture system ready. Waiting for trigger on pin 7...")

while True:
    # Read current pin state
    current_state = trigger_pin.value()
    
    # Detect rising edge (transition from low to high)
    if current_state == 1 and previous_state == 0:
        print("Trigger detected! Capturing image...")
        
        # Capture image
        img = sensor.snapshot()
        
        # Save image to SD card with timestamp or counter
        filename = "/sdcard/image_%d.jpg" % image_counter
        img.save(filename)
        print("Image saved as: %s" % filename)
        
        # Blink LED to indicate image captured and saved
        led.on()
        time.sleep_ms(100)
        led.off()
        time.sleep_ms(100)
        led.on()
        time.sleep_ms(100)
        led.off()
        
        image_counter += 1
        
        # Small delay to debounce
        time.sleep_ms(100)
    
    # Update previous state
    previous_state = current_state
    
    # Small delay to prevent excessive CPU usage
    time.sleep_ms(10)

