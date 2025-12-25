"""
SX1262 SetStandby Command Test
Tests if SetStandby command is actually working
"""

from machine import SPI, Pin
import time

# Hardware
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)

# Commands
CMD_SET_STANDBY = 0x80
CMD_GET_STATUS = 0xC0
CMD_SET_REGULATOR_MODE = 0x96
CMD_CLEAR_DEVICE_ERRORS = 0x07
CMD_GET_DEVICE_ERRORS = 0x17

def wait_busy(timeout_ms=1000):
    start = time.ticks_ms()
    while busy.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_us(10)
    return True

def cmd_write(cmd, data=None):
    if not wait_busy():
        print(f"    BUSY timeout before command 0x{cmd:02X}")
        return False
    cs.value(0)
    spi.write(bytes([cmd]))
    if data:
        spi.write(data)
    cs.value(1)
    if not wait_busy():
        print(f"    BUSY timeout after command 0x{cmd:02X}")
        return False
    return True

def get_status():
    if not wait_busy():
        return None
    cs.value(0)
    spi.write(bytes([CMD_GET_STATUS]))
    status = bytearray(1)
    spi.write_readinto(bytes([0x00]), status)
    cs.value(1)
    wait_busy()
    return status[0]

def get_device_errors():
    if not wait_busy():
        return None
    cs.value(0)
    spi.write(bytes([CMD_GET_DEVICE_ERRORS]))
    response = bytearray(3)
    spi.write_readinto(bytes([0x00, 0x00, 0x00]), response)
    cs.value(1)
    wait_busy()
    return (response[1] << 8) | response[2]

def get_mode(status):
    # Try all decoding methods
    mode1 = (status >> 1) & 0x07  # Bits [3:1]
    mode2 = (status >> 4) & 0x03  # Bits [5:4]
    mode3 = (status >> 6) & 0x03  # Bits [7:6]
    return mode1, mode2, mode3

print("=" * 60)
print("SX1262 SetStandby Command Test")
print("=" * 60)

# Reset
print("\n[1] Reset...")
reset.value(0)
time.sleep_ms(10)
reset.value(1)
time.sleep_ms(10)
wait_busy()

# Clear errors
print("\n[2] Clear errors...")
errors = get_device_errors()
print(f"  Initial errors: 0x{errors:04X if errors is not None else 'NONE'}")
if errors is not None and errors != 0:
    cmd_write(CMD_CLEAR_DEVICE_ERRORS, bytes([0x00, 0x00]))
    time.sleep_ms(10)
    errors = get_device_errors()
    print(f"  Errors after clear: 0x{errors:04X if errors is not None else 'NONE'}")

# Set regulator mode
print("\n[3] Set regulator mode...")
cmd_write(CMD_SET_REGULATOR_MODE, bytes([0x01]))

# Test SetStandby with detailed logging
print("\n[4] Testing SetStandby(0) - STDBY_RC...")
status_before = get_status()
mode1_b, mode2_b, mode3_b = get_mode(status_before)
print(f"  Before: Status=0x{status_before:02X}, Mode[3:1]={mode1_b}, Mode[5:4]={mode2_b}")

# Send command
print("  Sending SET_STANDBY(0)...")
if cmd_write(CMD_SET_STANDBY, bytes([0x00])):
    print("  Command sent successfully")
    time.sleep_ms(50)  # Longer delay to allow mode change
    status_after = get_status()
    mode1_a, mode2_a, mode3_a = get_mode(status_after)
    print(f"  After:  Status=0x{status_after:02X}, Mode[3:1]={mode1_a}, Mode[5:4]={mode2_a}")
    
    if status_before != status_after:
        print("  ✓ Status byte changed")
    else:
        print("  ✗ Status byte unchanged")
    
    if mode1_a == 0:
        print("  ✓ Mode changed to STDBY_RC")
    elif mode1_b == mode1_a:
        print("  ✗ Mode did not change (still mode {})".format(mode1_a))
    else:
        print(f"  ⚠ Mode changed but to {mode1_a} (not 0)")

# Test SetStandby(1) 
print("\n[5] Testing SetStandby(1) - STDBY_XOSC...")
status_before = get_status()
mode1_b, mode2_b, mode3_b = get_mode(status_before)
print(f"  Before: Status=0x{status_before:02X}, Mode[3:1]={mode1_b}")

if cmd_write(CMD_SET_STANDBY, bytes([0x01])):
    print("  Command sent successfully")
    time.sleep_ms(50)
    status_after = get_status()
    mode1_a, mode2_a, mode3_a = get_mode(status_after)
    print(f"  After:  Status=0x{status_after:02X}, Mode[3:1]={mode1_a}")
    
    if mode1_a == 1:
        print("  ✓ Mode changed to STDBY_XOSC")
    elif mode1_b == mode1_a:
        print("  ✗ Mode did not change")
    else:
        print(f"  ⚠ Mode changed but to {mode1_a} (not 1)")

# Check errors after commands
errors = get_device_errors()
print(f"\n[6] Final errors: 0x{errors:04X if errors is not None else 'NONE'}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

