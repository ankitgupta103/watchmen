"""
SX1262 Mode Switch Test - Simple and Independent
Tests mode switching and verifies chip is in correct mode
"""

from machine import SPI, Pin
import time
from sx1262 import SX1262, SF_7, BW_125, CR_4_5

# ============================================================================
# Hardware Setup
# ============================================================================

spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)

# ============================================================================
# Initialize Radio
# ============================================================================

print("=" * 60)
print("SX1262 Mode Switch Test")
print("=" * 60)

radio = SX1262(spi, cs, busy, reset, dio1, freq=868000000)

# Configure radio (minimal config)
print("\n[1] Configuring radio...")
radio.configure(
    frequency=868000000,
    sf=SF_7,
    bw=BW_125,
    cr=CR_4_5,
    tx_power=14,
    preamble_length=12,
    payload_length=0
)
print("    ✓ Configuration complete")

# ============================================================================
# Mode Switch Test
# ============================================================================

def check_mode(expected_name, expected_value):
    """Check if chip is in expected mode"""
    time.sleep_ms(10)  # Small delay for mode to settle
    radio._wait_on_busy()  # Ensure chip is ready
    chip_mode = radio.get_chip_mode()
    mode_names = {0: "STDBY_RC", 1: "STDBY_XOSC", 2: "FS", 3: "RX", 4: "TX"}
    mode_name = mode_names.get(chip_mode, f"UNKNOWN({chip_mode})")
    
    if chip_mode == expected_value:
        print(f"    ✓ Mode correct: {mode_name} (value={chip_mode})")
        return True
    else:
        print(f"    ✗ Mode mismatch: expected {expected_name} ({expected_value}), got {mode_name} ({chip_mode})")
        return False

print("\n[2] Testing Mode Switches...")
print("-" * 60)

# Test 1: STDBY_RC
print("\n[Test 1] Switch to STDBY_RC...")
radio.set_standby(0)  # STDBY_RC
time.sleep_ms(5)
if check_mode("STDBY_RC", 0):
    print("    ✓ STDBY_RC mode verified")

# Test 2: STDBY_XOSC
print("\n[Test 2] Switch to STDBY_XOSC...")
radio.set_standby(1)  # STDBY_XOSC
time.sleep_ms(5)
if check_mode("STDBY_XOSC", 1):
    print("    ✓ STDBY_XOSC mode verified")

# Test 3: Prepare for TX
print("\n[Test 3] Preparing for TX...")
# Clear errors
radio.clear_device_errors()
# Clear IRQ
radio.clear_irq_status(0xFFFF)
# Write test data
test_data = b"TEST"
radio.write_buffer(0, test_data)
radio._write_register(0x0702, len(test_data))  # Set payload length
time.sleep_ms(1)
print("    ✓ TX preparation complete")

# Test 4: Switch to TX mode
print("\n[Test 4] Switch to TX mode...")
print("    BUSY before SetTx:", radio.busy.value())
radio.set_tx(0)  # Start TX
print("    BUSY after SetTx:", radio.busy.value())
time.sleep_ms(10)  # Allow mode transition
if check_mode("TX", 4):
    print("    ✓ TX mode verified")

# Test 5: Wait for TX_DONE and return to STDBY
print("\n[Test 5] Waiting for TX_DONE...")
start = time.ticks_ms()
tx_done = False
while time.ticks_diff(time.ticks_ms(), start) < 5000:  # 5 second timeout
    irq = radio.get_irq_status()
    if irq & 0x0001:  # TX_DONE
        print(f"    ✓ TX_DONE IRQ received after {time.ticks_diff(time.ticks_ms(), start)}ms")
        radio.clear_irq_status(0x0001)
        tx_done = True
        break
    time.sleep_ms(10)

if tx_done:
    # Return to STDBY_RC
    print("\n[Test 6] Return to STDBY_RC after TX...")
    radio.set_standby(0)  # STDBY_RC
    time.sleep_ms(5)
    if check_mode("STDBY_RC", 0):
        print("    ✓ Back to STDBY_RC verified")
else:
    print("    ✗ TX_DONE timeout")

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 60)
print("Mode Switch Test Complete")
print("=" * 60)

