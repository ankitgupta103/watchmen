"""
Simple OpenMV RT1062 Low Power Mode Test

A minimal script to test low power mode entry and exit.
"""

import time
import machine

# Initialize LEDs
# OpenMV RT1062 uses LED_B for blue LED
try:
    led = machine.Pin("LED_B", machine.Pin.OUT)  # Blue LED
except:
    # Fallback if LED name differs
    led = machine.Pin("LED_BLUE", machine.Pin.OUT)

# Initialize RTC
rtc = machine.RTC()

print("Starting low power test...")
led.on()
time.sleep(1)
led.off()

# Set wake-up alarm for 5 seconds
rtc.wakeup(5000)
print("Entering light sleep mode for 5 seconds...")
print("(Check power consumption now)")

# Enter light sleep
machine.lightsleep()

# After wake-up
print("Woke up from light sleep!")
led.on()
time.sleep(2)
led.off()

print("Test complete!")

