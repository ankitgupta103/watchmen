"""
API Test: Configuration Methods

This example demonstrates:
- setFrequency() - Change frequency
- setOutputPower() - Change TX power
- setSpreadingFactor() - Change SF
- setBandwidth() - Change BW
- setCodingRate() - Change CR
- setPreambleLength() - Change preamble
- setSyncWord() - Change sync word
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

# Initial configuration
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=True
)

print("=== Configuration Methods API Test ===\n")

# Test 1: setFrequency()
print("Test 1: setFrequency() - Change frequency")
frequencies = [868.0, 868.1, 868.2, 868.3]
for freq in frequencies:
    try:
        status = sx.setFrequency(freq, calibrate=True)
        if status == 0:
            print(f"  [OK] Frequency set to {freq} MHz")
        else:
            print(f"  [FAIL] Failed to set frequency {freq} MHz: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting frequency {freq} MHz: {e}")
    time.sleep(0.5)

# Reset to 868.0 MHz
sx.setFrequency(868.0, calibrate=True)
print()

# Test 2: setOutputPower()
print("Test 2: setOutputPower() - Change TX power")
power_levels = [0, 5, 10, 14, 20]
for power in power_levels:
    try:
        status = sx.setOutputPower(power)
        if status == 0:
            print(f"  [OK] TX power set to {power} dBm")
        else:
            print(f"  [FAIL] Failed to set power {power} dBm: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting power {power} dBm: {e}")
    time.sleep(0.2)

# Reset to 14 dBm
sx.setOutputPower(14)
print()

# Test 3: setSpreadingFactor()
print("Test 3: setSpreadingFactor() - Change spreading factor")
spreading_factors = [5, 7, 9, 12]
for sf in spreading_factors:
    try:
        status = sx.setSpreadingFactor(sf)
        if status == 0:
            print(f"  [OK] Spreading factor set to {sf}")
        else:
            print(f"  [FAIL] Failed to set SF {sf}: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting SF {sf}: {e}")
    time.sleep(0.2)

# Reset to SF9
sx.setSpreadingFactor(9)
print()

# Test 4: setBandwidth()
print("Test 4: setBandwidth() - Change bandwidth")
bandwidths = [125.0, 250.0, 500.0]
for bw in bandwidths:
    try:
        status = sx.setBandwidth(bw)
        if status == 0:
            print(f"  [OK] Bandwidth set to {bw} kHz")
        else:
            print(f"  [FAIL] Failed to set BW {bw} kHz: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting BW {bw} kHz: {e}")
    time.sleep(0.2)

# Reset to 125 kHz
sx.setBandwidth(125.0)
print()

# Test 5: setCodingRate()
print("Test 5: setCodingRate() - Change coding rate")
coding_rates = [5, 6, 7, 8]
for cr in coding_rates:
    try:
        status = sx.setCodingRate(cr)
        if status == 0:
            print(f"  [OK] Coding rate set to {cr} (4/{cr})")
        else:
            print(f"  [FAIL] Failed to set CR {cr}: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting CR {cr}: {e}")
    time.sleep(0.2)

# Reset to CR7
sx.setCodingRate(7)
print()

# Test 6: setPreambleLength()
print("Test 6: setPreambleLength() - Change preamble length")
preamble_lengths = [8, 12, 16, 20]
for pl in preamble_lengths:
    try:
        status = sx.setPreambleLength(pl)
        if status == 0:
            print(f"  [OK] Preamble length set to {pl}")
        else:
            print(f"  [FAIL] Failed to set preamble length {pl}: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting preamble length {pl}: {e}")
    time.sleep(0.2)

# Reset to 8
sx.setPreambleLength(8)
print()

# Test 7: setSyncWord()
print("Test 7: setSyncWord() - Change sync word")
sync_words = [0x12, 0x34]
for sw in sync_words:
    try:
        status = sx.setSyncWord(sw)
        if status == 0:
            print(f"  [OK] Sync word set to 0x{sw:02X}")
        else:
            print(f"  [FAIL] Failed to set sync word 0x{sw:02X}: {status}")
    except Exception as e:
        print(f"  [FAIL] Error setting sync word 0x{sw:02X}: {e}")
    time.sleep(0.2)

# Reset to 0x12
sx.setSyncWord(0x12)
print()

# Test 8: Combined configuration change
print("Test 8: Combined configuration change")
print("  Changing multiple parameters...")
try:
    status1 = sx.setFrequency(868.1, calibrate=False)
    status2 = sx.setOutputPower(10)
    status3 = sx.setSpreadingFactor(7)
    if status1 == 0 and status2 == 0 and status3 == 0:
        print("  [OK] Multiple parameters changed successfully")
        print("    Frequency: 868.1 MHz")
        print("    Power: 10 dBm")
        print("    SF: 7")
    else:
        print(f"  [FAIL] Some parameters failed: freq={status1}, power={status2}, sf={status3}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

# Reset configuration
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

print("=== Configuration Tests Complete ===")

