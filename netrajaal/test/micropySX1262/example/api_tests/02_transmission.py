"""
API Test: Transmission (send)

This example demonstrates:
- send() method with different data types
- send() with various packet sizes
- Error handling for transmission
- Transmission status codes
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

print("=== Transmission (send) API Test ===\n")

# Test 1: Send string data
print("Test 1: Send string data")
try:
    message = "Hello, LoRa!"
    payload_len, status = sx.send(message.encode())
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes: '{message}'")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 2: Send bytes
print("\nTest 2: Send bytes")
try:
    data = b"Test message"
    payload_len, status = sx.send(data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes: {data}")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 3: Send bytearray
print("\nTest 3: Send bytearray")
try:
    data = bytearray([0x01, 0x02, 0x03, 0x04, 0x05])
    payload_len, status = sx.send(data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes: {list(data)}")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 4: Send small packet (1 byte)
print("\nTest 4: Send small packet (1 byte)")
try:
    data = b"A"
    payload_len, status = sx.send(data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 5: Send medium packet (100 bytes)
print("\nTest 5: Send medium packet (100 bytes)")
try:
    data = b"X" * 100
    payload_len, status = sx.send(data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 6: Send large packet (254 bytes - max payload)
print("\nTest 6: Send large packet (254 bytes - max payload)")
try:
    data = b"X" * 254
    payload_len, status = sx.send(data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes (max payload)")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 7: Send structured data (JSON-like)
print("\nTest 7: Send structured data")
try:
    import json
    sensor_data = {
        "temp": 25.5,
        "humidity": 60.0,
        "node_id": 1
    }
    json_str = json.dumps(sensor_data)
    payload_len, status = sx.send(json_str.encode())
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes: {json_str}")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 8: Send binary data
print("\nTest 8: Send binary data")
try:
    # Create binary data with various patterns
    binary_data = bytes(range(256))[:100]  # First 100 bytes
    payload_len, status = sx.send(binary_data)
    if status == 0:
        print(f"[OK] Sent {payload_len} bytes of binary data")
    else:
        print(f"[FAIL] Send failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Send error: {e}")
time.sleep(1)

# Test 9: Continuous transmission
print("\nTest 9: Continuous transmission (5 packets)")
try:
    for i in range(5):
        message = f"Packet {i+1}/5"
        payload_len, status = sx.send(message.encode())
        if status == 0:
            print(f"  [OK] Packet {i+1}: {payload_len} bytes")
        else:
            print(f"  [FAIL] Packet {i+1} failed: {status}")
        time.sleep(0.5)
    print("[OK] Continuous transmission complete")
except Exception as e:
    print(f"[FAIL] Continuous transmission error: {e}")

print("\n=== Transmission Tests Complete ===")

