"""
API Test: Status and Information Methods

This example demonstrates:
- getRSSI() - Get received signal strength
- getSNR() - Get signal-to-noise ratio
- getTimeOnAir() - Calculate time on air
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

print("=== Status and Information Methods API Test ===\n")

# Test 1: getRSSI() - After receiving a packet
print("Test 1: getRSSI() - Get received signal strength")
print("  Note: RSSI is only valid after receiving a packet")
print("  Waiting for a packet to measure RSSI...")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=10000)
    if status == 0 or status == -7:  # Success or CRC error (still has RSSI)
        rssi = sx.getRSSI()
        print(f"  [OK] RSSI: {rssi:.2f} dBm")
        if rssi > -100:
            print("    Signal strength: Good")
        elif rssi > -120:
            print("    Signal strength: Fair")
        else:
            print("    Signal strength: Weak")
    else:
        print(f"  [WARN] No packet received (status: {status}), RSSI may be invalid")
        rssi = sx.getRSSI()
        print(f"  RSSI (may be invalid): {rssi:.2f} dBm")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 2: getSNR() - After receiving a packet
print("Test 2: getSNR() - Get signal-to-noise ratio")
print("  Waiting for a packet to measure SNR...")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=10000)
    if status == 0 or status == -7:  # Success or CRC error (still has SNR)
        snr = sx.getSNR()
        print(f"  [OK] SNR: {snr:.2f} dB")
        if snr > 10:
            print("    Signal quality: Excellent")
        elif snr > 5:
            print("    Signal quality: Good")
        elif snr > 0:
            print("    Signal quality: Fair")
        else:
            print("    Signal quality: Poor")
    else:
        print(f"  [WARN] No packet received (status: {status}), SNR may be invalid")
        snr = sx.getSNR()
        print(f"  SNR (may be invalid): {snr:.2f} dB")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 3: getTimeOnAir() - Calculate time on air for different packet sizes
print("Test 3: getTimeOnAir() - Calculate time on air")
packet_sizes = [1, 10, 50, 100, 255]
print("  Packet Size | Time on Air (ms)")
print("  ------------|------------------")
for size in packet_sizes:
    try:
        time_us = sx.getTimeOnAir(size)
        time_ms = time_us / 1000.0
        print(f"  {size:11d} | {time_ms:15.2f}")
    except Exception as e:
        print(f"  {size:11d} | Error: {e}")
print()

# Test 4: getTimeOnAir() with different configurations
print("Test 4: getTimeOnAir() with different SF configurations")
packet_size = 50
print(f"  Packet size: {packet_size} bytes")
print("  SF | Time on Air (ms)")
print("  ---|------------------")
for sf in [5, 7, 9, 12]:
    try:
        sx.setSpreadingFactor(sf)
        time_us = sx.getTimeOnAir(packet_size)
        time_ms = time_us / 1000.0
        print(f"  {sf:2d} | {time_ms:15.2f}")
    except Exception as e:
        print(f"  {sf:2d} | Error: {e}")

# Reset to SF9
sx.setSpreadingFactor(9)
print()

# Test 5: getTimeOnAir() with different bandwidths
print("Test 5: getTimeOnAir() with different bandwidths")
packet_size = 50
print(f"  Packet size: {packet_size} bytes")
print("  BW (kHz) | Time on Air (ms)")
print("  ---------|------------------")
for bw in [125.0, 250.0, 500.0]:
    try:
        sx.setBandwidth(bw)
        time_us = sx.getTimeOnAir(packet_size)
        time_ms = time_us / 1000.0
        print(f"  {bw:8.1f} | {time_ms:15.2f}")
    except Exception as e:
        print(f"  {bw:8.1f} | Error: {e}")

# Reset to 125 kHz
sx.setBandwidth(125.0)
print()

# Test 6: Combined RSSI and SNR after reception
print("Test 6: Combined RSSI and SNR after reception")
print("  Waiting for a packet...")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=10000)
    if status == 0 or status == -7:
        rssi = sx.getRSSI()
        snr = sx.getSNR()
        print(f"  [OK] Received packet:")
        print(f"    RSSI: {rssi:.2f} dBm")
        print(f"    SNR:  {snr:.2f} dB")
        print(f"    Data: {msg[:20]}..." if len(msg) > 20 else f"    Data: {msg}")
    else:
        print(f"  [WARN] No packet received (status: {status})")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

print("\n=== Status Information Tests Complete ===")

