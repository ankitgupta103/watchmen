"""
API Test: Reception (recv)

This example demonstrates:
- recv() method with different parameters
- Blocking and non-blocking reception
- Timeout handling
- Error status codes
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

print("=== Reception (recv) API Test ===\n")
print("Note: This test requires a transmitter to send data.")
print("Run a transmitter example in parallel to test reception.\n")

# Test 1: Blocking receive (no timeout)
print("Test 1: Blocking receive (no timeout)")
print("  Waiting for message (will block until received)...")
try:
    msg, status = sx.recv()
    if status == 0:
        try:
            print(f"  [OK] Received: {msg.decode()}")
        except:
            print(f"  [OK] Received: {msg} (raw bytes)")
    elif status == -6:
        print("  [WARN] Timeout (no message received)")
    elif status == -7:
        print(f"  [WARN] CRC error but data received: {msg}")
    else:
        print(f"  [FAIL] Receive failed with status: {status}")
except Exception as e:
    print(f"  [FAIL] Receive error: {e}")

# Test 2: Receive with timeout
print("\nTest 2: Receive with timeout (5 seconds)")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
    if status == 0:
        try:
            print(f"  [OK] Received: {msg.decode()}")
        except:
            print(f"  [OK] Received: {msg} (raw bytes)")
    elif status == -6:
        print("  [WARN] Timeout (no message received within 5 seconds)")
    elif status == -7:
        print(f"  [WARN] CRC error but data received: {msg}")
    else:
        print(f"  [FAIL] Receive failed with status: {status}")
except Exception as e:
    print(f"  [FAIL] Receive error: {e}")

# Test 3: Receive with short timeout
print("\nTest 3: Receive with short timeout (1 second)")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=1000)
    if status == 0:
        try:
            print(f"  [OK] Received: {msg.decode()}")
        except:
            print(f"  [OK] Received: {msg} (raw bytes)")
    elif status == -6:
        print("  [WARN] Timeout (no message received within 1 second)")
    else:
        print(f"  [FAIL] Receive failed with status: {status}")
except Exception as e:
    print(f"  [FAIL] Receive error: {e}")

# Test 4: Receive with expected length
print("\nTest 4: Receive with expected length (10 bytes)")
try:
    msg, status = sx.recv(len=10, timeout_en=True, timeout_ms=5000)
    if status == 0:
        print(f"  [OK] Received {len(msg)} bytes: {msg}")
    elif status == -6:
        print("  [WARN] Timeout")
    else:
        print(f"  [FAIL] Receive failed with status: {status}")
except Exception as e:
    print(f"  [FAIL] Receive error: {e}")

# Test 5: Continuous reception loop
print("\nTest 5: Continuous reception loop (5 attempts)")
print("  Waiting for messages...")
received_count = 0
for i in range(5):
    try:
        msg, status = sx.recv(timeout_en=True, timeout_ms=2000)
        if status == 0:
            received_count += 1
            try:
                print(f"  [{i+1}] [OK] Received: {msg.decode()}")
            except:
                print(f"  [{i+1}] [OK] Received: {msg} (raw bytes)")
        elif status == -6:
            print(f"  [{i+1}] [WARN] Timeout (no message)")
        elif status == -7:
            received_count += 1
            print(f"  [{i+1}] [WARN] CRC error but data received: {msg}")
        else:
            print(f"  [{i+1}] [FAIL] Error: {status}")
    except Exception as e:
        print(f"  [{i+1}] [FAIL] Error: {e}")
print(f"\n  Total received: {received_count}/5")

# Test 6: Receive and display RSSI/SNR
print("\nTest 6: Receive with RSSI and SNR information")
try:
    msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
    if status == 0:
        rssi = sx.getRSSI()
        snr = sx.getSNR()
        try:
            print(f"  [OK] Received: {msg.decode()}")
        except:
            print(f"  [OK] Received: {msg} (raw bytes)")
        print(f"  RSSI: {rssi:.2f} dBm")
        print(f"  SNR: {snr:.2f} dB")
    elif status == -6:
        print("  [WARN] Timeout")
    else:
        print(f"  [FAIL] Receive failed with status: {status}")
except Exception as e:
    print(f"  [FAIL] Receive error: {e}")

print("\n=== Reception Tests Complete ===")

