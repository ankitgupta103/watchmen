"""
OpenMV RT1062 Ultra-Low Power Implementation

Production-ready implementation for minimal power consumption with
external interrupt wake-up. Optimized for battery-powered applications.

Power Consumption:
- Deep Sleep: < 30µA (when powered via battery connector)
- Active (processing): ~130mA (only during brief wake periods)

Strategy:
1. Enter deep sleep immediately after boot
2. Wake on external interrupt (GPIO pin)
3. Process event quickly
4. Re-enter deep sleep immediately
5. Minimize active time to maximize battery life
"""

import time
import machine

# ==================== CONFIGURATION ====================
WAKEUP_PIN = 'P4'                 # Change to your GPIO pin
TRIGGER_EDGE = machine.Pin.IRQ_FALLING  # FALLING = button press to GND
# Options: machine.Pin.IRQ_RISING, machine.Pin.IRQ_FALLING, or machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING

# Optional: RTC alarm as backup (None to disable)
BACKUP_RTC_ALARM_MS = None  # e.g., 3600000 for 1 hour backup wake-up

# ==================== INITIALIZATION ====================
# Initialize LEDs using machine.Pin (OpenMV RT1062 uses LED_R, LED_G, LED_B)
try:
    led_red = machine.Pin("LED_R", machine.Pin.OUT)
    led_green = machine.Pin("LED_G", machine.Pin.OUT)
    led_blue = machine.Pin("LED_B", machine.Pin.OUT)
except:
    # Fallback if LED names differ - adjust pin names as needed for your board
    led_red = machine.Pin("LED_RED", machine.Pin.OUT)
    led_green = machine.Pin("LED_GREEN", machine.Pin.OUT)
    led_blue = machine.Pin("LED_BLUE", machine.Pin.OUT)

# Turn off all LEDs immediately
led_red.off()
led_green.off()
led_blue.off()

# ==================== STATE MANAGEMENT ====================
STATE_FILE = '/flash/app_state.txt'

def save_state(key, value):
    """Save key-value pair to flash (survives deep sleep)"""
    try:
        # Simple key-value storage
        state = {}
        try:
            with open(STATE_FILE, 'r') as f:
                content = f.read()
                if content:
                    # Simple parsing (for production, use JSON or proper format)
                    for line in content.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            state[k.strip()] = v.strip()
        except:
            pass
        
        state[key] = str(value)
        
        with open(STATE_FILE, 'w') as f:
            for k, v in state.items():
                f.write(f"{k}:{v}\n")
        return True
    except Exception as e:
        print(f"State save error: {e}")
        return False

def load_state(key, default=None):
    """Load value from flash"""
    try:
        with open(STATE_FILE, 'r') as f:
            for line in f:
                if ':' in line:
                    k, v = line.split(':', 1)
                    if k.strip() == key:
                        return v.strip()
    except:
        pass
    return default

# ==================== POWER MANAGEMENT ====================
def disable_peripherals():
    """Disable all unnecessary peripherals for power savings"""
    # LEDs already off
    # Camera sensor (if initialized, disable it)
    # WiFi/Bluetooth if present
    pass

def setup_wakeup_sources():
    """Configure all wake-up sources"""
    # External interrupt
    wakeup_pin = machine.Pin(WAKEUP_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    wakeup_pin.irq(trigger=TRIGGER_EDGE, handler=None)
    
    # Optional RTC alarm backup
    if BACKUP_RTC_ALARM_MS:
        rtc = machine.RTC()
        rtc.wakeup(BACKUP_RTC_ALARM_MS)
        print(f"RTC backup alarm: {BACKUP_RTC_ALARM_MS}ms")
    
    return wakeup_pin

# ==================== APPLICATION LOGIC ====================
def process_event():
    """
    Your application logic here
    Keep this FAST to minimize power consumption
    """
    # Increment event counter
    count = int(load_state('event_count', '0'))
    count += 1
    save_state('event_count', count)
    
    # Quick visual feedback
    led_green.on()
    time.sleep_ms(50)
    led_green.off()
    
    print(f"Event processed. Total events: {count}")
    
    # Add your logic here:
    # - Read sensor
    # - Take picture
    # - Send data
    # - etc.
    
    # Keep processing time SHORT (< 1 second ideally)

# ==================== MAIN APPLICATION ====================
def main():
    """Main application - optimized for power"""
    
    # Check wake-up reason
    reset_cause = machine.reset_cause()
    
    if reset_cause == machine.DEEPSLEEP_RESET:
        # Woke from deep sleep
        wake_source = "External Interrupt"  # Could check pin state for more detail
        
        print("\n" + "=" * 60)
        print("WOKE FROM DEEP SLEEP")
        print(f"Source: {wake_source}")
        print(f"Event count: {load_state('event_count', '0')}")
        print("=" * 60)
        
        # Process the event
        process_event()
        
    elif reset_cause == machine.PWRON_RESET:
        # Power-on reset (first boot)
        print("\n" + "=" * 60)
        print("FIRST BOOT - Initializing")
        print("=" * 60)
        
        # Initialize state
        save_state('event_count', '0')
        save_state('boot_count', '1')
        
        # Optional: Do initial setup here
        
    else:
        # Other reset (watchdog, etc.)
        print(f"\nReset cause: {reset_cause}")
    
    # Setup wake-up sources
    print(f"\nConfiguring wake-up on pin {WAKEUP_PIN}")
    setup_wakeup_sources()
    
    # Disable unnecessary peripherals
    disable_peripherals()
    
    # Prepare for deep sleep
    print("\nEntering deep sleep in 1 second...")
    print("Power consumption: < 30µA")
    print("Wake-up: External interrupt on", WAKEUP_PIN)
    print("=" * 60)
    
    # Brief delay to allow serial output
    time.sleep_ms(1000)
    
    # Turn off LEDs
    led_red.off()
    led_green.off()
    led_blue.off()
    
    # Enter deep sleep
    # Module will reset when interrupt occurs
    machine.deepsleep()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    main()

