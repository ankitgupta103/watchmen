"""
Diagnostic RX Receiver for OpenMV RT1062 + Waveshare Core1262-868M

This script helps troubleshoot reception issues by:
- Testing different parameter combinations
- Monitoring RSSI continuously
- Trying different sync words
- Providing detailed diagnostic information
"""

from sx1262 import SX1262
from _sx126x import ERR_NONE, ERROR
try:
    from utime import sleep_ms, ticks_ms
except ImportError:
    import time
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)
    def ticks_ms():
        return int(time.time() * 1000) & 0x7FFFFFFF

# Pin definitions
SPI_BUS = 1
P0_MOSI = 'P0'
P1_MISO = 'P1'
P2_SCLK = 'P2'
P3_CS = 'P3'
P6_RST = 'P6'
P7_BUSY = 'P7'
P13_DIO1 = 'P13'

# Configuration - Try different values if not receiving
FREQUENCY = 868.0
BANDWIDTH = 125.0
SPREADING_FACTOR = 9
CODING_RATE = 7
SYNC_WORD_PRIVATE = 0x12  # Try this first
SYNC_WORD_PUBLIC = 0x34   # Try this if 0x12 doesn't work

print("=" * 60)
print("LoRa RX Diagnostic Tool")
print("=" * 60)
print("This script will help diagnose reception issues")
print("-" * 60)

# Initialize
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

# Test 1: Try private sync word (0x12)
print("\n[TEST 1] Configuring with Sync Word 0x12 (Private)...")
status = sx.begin(
    freq=FREQUENCY,
    bw=BANDWIDTH,
    sf=SPREADING_FACTOR,
    cr=CODING_RATE,
    syncWord=SYNC_WORD_PRIVATE,
    power=14,
    blocking=True
)

if status != ERR_NONE:
    print(f"ERROR: Configuration failed: {ERROR.get(status, status)}")
else:
    print("✓ Configuration successful")
    
    # Start continuous RX to monitor RSSI
    sx.startReceive()
    print("\nMonitoring RSSI (should show noise floor ~-120 to -140 dBm if no signal)...")
    print("If you see higher values (e.g., -80 to -100 dBm), a signal is present!")
    print("Press Ctrl+C to stop and try next test")
    print("-" * 60)
    
    try:
        for i in range(100):  # Monitor for ~10 seconds
            try:
                rssi = sx.getRSSI()
                print(f"RSSI: {rssi:6.2f} dBm", end='\r')
            except:
                pass
            sleep_ms(100)
            
            # Try to receive
            msg, err = sx.recv(timeout_en=True, timeout_ms=100)
            if err == ERR_NONE and len(msg) > 0:
                print(f"\n\n✓ PACKET RECEIVED!")
                print(f"Length: {len(msg)} bytes")
                try:
                    print(f"Data: {msg.decode()}")
                except:
                    print(f"Data (hex): {' '.join([f'{b:02X}' for b in msg])}")
                print(f"RSSI: {sx.getRSSI():.2f} dBm")
                print(f"SNR: {sx.getSNR():.2f} dB")
                break
    except KeyboardInterrupt:
        print("\n\nStopped by user")

# Test 2: Try public sync word (0x34)
print("\n\n[TEST 2] Trying Sync Word 0x34 (Public)...")
status = sx.begin(
    freq=FREQUENCY,
    bw=BANDWIDTH,
    sf=SPREADING_FACTOR,
    cr=CODING_RATE,
    syncWord=SYNC_WORD_PUBLIC,
    power=14,
    blocking=True
)

if status == ERR_NONE:
    sx.startReceive()
    print("Monitoring for packets with Sync Word 0x34...")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        for i in range(200):
            msg, err = sx.recv(timeout_en=True, timeout_ms=100)
            
            try:
                rssi = sx.getRSSI()
                print(f"RSSI: {rssi:6.2f} dBm", end='\r')
            except:
                pass
            
            if err == ERR_NONE and len(msg) > 0:
                print(f"\n\n✓ PACKET RECEIVED with Sync Word 0x34!")
                print(f"Length: {len(msg)} bytes")
                try:
                    print(f"Data: {msg.decode()}")
                except:
                    print(f"Data (hex): {' '.join([f'{b:02X}' for b in msg])}")
                print(f"RSSI: {sx.getRSSI():.2f} dBm")
                print(f"SNR: {sx.getSNR():.2f} dB")
                break
            sleep_ms(50)
    except KeyboardInterrupt:
        print("\n\nStopped by user")

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)
print("\nTROUBLESHOOTING TIPS:")
print("1. Check that frequency matches transmitter (868.0 MHz)")
print("2. Check that bandwidth matches (125 kHz)")
print("3. Check that spreading factor matches (SF9)")
print("4. Check that coding rate matches (CR7 = 4/7)")
print("5. Try both sync words: 0x12 (private) and 0x34 (public)")
print("6. Ensure antennas are connected on both devices")
print("7. Check that devices are within range")
print("8. Verify preamble length matches (default is usually 8)")
print("=" * 60)

