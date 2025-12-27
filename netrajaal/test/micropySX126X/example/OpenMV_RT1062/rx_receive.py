"""
RX Receiver Script for OpenMV RT1062 + Waveshare Core1262-868M

This script receives data from another LoRa device.
Make sure the LoRa parameters (frequency, spreading factor, bandwidth, etc.)
match the transmitting device.

Hardware Connections:
- P0: MOSI
- P1: MISO
- P2: SCLK
- P3: CS
- P6: RESET
- P7: BUSY
- P13: DIO1 (IRQ)
"""

from sx1262 import SX1262
from _sx126x import ERR_NONE, ERROR
try:
    from utime import sleep_ms, ticks_ms, ticks_diff
except ImportError:
    import time
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)
    def ticks_ms():
        return int(time.time() * 1000) & 0x7FFFFFFF
    def ticks_diff(end, start):
        diff = (end - start) & 0x7FFFFFFF
        return diff if diff < 0x40000000 else diff - 0x80000000

# ============================================================
# CONFIGURATION - Adjust these to match your transmitter
# ============================================================

# Pin definitions for OpenMV RT1062
SPI_BUS = 1
P0_MOSI = 'P0'   # MOSI
P1_MISO = 'P1'   # MISO
P2_SCLK = 'P2'   # SCLK
P3_CS = 'P3'     # Chip Select
P6_RST = 'P6'    # Reset
P7_BUSY = 'P7'   # Busy
P13_DIO1 = 'P13' # DIO1 (IRQ)

# SPI Configuration
SPI_BAUDRATE = 2000000
SPI_POLARITY = 0
SPI_PHASE = 0

# LoRa Configuration - MUST MATCH TRANSMITTER SETTINGS
FREQUENCY = 868.0      # MHz - Must match transmitter frequency
BANDWIDTH = 125.0      # kHz - Must match transmitter bandwidth
SPREADING_FACTOR = 9   # 5-12 - Must match transmitter spreading factor
CODING_RATE = 7        # 5-8 - Must match transmitter coding rate
SYNC_WORD = 0x12       # 0x12 (private) or 0x34 (public) - Must match transmitter
TX_POWER = 14          # dBm - Not critical for RX, but good to set
PREAMBLE_LENGTH = 8    # Must match transmitter preamble length

# Receive Configuration
USE_TIMEOUT = False    # Set to True to use timeout-based reception
RX_TIMEOUT_MS = 5000   # Timeout in milliseconds (if USE_TIMEOUT is True)
SHOW_HEX = True        # Show hex representation of received data
SHOW_ASCII = True      # Show ASCII/text representation of received data

# ============================================================
# INITIALIZATION
# ============================================================

print("Initializing SX1262 receiver...")
print(f"Frequency: {FREQUENCY} MHz")
print(f"Bandwidth: {BANDWIDTH} kHz")
print(f"Spreading Factor: {SPREADING_FACTOR}")
print(f"Coding Rate: {CODING_RATE}")
print(f"Sync Word: 0x{SYNC_WORD:02X}")
print("-" * 60)

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
    spi_baudrate=SPI_BAUDRATE,
    spi_polarity=SPI_POLARITY,
    spi_phase=SPI_PHASE
)

# Configure LoRa mode
status = sx.begin(
    freq=FREQUENCY,
    bw=BANDWIDTH,
    sf=SPREADING_FACTOR,
    cr=CODING_RATE,
    syncWord=SYNC_WORD,
    power=TX_POWER,
    currentLimit=60.0,
    preambleLength=PREAMBLE_LENGTH,
    implicit=False,
    crcOn=True,
    tcxoVoltage=1.6,
    useRegulatorLDO=False,
    blocking=True
)

if status != ERR_NONE:
    error_msg = ERROR.get(status, f"Unknown error: {status}")
    print(f"ERROR: Failed to initialize LoRa mode: {error_msg}")
    raise Exception(f"Initialization failed: {error_msg}")

print("✓ SX1262 initialized successfully")
print("=" * 60)
print("Waiting for messages...")
print("(Press Ctrl+C to stop)")
print("=" * 60)

# ============================================================
# RECEIVE LOOP
# ============================================================

packet_count = 0

try:
    while True:
        if USE_TIMEOUT:
            # Receive with timeout
            msg, err = sx.recv(timeout_en=True, timeout_ms=RX_TIMEOUT_MS)
        else:
            # Receive without timeout (blocking indefinitely until packet received)
            msg, err = sx.recv(timeout_en=False, timeout_ms=0)
        
        if err == ERR_NONE and len(msg) > 0:
            packet_count += 1
            
            # Get signal quality metrics
            try:
                rssi = sx.getRSSI()
                snr = sx.getSNR()
            except:
                rssi = 0.0
                snr = 0.0
            
            # Display packet information
            print(f"\n--- Packet #{packet_count} ---")
            print(f"Length: {len(msg)} bytes")
            print(f"RSSI: {rssi:.2f} dBm")
            print(f"SNR: {snr:.2f} dB")
            
            # Display data in different formats
            if SHOW_HEX:
                hex_str = ' '.join([f'{b:02X}' for b in msg])
                print(f"Hex: {hex_str}")
            
            if SHOW_ASCII:
                # Try to decode as UTF-8 text
                try:
                    text = msg.decode('utf-8', errors='replace')
                    # Check if it's printable ASCII/text
                    if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in text):
                        print(f"Text: {text}")
                    else:
                        print(f"Text: {repr(text)}")
                except:
                    print(f"Text: (binary data)")
            
            # Display raw bytes as array (useful for debugging)
            print(f"Bytes: {list(msg)}")
            print("-" * 60)
            
        elif err == -6:  # ERR_RX_TIMEOUT
            if USE_TIMEOUT:
                print(".", end="")  # Show activity indicator
            # Continue waiting
            continue
            
        elif err != ERR_NONE:
            error_msg = ERROR.get(err, f"Unknown error: {err}")
            print(f"\nERROR: Receive failed: {error_msg}")
            print(f"Error code: {err}")
            sleep_ms(100)
            
except KeyboardInterrupt:
    print("\n\nReceiver stopped by user")
    print(f"Total packets received: {packet_count}")
except Exception as e:
    print(f"\n\nFatal error: {e}")
    import sys
    sys.print_exception(e)

