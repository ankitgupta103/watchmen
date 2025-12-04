"""
OpenMV RT1062 Deep Sleep Mode with PIR Sensor on P11

IMPORTANT: Deep Sleep Hardware Limitation
- ONLY P11 pin can wake from deep sleep on RT1062 (hardware limitation)
- P11 automatically enables wake-up on RISING edge (0->1 transition)
- In deep sleep, everything is turned off except wake-up detection on P11
- Power consumption: < 30µA (when powered via battery connector)
- This is how it achieves ultra-low power - literally everything but a small part of silicon is off

Hardware Setup:
- PIR sensor output connected to P11 pin
- PIR outputs: 1 = motion detected (HIGH), 0 = no motion (LOW)
- When PIR detects motion, it sends HIGH to P11, triggering wake-up
- Power via battery connector for lowest power consumption (< 30µA)

Note: reset_cause() may not reliably indicate deep sleep wake-up on RT1062
"""

import time
import machine

# ==================== CONFIGURATION ====================
PIR_PIN = 'P11'  # MUST be P11 - only pin that can wake from deep sleep
LED_PIN = "LED_B"  # Blue LED (adjust if needed: LED_R, LED_G, LED_B)

# ==================== INITIALIZATION ====================
# Initialize PIR sensor pin as input
# P11 wakes on RISING edge automatically in deep sleep
pir = machine.Pin(PIR_PIN, machine.Pin.IN, machine.Pin.PULL_DOWN)

# Initialize LED
try:
    led = machine.Pin(LED_PIN, machine.Pin.OUT)
except:
    # Fallback LED names
    try:
        led = machine.Pin("LED_BLUE", machine.Pin.OUT)
    except:
        led = None
        print("LED not available")

# Turn off LED initially
if led:
    led.off()

# ==================== STATE MANAGEMENT ====================
# Save state to flash (survives deep sleep reset)
STATE_FILE = '/flash/pir_state.txt'

def save_wake_count(count):
    """Save wake count to flash"""
    try:
        with open(STATE_FILE, 'w') as f:
            f.write(str(count))
        return True
    except:
        return False

def load_wake_count():
    """Load wake count from flash"""
    try:
        with open(STATE_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

# ==================== MAIN APPLICATION ====================
def main():
    """Main application - deep sleep with PIR wake-up on P11"""
    
    print("=" * 60)
    print("OpenMV RT1062 Deep Sleep with PIR on P11")
    print("=" * 60)
    print(f"PIR Pin: {PIR_PIN} (ONLY pin that can wake from deep sleep)")
    print(f"Power consumption in deep sleep: < 30µA")
    print(f"Wake-up: RISING edge on P11 (PIR motion detected)")
    print("=" * 60)
    
    # Load previous wake count
    wake_count = load_wake_count()
    wake_count += 1
    save_wake_count(wake_count)
    
    print(f"\nWoke up! (Wake count: {wake_count})")
    print("PIR motion detected - Processing...")
    
    # Turn ON LED to indicate we're awake
    if led:
        led.on()
        print("LED ON - System awake")
    
    # ============================================================
    # YOUR ACTIVE MODE CODE HERE
    # This is where you process the motion detection event
    # Examples:
    # - Take a picture
    # - Read sensors
    # - Send data
    # - Process data
    # ============================================================
    
    # Example: Blink LED to show activity
    if led:
        for _ in range(3):
            led.on()
            time.sleep_ms(200)
            led.off()
            time.sleep_ms(200)
        led.on()  # Keep LED on while processing
    
    # Simulate processing time (replace with your actual code)
    print("Processing motion event...")
    time.sleep_ms(500)  # Your processing code here
    
    # ============================================================
    # END OF ACTIVE MODE CODE
    # ============================================================
    
    print("\nProcessing complete. Preparing for deep sleep...")
    
    # Turn OFF LED before entering deep sleep
    if led:
        led.off()
        print("LED OFF - Entering deep sleep")
    
    # Small delay to ensure serial output is sent
    time.sleep_ms(100)
    
    print("=" * 60)
    print("Entering DEEP SLEEP mode...")
    print("Power consumption: < 30µA")
    print("Wake-up: PIR motion on P11 (RISING edge)")
    print("=" * 60)
    print()
    
    # Enter deep sleep
    # Module will RESET when P11 goes HIGH (PIR detects motion)
    # Code will start from beginning after wake-up
    machine.deepsleep()
    
    # This code will NOT execute after deep sleep
    # (module resets, so execution starts from beginning)
    print("This should never print (module resets after deep sleep)")

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        # Turn off LED on error
        if led:
            led.off()
        raise

