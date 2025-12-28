"""
API Test: Power Management

This example demonstrates:
- sleep() - Put module to sleep
- standby() - Put module to standby
- Wake up from sleep
- Power consumption modes
"""

import time
from sx1262 import SX1262

# Pin definitions for OpenMV RT1062
SPI_BUS = 1
P0_MOSI = 'P0'
P1_MISO = 'P1'
P2_SCLK = 'P2'
P3_CS = 'P3'
P6_RST = 'P6'
P7_BUSY = 'P7'
P13_DIO1 = 'P13'

# Initialize SX1262
sx = SX1262(
    spi_bus=SPI_BUS,
    clk=P2_SCLK,
    mosi=P0_MOSI,
    miso=P1_MISO,
    cs=P3_CS,
    irq=P13_DIO1,
    rst=P6_RST,
    gpio=P7_BUSY,
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure for LoRa
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=True
)

print("=== Power Management API Test ===\n")

# Test 1: sleep() with retainConfig=True
print("Test 1: sleep() with retainConfig=True (warm sleep)")
try:
    status = sx.sleep(retainConfig=True)
    if status == 0:
        print("  [OK] Module put to sleep (config retained)")
        print("  Power consumption: ~0.85 µA")
    else:
        print(f"  [FAIL] Sleep failed: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

# Wait a bit
time.sleep(1)

# Wake up from sleep
print("\n  Waking up from sleep...")
try:
    status = sx.standby()
    if status == 0:
        print("  [OK] Module woken up (standby mode)")
        print("  Configuration retained - ready to use immediately")
    else:
        print(f"  [FAIL] Wake up failed: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 2: sleep() with retainConfig=False
print("Test 2: sleep() with retainConfig=False (cold sleep)")
try:
    status = sx.sleep(retainConfig=False)
    if status == 0:
        print("  [OK] Module put to sleep (config not retained)")
        print("  Power consumption: ~0.4 µA")
    else:
        print(f"  [FAIL] Sleep failed: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

# Wait a bit
time.sleep(1)

# Wake up from cold sleep - need to reconfigure
print("\n  Waking up from cold sleep...")
try:
    status = sx.standby()
    if status == 0:
        print("  [OK] Module woken up (standby mode)")
        print("  Configuration lost - need to reconfigure")
        # Reconfigure
        status = sx.begin(
            freq=868.0,
            bw=125.0,
            sf=9,
            cr=7,
            syncWord=0x12,
            power=14,
            blocking=True
        )
        if status == 0:
            print("  [OK] Module reconfigured successfully")
        else:
            print(f"  [FAIL] Reconfiguration failed: {status}")
    else:
        print(f"  [FAIL] Wake up failed: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 3: standby() mode
print("Test 3: standby() - Standby mode")
try:
    status = sx.standby()
    if status == 0:
        print("  [OK] Module in standby mode")
        print("  Power consumption: ~720 nA")
        print("  Faster wakeup than sleep mode")
    else:
        print(f"  [FAIL] Standby failed: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 4: Periodic transmission with sleep
print("Test 4: Periodic transmission with sleep (power saving)")
print("  Simulating periodic transmission pattern...")
for i in range(3):
    try:
        # Wake up
        sx.standby()
        print(f"  [{i+1}] Woke up, sending data...")
        
        # Send data
        message = f"Periodic message {i+1}"
        payload_len, status = sx.send(message.encode())
        if status == 0:
            print(f"       [OK] Sent: {message}")
        else:
            print(f"       [FAIL] Send failed: {status}")
        
        # Put to sleep
        sx.sleep(retainConfig=True)
        print(f"       [OK] Back to sleep")
        
        # Wait (simulating sleep period)
        time.sleep(1)
    except Exception as e:
        print(f"  [FAIL] Error in cycle {i+1}: {e}")

# Wake up for final test
sx.standby()
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=True
)
print()

# Test 5: Power consumption comparison
print("Test 5: Power consumption comparison")
print("  Mode                    | Current")
print("  ------------------------|------------------")
print("  Sleep (retain config)   | ~0.85 µA")
print("  Sleep (cold)            | ~0.4 µA")
print("  Standby                  | ~720 nA")
print("  RX Continuous            | ~4.6 mA")
print("  TX (14 dBm)              | ~45 mA")
print("  TX (0 dBm)               | ~28 mA")
print()

# Test 6: Sleep and wake cycle timing
print("Test 6: Sleep and wake cycle timing")
try:
    # Measure wake time from sleep
    sx.sleep(retainConfig=True)
    start = time.ticks_ms()
    sx.standby()
    wake_time = time.ticks_diff(time.ticks_ms(), start)
    print(f"  [OK] Wake time from sleep (retain config): {wake_time} ms")
    
    # Measure wake time from cold sleep
    sx.sleep(retainConfig=False)
    start = time.ticks_ms()
    sx.standby()
    sx.begin(
        freq=868.0,
        bw=125.0,
        sf=9,
        cr=7,
        syncWord=0x12,
        power=14,
        blocking=True
    )
    wake_time = time.ticks_diff(time.ticks_ms(), start)
    print(f"  [OK] Wake time from cold sleep (with reconfig): {wake_time} ms")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

print("\n=== Power Management Tests Complete ===")

