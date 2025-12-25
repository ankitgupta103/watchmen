"""
SX1262 Simple Mode Switch Test
Minimal script to test mode switching only
"""

from machine import SPI, Pin
import time
from sx1262 import SX1262

# Hardware
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)

# Initialize
print("Initializing SX1262...")
radio = SX1262(spi, cs, busy, reset, dio1, freq=868000000)

# Minimal config
print("Configuring...")
radio.configure(frequency=868000000, sf=7, bw=7, cr=1, tx_power=14, preamble_length=12, payload_length=0)
print("Config done\n")

# Mode names
modes = {0: "STDBY_RC", 1: "STDBY_XOSC", 2: "FS", 3: "RX", 4: "TX"}

def get_mode():
    """Get current chip mode"""
    radio._wait_on_busy()
    mode = radio.get_chip_mode()
    return mode, modes.get(mode, f"UNK({mode})")

def test_mode(name, cmd, expected):
    """Test mode switch"""
    print(f"Test: {name}")
    print(f"  BUSY before: {radio.busy.value()}")
    cmd()
    print(f"  BUSY after: {radio.busy.value()}")
    time.sleep_ms(10)
    mode, mode_name = get_mode()
    print(f"  Mode: {mode_name} (expected: {modes[expected]})")
    if mode == expected:
        print(f"  ✓ PASS\n")
        return True
    else:
        print(f"  ✗ FAIL\n")
        return False

# Test sequence
print("=" * 50)
print("Mode Switch Test")
print("=" * 50)

test_mode("STDBY_RC", lambda: radio.set_standby(0), 0)
test_mode("STDBY_XOSC", lambda: radio.set_standby(1), 1)
test_mode("STDBY_RC again", lambda: radio.set_standby(0), 0)

# TX test
print("Test: TX Mode")
print(f"  BUSY before: {radio.busy.value()}")
radio.clear_device_errors()
radio.clear_irq_status(0xFFFF)
radio.write_buffer(0, b"TEST")
radio._write_register(0x0702, 4)
time.sleep_ms(1)
radio.set_tx(0)
print(f"  BUSY after SetTx: {radio.busy.value()}")
time.sleep_ms(20)
mode, mode_name = get_mode()
print(f"  Mode: {mode_name} (expected: TX)")
if mode == 4:
    print("  ✓ TX mode entered")
    # Wait for TX_DONE
    print("  Waiting for TX_DONE...")
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 3000:
        if radio.get_irq_status() & 0x0001:
            print(f"  ✓ TX_DONE after {time.ticks_diff(time.ticks_ms(), start)}ms")
            radio.clear_irq_status(0x0001)
            radio.set_standby(0)
            time.sleep_ms(5)
            mode, mode_name = get_mode()
            print(f"  Mode after TX: {mode_name}")
            break
        time.sleep_ms(10)
else:
    print(f"  ✗ TX mode not entered (mode={mode})")

print("\n" + "=" * 50)
print("Test Complete")
print("=" * 50)

