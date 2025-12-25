"""
SX1262 Mode Switch Test with Minimal Initialization
Tests if basic initialization is needed for mode switching
"""

from machine import SPI, Pin
import time

# Hardware
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)

# SX1262 Commands
CMD_SET_STANDBY = 0x80
CMD_SET_REGULATOR_MODE = 0x96
CMD_GET_STATUS = 0xC0

modes = {0: "STDBY_RC", 1: "STDBY_XOSC", 2: "FS", 3: "RX", 4: "TX"}

def wait_busy(timeout_ms=1000):
    start = time.ticks_ms()
    while busy.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_us(10)
    return True

def cmd_write(cmd, data=None):
    if not wait_busy():
        return False
    cs.value(0)
    spi.write(bytes([cmd]))
    if data:
        spi.write(data)
    cs.value(1)
    return wait_busy()

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

def get_mode():
    status = get_status()
    if status is None:
        return None
    # Try different decoding methods
    mode1 = (status >> 1) & 0x07  # Bits [3:1]
    mode2 = (status >> 4) & 0x03  # Bits [5:4] (old method)
    mode3 = (status >> 6) & 0x03  # Bits [7:6] (wrong method)
    return status, mode1, mode2, mode3

print("=" * 60)
print("SX1262 Mode Switch Test with Initialization")
print("=" * 60)

# Reset
print("\n[1] Reset...")
reset.value(0)
time.sleep_ms(10)
reset.value(1)
time.sleep_ms(10)
wait_busy()
print("  ✓ Reset done")

# Check initial status
print("\n[2] Initial status after reset...")
status, mode1, mode2, mode3 = get_mode()
print(f"  Status byte: 0x{status:02X} = 0b{status:08b}")
print(f"  Mode (bits[3:1]): {mode1} ({modes.get(mode1, 'INVALID')})")
print(f"  Mode (bits[5:4]): {mode2} ({modes.get(mode2, 'INVALID')})")
print(f"  Mode (bits[7:6]): {mode3} ({modes.get(mode3, 'INVALID')})")

# Try minimal initialization
print("\n[3] Setting regulator mode...")
if cmd_write(CMD_SET_REGULATOR_MODE, bytes([0x01])):
    print("  ✓ Regulator mode set")
    status, mode1, mode2, mode3 = get_mode()
    print(f"  Status: 0x{status:02X}, Mode: {mode1}")

# Test STDBY_RC
print("\n[4] Testing STDBY_RC...")
print(f"  BUSY: {busy.value()}")
if cmd_write(CMD_SET_STANDBY, bytes([0x00])):
    time.sleep_ms(20)  # Longer delay
    status, mode1, mode2, mode3 = get_mode()
    print(f"  Status: 0x{status:02X}")
    print(f"  Mode (bits[3:1]): {mode1} = {modes.get(mode1, 'INVALID')}")
    print(f"  Mode (bits[5:4]): {mode2} = {modes.get(mode2, 'INVALID')}")
    if mode1 == 0 or mode2 == 0:
        print("  ✓ STDBY_RC confirmed")
    else:
        print("  ✗ Not in STDBY_RC")

# Test STDBY_XOSC
print("\n[5] Testing STDBY_XOSC...")
print(f"  BUSY: {busy.value()}")
if cmd_write(CMD_SET_STANDBY, bytes([0x01])):
    time.sleep_ms(20)
    status, mode1, mode2, mode3 = get_mode()
    print(f"  Status: 0x{status:02X}")
    print(f"  Mode (bits[3:1]): {mode1} = {modes.get(mode1, 'INVALID')}")
    print(f"  Mode (bits[5:4]): {mode2} = {modes.get(mode2, 'INVALID')}")
    if mode1 == 1 or mode2 == 1:
        print("  ✓ STDBY_XOSC confirmed")
    else:
        print("  ✗ Not in STDBY_XOSC")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

