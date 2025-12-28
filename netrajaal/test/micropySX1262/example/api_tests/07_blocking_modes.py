"""
API Test: Blocking and Non-blocking Modes

This example demonstrates:
- setBlockingCallback() - Set blocking/non-blocking mode
- Blocking mode operation
- Non-blocking mode with callback
- Event handling
"""

import time
from sx1262 import SX1262
from machine import Pin

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

print("=== Blocking and Non-blocking Modes API Test ===\n")

# Test 1: Blocking mode (default)
print("Test 1: Blocking mode (default)")
try:
    status = sx.setBlockingCallback(blocking=True)
    if status == 0:
        print("  [OK] Blocking mode enabled")
        print("  - send() blocks until transmission complete")
        print("  - recv() blocks until packet received or timeout")
        
        # Test blocking send
        print("\n  Testing blocking send...")
        payload_len, status = sx.send(b"Blocking mode test")
        if status == 0:
            print(f"  [OK] Blocking send completed: {payload_len} bytes")
        else:
            print(f"  [FAIL] Blocking send failed: {status}")
    else:
        print(f"  [FAIL] Failed to set blocking mode: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 2: Non-blocking mode without callback
print("Test 2: Non-blocking mode without callback")
try:
    status = sx.setBlockingCallback(blocking=False)
    if status == 0:
        print("  [OK] Non-blocking mode enabled")
        print("  - send() returns immediately")
        print("  - recv() returns immediately (check status)")
        
        # Test non-blocking send
        print("\n  Testing non-blocking send...")
        payload_len, status = sx.send(b"Non-blocking test")
        if status == 0:
            print(f"  [OK] Non-blocking send initiated: {payload_len} bytes")
            print("  (Transmission continues in background)")
        else:
            print(f"  [FAIL] Non-blocking send failed: {status}")
    else:
        print(f"  [FAIL] Failed to set non-blocking mode: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 3: Non-blocking mode with callback
print("Test 3: Non-blocking mode with callback")
print("  Setting up callback function...")

# Global variables for callback
rx_events = []
tx_events = []

def event_callback(events):
    """Callback function for non-blocking mode"""
    if events & SX1262.RX_DONE:
        rx_events.append(events)
        print(f"  [Callback] RX_DONE event received")
        # Read the received packet
        msg, status = sx.recv()
        if status == 0:
            try:
                print(f"  [Callback] Received: {msg.decode()}")
            except:
                print(f"  [Callback] Received: {msg}")
    elif events & SX1262.TX_DONE:
        tx_events.append(events)
        print(f"  [Callback] TX_DONE event received")

try:
    status = sx.setBlockingCallback(blocking=False, callback=event_callback)
    if status == 0:
        print("  [OK] Non-blocking mode with callback enabled")
        print("  - Callback will be called on TX_DONE or RX_DONE events")
        
        # Test non-blocking send with callback
        print("\n  Testing non-blocking send with callback...")
        payload_len, status = sx.send(b"Callback test")
        if status == 0:
            print(f"  [OK] Send initiated: {payload_len} bytes")
            print("  Waiting for TX_DONE callback...")
            time.sleep(2)  # Wait for transmission to complete
            if len(tx_events) > 0:
                print("  [OK] TX_DONE callback received")
            else:
                print("  [WARN] TX_DONE callback not received (may need more time)")
        else:
            print(f"  [FAIL] Send failed: {status}")
    else:
        print(f"  [FAIL] Failed to set non-blocking mode with callback: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 4: Switch between blocking and non-blocking
print("Test 4: Switch between blocking and non-blocking modes")
try:
    # Switch to blocking
    status = sx.setBlockingCallback(blocking=True)
    if status == 0:
        print("  [OK] Switched to blocking mode")
        payload_len, status = sx.send(b"Blocking mode")
        if status == 0:
            print(f"  [OK] Blocking send: {payload_len} bytes")
    
    # Switch to non-blocking
    status = sx.setBlockingCallback(blocking=False)
    if status == 0:
        print("  [OK] Switched to non-blocking mode")
        payload_len, status = sx.send(b"Non-blocking mode")
        if status == 0:
            print(f"  [OK] Non-blocking send: {payload_len} bytes")
    
    # Switch back to blocking
    status = sx.setBlockingCallback(blocking=True)
    if status == 0:
        print("  [OK] Switched back to blocking mode")
except Exception as e:
    print(f"  [FAIL] Error: {e}")
print()

# Test 5: Non-blocking reception with callback
print("Test 5: Non-blocking reception with callback")
print("  Note: This requires a transmitter to send data")
try:
    status = sx.setBlockingCallback(blocking=False, callback=event_callback)
    if status == 0:
        print("  [OK] Non-blocking RX mode enabled")
        print("  Waiting for incoming packets (10 seconds)...")
        print("  Callback will be triggered on RX_DONE")
        
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < 10000:
            time.sleep(0.1)
            # Check if callback was triggered
            if len(rx_events) > 0:
                print("  [OK] RX_DONE callback received")
                break
        
        if len(rx_events) == 0:
            print("  [WARN] No RX_DONE callback received (no packet received)")
    else:
        print(f"  [FAIL] Failed to set non-blocking RX mode: {status}")
except Exception as e:
    print(f"  [FAIL] Error: {e}")

# Reset to blocking mode
sx.setBlockingCallback(blocking=True)
print()

print("=== Blocking Mode Tests Complete ===")

