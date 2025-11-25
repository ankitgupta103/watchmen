"""
OpenMV RT1062 Low Power Mode Test Script

This script tests the low power mode functionality of the OpenMV RT1062 camera module.
It demonstrates entering low power mode and waking up from it.

Features:
- Enters light sleep mode
- Uses RTC alarm to wake up
- Provides LED feedback
- Serial output for debugging
"""

import time
import machine

# Initialize LED for visual feedback
# OpenMV RT1062 uses LED_R, LED_G, LED_B
try:
    led_red = machine.Pin("LED_R", machine.Pin.OUT)  # Red LED
    led_green = machine.Pin("LED_G", machine.Pin.OUT)  # Green LED
    led_blue = machine.Pin("LED_B", machine.Pin.OUT)  # Blue LED
except:
    # Fallback if LED names differ - adjust pin names as needed for your board
    led_red = machine.Pin("LED_RED", machine.Pin.OUT)
    led_green = machine.Pin("LED_GREEN", machine.Pin.OUT)
    led_blue = machine.Pin("LED_BLUE", machine.Pin.OUT)

# Initialize RTC for wake-up alarm
rtc = machine.RTC()

def blink_led(led, times=3, duration=0.1):
    """Blink an LED a specified number of times"""
    for _ in range(times):
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)

def print_status(message):
    """Print status message (for serial debugging)"""
    print(f"[{time.ticks_ms()}] {message}")

def test_light_sleep():
    """Test entering and exiting light sleep mode"""
    print_status("=" * 50)
    print_status("Starting Low Power Mode Test")
    print_status("=" * 50)
    
    # Blink green LED to indicate start
    blink_led(led_green, 2, 0.2)
    
    # Get current time
    current_time = rtc.datetime()
    print_status(f"Current RTC time: {current_time}")
    
    # Calculate wake-up time (5 seconds from now)
    wake_seconds = current_time[6] + 5  # Add 5 seconds to current second
    wake_minutes = current_time[5]
    wake_hours = current_time[4]
    
    # Handle second overflow
    if wake_seconds >= 60:
        wake_seconds -= 60
        wake_minutes += 1
        if wake_minutes >= 60:
            wake_minutes = 0
            wake_hours += 1
            if wake_hours >= 24:
                wake_hours = 0
    
    # Set RTC alarm for wake-up
    rtc.wakeup(5000)  # Wake up after 5 seconds (5000 milliseconds)
    print_status(f"RTC alarm set for 5 seconds")
    
    # Blink red LED to indicate entering sleep
    print_status("Entering light sleep mode in 2 seconds...")
    blink_led(led_red, 3, 0.15)
    time.sleep(2)
    
    # Record time before sleep
    time_before_sleep = time.ticks_ms()
    print_status("Entering light sleep mode NOW...")
    print_status("(Module should consume minimal power)")
    
    # Turn off all LEDs before sleep
    led_red.off()
    led_green.off()
    led_blue.off()
    
    # Enter light sleep mode
    # Light sleep maintains RAM and can be woken by RTC alarm
    machine.lightsleep()
    
    # Code execution resumes here after wake-up
    time_after_sleep = time.ticks_ms()
    sleep_duration = time_after_sleep - time_before_sleep
    
    # Wake-up indication
    print_status("=" * 50)
    print_status("WOKE UP FROM LIGHT SLEEP!")
    print_status(f"Sleep duration: {sleep_duration} ms")
    print_status("=" * 50)
    
    # Blink all LEDs to indicate wake-up
    for _ in range(5):
        led_red.on()
        led_green.on()
        led_blue.on()
        time.sleep(0.1)
        led_red.off()
        led_green.off()
        led_blue.off()
        time.sleep(0.1)
    
    return True

def test_deep_sleep():
    """Test entering deep sleep mode (more power saving, but loses RAM state)"""
    print_status("=" * 50)
    print_status("Testing Deep Sleep Mode")
    print_status("=" * 50)
    print_status("WARNING: Deep sleep will reset the module!")
    print_status("Code after deepsleep() will not execute")
    print_status("=" * 50)
    
    # Blink blue LED
    blink_led(led_blue, 3, 0.2)
    
    # Set RTC alarm for wake-up
    rtc.wakeup(10000)  # Wake up after 10 seconds
    print_status("RTC alarm set for 10 seconds")
    print_status("Entering deep sleep in 2 seconds...")
    time.sleep(2)
    
    print_status("Entering deep sleep mode NOW...")
    print_status("Module will reset after wake-up")
    
    # Turn off all LEDs
    led_red.off()
    led_green.off()
    led_blue.off()
    
    # Enter deep sleep mode
    # Deep sleep loses RAM state, module will reset on wake-up
    machine.deepsleep()

def main():
    """Main test function"""
    print_status("OpenMV RT1062 Low Power Mode Test")
    print_status("Board: OpenMV RT1062")
    print_status("Firmware: MicroPython")
    print_status("")
    
    try:
        # Test light sleep (recommended for most use cases)
        print_status("Test 1: Light Sleep Mode")
        success = test_light_sleep()
        
        if success:
            print_status("Light sleep test completed successfully!")
            time.sleep(2)
            
            # Optional: Uncomment to test deep sleep
            # Note: Deep sleep will reset the module, so code after it won't run
            # print_status("")
            # print_status("Test 2: Deep Sleep Mode")
            # test_deep_sleep()
        
        print_status("")
        print_status("All tests completed!")
        print_status("Module is ready for use")
        
        # Keep green LED on to indicate success
        led_green.on()
        
    except Exception as e:
        print_status(f"ERROR: {e}")
        # Blink red LED to indicate error
        for _ in range(10):
            led_red.on()
            time.sleep(0.2)
            led_red.off()
            time.sleep(0.2)
        raise

# Run the test
if __name__ == "__main__":
    main()

