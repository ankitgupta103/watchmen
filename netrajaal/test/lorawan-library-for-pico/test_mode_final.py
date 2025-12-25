"""
SX1262 Mode Switch Test - Complete Initialization
Tests mode switching with proper initialization sequence
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
CMD_SET_DIO3_AS_TCXO_CTRL = 0x97
CMD_SET_DIO2_AS_RF_SWITCH_CTRL = 0x9D
CMD_GET_STATUS = 0xC0
CMD_GET_DEVICE_ERRORS = 0x17
CMD_CLEAR_DEVICE_ERRORS = 0x07

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

def get_device_errors():
    """Get device errors"""
    if not wait_busy():
        return None
    cs.value(0)
    spi.write(bytes([CMD_GET_DEVICE_ERRORS]))
    response = bytearray(3)
    spi.write_readinto(bytes([0x00, 0x00, 0x00]), response)
    cs.value(1)
    wait_busy()
    return (response[1] << 8) | response[2]

def clear_device_errors():
    """Clear device errors"""
    return cmd_write(CMD_CLEAR_DEVICE_ERRORS, bytes([0x00, 0x00]))

def get_mode():
    status = get_status()
    if status is None:
        return None, None
    # Chip mode is in bits [3:1]
    mode = (status >> 1) & 0x07
    return status, mode

print("=" * 60)
print("SX1262 Complete Mode Switch Test")
print("=" * 60)

# Step 1: Reset
print("\n[1] Reset...")
reset.value(0)
time.sleep_ms(10)
reset.value(1)
time.sleep_ms(10)
wait_busy()
print("  ✓ Reset done")

# Step 2: Check initial status and errors
print("\n[2] Initial check...")
status, mode = get_mode()
errors = get_device_errors()
print(f"  Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")
if errors is not None:
    print(f"  Errors: 0x{errors:04X}")
    if errors != 0:
        print("  Clearing errors...")
        clear_device_errors()

# Step 3: Initialize properly
print("\n[3] Initialization sequence...")

# 3.1: Set Standby RC
print("  3.1 Set Standby RC...")
if cmd_write(CMD_SET_STANDBY, bytes([0x00])):
    time.sleep_ms(10)
    status, mode = get_mode()
    print(f"    Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")

# 3.2: Set Regulator Mode
print("  3.2 Set Regulator Mode (DC-DC)...")
if cmd_write(CMD_SET_REGULATOR_MODE, bytes([0x01])):
    print("    ✓ Done")
    time.sleep_ms(5)
    status, mode = get_mode()
    print(f"    Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")

# 3.3: Configure TCXO (DIO3)
print("  3.3 Configure TCXO (DIO3)...")
# Voltage: 0x01 = 1.7V, Delay: 5ms = 0x0140
if cmd_write(CMD_SET_DIO3_AS_TCXO_CTRL, bytes([0x01, 0x01, 0x40])):
    print("    ✓ Done")
    time.sleep_ms(5)  # Allow TCXO to stabilize

# 3.4: Configure RF Switch (DIO2)
print("  3.4 Configure RF Switch (DIO2)...")
if cmd_write(CMD_SET_DIO2_AS_RF_SWITCH_CTRL, bytes([0x01])):
    print("    ✓ Done")

# Check status after initialization
status, mode = get_mode()
errors = get_device_errors()
print(f"\n  Status after init: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")
if errors is not None:
    print(f"  Errors: 0x{errors:04X}")

# Step 4: Test mode switching
print("\n[4] Testing Mode Switches...")
print("-" * 60)

# Test STDBY_RC
print("\n[Test 1] Switch to STDBY_RC...")
if cmd_write(CMD_SET_STANDBY, bytes([0x00])):
    time.sleep_ms(20)
    status, mode = get_mode()
    errors = get_device_errors()
    print(f"  Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")
    if errors is not None and errors != 0:
        print(f"  Errors: 0x{errors:04X}")
    if mode == 0:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")

# Test STDBY_XOSC
print("\n[Test 2] Switch to STDBY_XOSC...")
if cmd_write(CMD_SET_STANDBY, bytes([0x01])):
    time.sleep_ms(20)
    status, mode = get_mode()
    errors = get_device_errors()
    print(f"  Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")
    if errors is not None and errors != 0:
        print(f"  Errors: 0x{errors:04X}")
    if mode == 1:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")

# Test back to STDBY_RC
print("\n[Test 3] Switch back to STDBY_RC...")
if cmd_write(CMD_SET_STANDBY, bytes([0x00])):
    time.sleep_ms(20)
    status, mode = get_mode()
    errors = get_device_errors()
    print(f"  Status: 0x{status:02X}, Mode: {mode} ({modes.get(mode, 'INVALID')})")
    if errors is not None and errors != 0:
        print(f"  Errors: 0x{errors:04X}")
    if mode == 0:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

