"""
SX1262 Basic Mode Switch Test - No Configuration
Tests mode switching without full configuration
"""

from machine import SPI, Pin
import time

# Hardware
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)

# SX1262 Command Opcodes
CMD_SET_STANDBY = 0x80
CMD_SET_REGULATOR_MODE = 0x96
CMD_GET_STATUS = 0xC0

# Mode names
modes = {0: "STDBY_RC", 1: "STDBY_XOSC", 2: "FS", 3: "RX", 4: "TX"}

def wait_busy(timeout_ms=1000):
    """Wait for BUSY pin to go LOW"""
    start = time.ticks_ms()
    while busy.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_us(10)
    return True

def send_command(cmd, data=None):
    """Send command to SX1262"""
    if not wait_busy():
        return False
    cs.value(0)
    spi.write(bytes([cmd]))
    if data:
        spi.write(data)
    cs.value(1)
    return wait_busy()

def get_status():
    """Get chip status"""
    if not wait_busy():
        return None
    cs.value(0)
    spi.write(bytes([CMD_GET_STATUS]))
    status_byte = bytearray(1)
    dummy = bytes([0x00])
    spi.write_readinto(dummy, status_byte)
    cs.value(1)
    wait_busy()
    return status_byte[0]

def get_chip_mode():
    """Get chip mode from status byte"""
    status = get_status()
    if status is None:
        return None, None
    # Try different decoding methods
    mode1 = (status >> 1) & 0x07  # Bits [3:1] - supposed to be correct
    mode2 = (status >> 4) & 0x03  # Bits [5:4] - old method
    mode3 = (status >> 6) & 0x03  # Bits [7:6] - wrong method
    return status, (mode1, mode2, mode3)

def set_standby(mode):
    """Set standby mode (0=RC, 1=XOSC)"""
    return send_command(CMD_SET_STANDBY, bytes([mode]))

# ============================================================================
# Test
# ============================================================================

print("=" * 60)
print("SX1262 Basic Mode Switch Test")
print("=" * 60)

# Initialize
print("\n[1] Resetting chip...")
reset.value(0)
time.sleep_ms(10)
reset.value(1)
time.sleep_ms(10)
if wait_busy():
    print("    ✓ Reset complete")
else:
    print("    ✗ Reset failed - BUSY stuck")
    exit()

# Check initial status
print("\n[Initial] Checking status after reset...")
status, (mode1, mode2, mode3) = get_chip_mode()
if status:
    print(f"  Status: 0x{status:02X} = 0b{status:08b}")
    print(f"  Mode [3:1]: {mode1}, Mode [5:4]: {mode2}")

# Set regulator mode (required for proper operation)
print("\n[Init] Setting regulator mode...")
if send_command(CMD_SET_REGULATOR_MODE, bytes([0x01])):  # DC-DC enabled
    print("    ✓ Regulator mode set")
    time.sleep_ms(5)
else:
    print("    ✗ Failed to set regulator mode")

# Test mode switching
print("\n[2] Testing Mode Switches...")
print("-" * 60)

# Test 1: STDBY_RC
print("\n[Test 1] Switch to STDBY_RC...")
print(f"  BUSY before: {busy.value()}")
if set_standby(0):
    time.sleep_ms(20)  # Longer delay
    status, (mode1, mode2, mode3) = get_chip_mode()
    if status is None:
        print("  ✗ FAIL - Could not read status")
    else:
        print(f"  Status byte: 0x{status:02X} = 0b{status:08b}")
        print(f"  Mode [3:1]: {mode1} ({modes.get(mode1, 'INVALID')})")
        print(f"  Mode [5:4]: {mode2} ({modes.get(mode2, 'INVALID')})")
        print(f"  Mode [7:6]: {mode3} ({modes.get(mode3, 'INVALID')})")
        if mode1 == 0 or mode2 == 0:
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
else:
    print("  ✗ FAIL - Command timeout")

# Test 2: STDBY_XOSC
print("\n[Test 2] Switch to STDBY_XOSC...")
print(f"  BUSY before: {busy.value()}")
if set_standby(1):
    time.sleep_ms(20)
    status, (mode1, mode2, mode3) = get_chip_mode()
    if status is None:
        print("  ✗ FAIL - Could not read status")
    else:
        print(f"  Status byte: 0x{status:02X} = 0b{status:08b}")
        print(f"  Mode [3:1]: {mode1} ({modes.get(mode1, 'INVALID')})")
        print(f"  Mode [5:4]: {mode2} ({modes.get(mode2, 'INVALID')})")
        if mode1 == 1 or mode2 == 1:
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
else:
    print("  ✗ FAIL - Command timeout")

# Test 3: Back to STDBY_RC
print("\n[Test 3] Switch back to STDBY_RC...")
print(f"  BUSY before: {busy.value()}")
if set_standby(0):
    time.sleep_ms(20)
    status, (mode1, mode2, mode3) = get_chip_mode()
    if status is None:
        print("  ✗ FAIL - Could not read status")
    else:
        print(f"  Status byte: 0x{status:02X} = 0b{status:08b}")
        print(f"  Mode [3:1]: {mode1} ({modes.get(mode1, 'INVALID')})")
        print(f"  Mode [5:4]: {mode2} ({modes.get(mode2, 'INVALID')})")
        if mode1 == 0 or mode2 == 0:
            print("  ✓ PASS")
        else:
            print("  ✗ FAIL")
else:
    print("  ✗ FAIL - Command timeout")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

