"""
OpenMV RT1062 Deep Sleep with External Interrupt Wake-up

Optimal implementation for very low power consumption (< 30µA) with
external interrupt-based wake-up.

Features:
- Deep sleep mode for minimal power consumption
- External interrupt wake-up (GPIO pin)
- State preservation using flash memory
- Automatic re-entry into deep sleep after processing
- Power consumption: < 30µA in deep sleep (when powered via battery connector)

Hardware Setup:
- Connect external trigger (button/sensor) to a GPIO pin (e.g., P4)
- Connect to GND for falling edge trigger, or use pull-up for rising edge
- Power via battery connector for lowest power consumption

GPIO Pins for Deep Sleep Wake-up:
- ⚠️ ONLY P11 can wake from deep sleep (hardware limitation)
- P11 wakes on RISING edge (0->1 transition) - hardcoded in firmware
- Other GPIO pins will NOT wake from deep sleep
- For other pins, use low-power polling instead of deep sleep
"""

import time
import machine

# Configuration
# ⚠️ IMPORTANT: On OpenMV RT1062, ONLY P11 can wake from deep sleep!
# If you use any other pin, deep sleep wake-up will NOT work.
WAKEUP_PIN = 'P11'  # MUST be P11 for deep sleep wake-up (hardware limitation)
# P11 automatically wakes on RISING edge (hardcoded in firmware)
WAKEUP_EDGE = machine.Pin.IRQ_RISING  # P11 wakes on RISING edge only

# Initialize LEDs (turn off for power saving)
# OpenMV RT1062 uses LED_R, LED_G, LED_B
try:
    led_red = machine.Pin("LED_R", machine.Pin.OUT)
    led_green = machine.Pin("LED_G", machine.Pin.OUT)
    led_blue = machine.Pin("LED_B", machine.Pin.OUT)
except:
    # Fallback if LED names differ - adjust pin names as needed for your board
    led_red = machine.Pin("LED_RED", machine.Pin.OUT)
    led_green = machine.Pin("LED_GREEN", machine.Pin.OUT)
    led_blue = machine.Pin("LED_BLUE", machine.Pin.OUT)

# Turn off all LEDs initially
led_red.off()
led_green.off()
led_blue.off()

def save_state_to_flash(data):
    """Save state data to flash memory (persists across deep sleep)"""
    try:
        # Open file in append mode (or create if doesn't exist)
        with open('/flash/state.txt', 'w') as f:
            f.write(str(data))
        return True
    except Exception as e:
        print(f"Error saving state: {e}")
        return False

def load_state_from_flash():
    """Load state data from flash memory"""
    try:
        with open('/flash/state.txt', 'r') as f:
            data = f.read()
            return int(data) if data.isdigit() else 0
    except:
        return 0  # Default value if file doesn't exist

def setup_external_interrupt(pin_name, edge):
    """
    Configure GPIO pin as external interrupt wake-up source
    
    Args:
        pin_name: Pin name (e.g., 'P4')
        edge: Interrupt edge (machine.Pin.IRQ_RISING, machine.Pin.IRQ_FALLING, or both)
    """
    wakeup_pin = machine.Pin(pin_name, machine.Pin.IN, machine.Pin.PULL_UP)
    
    # Configure as wake-up source
    # In deep sleep, the pin state change will wake the module
    wakeup_pin.irq(trigger=edge, handler=None)  # Handler not needed for deep sleep
    
    print(f"External interrupt configured on {pin_name}")
    print(f"Trigger: {'Rising' if edge & machine.Pin.IRQ_RISING else ''} "
          f"{'Falling' if edge & machine.Pin.IRQ_FALLING else ''}")
    
    return wakeup_pin

def enter_deep_sleep():
    """Enter deep sleep mode - module will reset on wake-up"""
    print("=" * 60)
    print("Entering DEEP SLEEP mode...")
    print(f"Power consumption: < 30µA (when powered via battery)")
    print(f"Wake-up: External interrupt on {WAKEUP_PIN}")
    print("=" * 60)
    
    # Turn off all LEDs
    led_red.off()
    led_green.off()
    led_blue.off()
    
    # Optional: Disable camera sensor for additional power savings
    # import sensor
    # sensor.shutdown()
    
    # Save current state before sleep
    wake_count = load_state_from_flash()
    wake_count += 1
    save_state_to_flash(wake_count)
    print(f"Wake count saved: {wake_count}")
    
    # Small delay to ensure serial output is sent
    time.sleep_ms(100)
    
    # Enter deep sleep
    # Module will reset when external interrupt occurs
    machine.deepsleep()

def handle_wakeup():
    """Handle wake-up from deep sleep"""
    # Check if we woke from deep sleep
    # Define reset cause constant (fallback if not available in machine module)
    try:
        DEEPSLEEP_RESET = machine.DEEPSLEEP_RESET
    except AttributeError:
        DEEPSLEEP_RESET = 4  # Common value for deep sleep reset in MicroPython
    
    if machine.reset_cause() == DEEPSLEEP_RESET:
        print("=" * 60)
        print("WOKE UP FROM DEEP SLEEP!")
        print(f"Wake-up cause: External interrupt on {WAKEUP_PIN}")
        print("=" * 60)
        
        # Load saved state
        wake_count = load_state_from_flash()
        print(f"Total wake-ups: {wake_count}")
        
        # Visual indication of wake-up
        for _ in range(3):
            led_green.on()
            time.sleep_ms(100)
            led_green.off()
            time.sleep_ms(100)
        
        return True
    else:
        print("Normal boot (not from deep sleep)")
        return False

def process_wakeup_event():
    """
    Process the event that caused wake-up
    This is where you put your main application logic
    """
    print("Processing wake-up event...")
    
    # Example: Read sensor, take picture, send data, etc.
    # led_blue.on()
    # time.sleep_ms(500)
    # led_blue.off()
    
    # For demonstration, just wait a bit
    time.sleep_ms(500)
    
    print("Event processing complete")

def main():
    """Main application loop"""
    print("\n" + "=" * 60)
    print("OpenMV RT1062 Deep Sleep with External Interrupt")
    print("=" * 60)
    print(f"Wake-up pin: {WAKEUP_PIN}")
    print(f"Target power: < 30µA in deep sleep")
    print("=" * 60 + "\n")
    
    # Handle wake-up
    woke_from_sleep = handle_wakeup()
    
    if woke_from_sleep:
        # Process the wake-up event
        process_wakeup_event()
    
    # Setup external interrupt for next sleep cycle
    wakeup_pin = setup_external_interrupt(WAKEUP_PIN, WAKEUP_EDGE)
    
    # Optional: Also set RTC alarm as backup wake-up (uncomment if needed)
    # rtc = machine.RTC()
    # rtc.wakeup(60000)  # Wake up after 60 seconds if no interrupt
    
    print("\nPreparing to enter deep sleep...")
    print("Waiting 2 seconds (you can trigger interrupt now to test)...")
    time.sleep(2)
    
    # Enter deep sleep
    # After wake-up, module will reset and this code will run again
    enter_deep_sleep()
    
    # This code will NOT execute after deep sleep
    # (module resets, so execution starts from beginning)
    print("This should never print (module resets after deep sleep)")

# Run main
if __name__ == "__main__":
    main()

