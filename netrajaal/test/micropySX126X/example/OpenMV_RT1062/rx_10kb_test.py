"""
RX Test: Receive 10KB of data and calculate time
OpenMV RT1062 + Waveshare Core1262-868M

This script receives 10KB (10,240 bytes) of data and calculates the time taken.
It must be configured with the same parameters as the TX script:
- Spreading Factor: 5 (lowest for highest data rate)
- Bandwidth: 500 kHz (highest available)
- Coding Rate: 5 (4/5, lowest for highest data rate)
- Preamble Length: 8 (minimum)
"""

import time
try:
    from utime import ticks_ms, ticks_diff
except ImportError:
    # Fallback for systems where time module provides these functions
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff

from sx1262 import SX1262

# Pin definitions for OpenMV RT1062
SPI_BUS = 1
P0_MOSI = 'P0'  # MOSI
P1_MISO = 'P1'  # MISO
P2_SCLK = 'P2'  # SCLK
P3_CS = 'P3'    # Chip Select
P6_RST = 'P6'   # Reset
P7_BUSY = 'P7'  # Busy
P13_DIO1 = 'P13'  # DIO1 (IRQ)

# SPI Configuration
SPI_BAUDRATE = 2000000
SPI_POLARITY = 0
SPI_PHASE = 0

# Expected data size: 10KB = 10,240 bytes
EXPECTED_DATA_SIZE = 10 * 1024  # 10,240 bytes
MAX_PACKET_SIZE = 255  # Maximum LoRa packet size

# Initialize SX1262
print("Initializing SX1262...")
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

# Configure LoRa for HIGHEST DATA RATE (must match TX configuration)
# SF5, BW500kHz, CR5 (4/5), Preamble 8
print("Configuring LoRa for highest data rate...")
print("  - Spreading Factor: 5")
print("  - Bandwidth: 500 kHz")
print("  - Coding Rate: 5 (4/5)")
print("  - Preamble Length: 8")
print("  - Frequency: 868.0 MHz")
print("  - CRC: Enabled")
print()

status = sx.begin(
    freq=868.0,
    bw=500.0,          # 500 kHz - highest bandwidth for max data rate
    sf=5,              # SF5 - lowest spreading factor for max data rate
    cr=5,              # CR5 (4/5) - lowest coding rate for max data rate
    syncWord=0x12,
    power=14,
    currentLimit=60.0,
    preambleLength=8,  # Minimum preamble length
    implicit=False,
    crcOn=True,        # Keep CRC enabled for reliability
    tcxoVoltage=1.6,
    useRegulatorLDO=False,
    blocking=True
)

if status != 0:
    print(f"Error initializing SX1262: {status}")
else:
    print("SX1262 initialized successfully!")
    print("Waiting for data transmission to start...")
    print()

# Receive data
received_data = bytearray()
packet_count = 0
first_packet_time = None
last_packet_time = None

print("Starting reception...")
print("=" * 60)

# Receive packets until we have 10KB or timeout
timeout_ms = 60000  # 60 second timeout for receiving all packets
receive_start_time = ticks_ms()

while len(received_data) < EXPECTED_DATA_SIZE:
    # Check for timeout
    elapsed = ticks_diff(ticks_ms(), receive_start_time)
    if elapsed > timeout_ms:
        print(f"\nTimeout waiting for data (waited {elapsed} ms)")
        break
    
    # Receive a packet
    msg, status = sx.recv(timeout_en=True, timeout_ms=10000)  # 10 second timeout per packet
    
    if status == 0 and len(msg) > 0:
        # Record timing for first and last packet
        current_time = ticks_ms()
        if first_packet_time is None:
            first_packet_time = current_time
        
        last_packet_time = current_time
        received_data.extend(msg)
        packet_count += 1
        
        rssi = sx.getRSSI()
        snr = sx.getSNR()
        print(f"Packet {packet_count}: Received {len(msg)} bytes "
              f"(Total: {len(received_data)}/{EXPECTED_DATA_SIZE} bytes) "
              f"RSSI: {rssi:.1f} dBm, SNR: {snr:.1f} dB")
        
        # If we received the expected amount, we're done
        if len(received_data) >= EXPECTED_DATA_SIZE:
            break
    elif status == -6:  # RX_TIMEOUT
        # No packet received, continue waiting
        continue
    else:
        print(f"Error receiving packet: {status}")
        if len(received_data) == 0:
            # If we haven't received anything yet, continue waiting
            continue
        else:
            # If we received some data but got an error, break
            break

receive_end_time = ticks_ms()

print("=" * 60)
print()

# Calculate statistics
total_received = len(received_data)
if first_packet_time is not None and last_packet_time is not None:
    reception_duration_ms = ticks_diff(last_packet_time, first_packet_time)
    reception_duration_s = reception_duration_ms / 1000.0
else:
    reception_duration_ms = 0
    reception_duration_s = 0.0

total_time_ms = ticks_diff(receive_end_time, receive_start_time)
total_time_s = total_time_ms / 1000.0

print("RECEPTION COMPLETE")
print("=" * 60)
print(f"Total data received: {total_received} bytes ({total_received / 1024:.2f} KB)")
print(f"Expected data size: {EXPECTED_DATA_SIZE} bytes ({EXPECTED_DATA_SIZE / 1024:.2f} KB)")
print(f"Number of packets: {packet_count}")
print(f"Data completeness: {total_received / EXPECTED_DATA_SIZE * 100:.1f}%")
print()
print(f"First packet received at: {first_packet_time} ms")
print(f"Last packet received at: {last_packet_time} ms")
print(f"Reception duration (first to last): {reception_duration_ms} ms ({reception_duration_s:.3f} seconds)")
print(f"Total receive time (including waits): {total_time_ms} ms ({total_time_s:.3f} seconds)")
print()

if reception_duration_s > 0:
    print(f"Effective data rate: {total_received / reception_duration_s:.2f} bytes/sec "
          f"({total_received * 8 / reception_duration_s / 1000:.2f} kbps)")
    print(f"Average time per packet: {reception_duration_ms / packet_count:.2f} ms")
    print(f"Packet rate: {packet_count / reception_duration_s:.2f} packets/sec")
print("=" * 60)

# Verify data integrity (check pattern)
if total_received == EXPECTED_DATA_SIZE:
    print("\nVerifying data integrity...")
    data_correct = True
    for i in range(min(100, total_received)):  # Check first 100 bytes as sample
        expected_byte = i % 256
        if received_data[i] != expected_byte:
            print(f"Data mismatch at position {i}: expected {expected_byte}, got {received_data[i]}")
            data_correct = False
            break
    
    if data_correct:
        print("Data verification: PASSED (sample check)")
    else:
        print("Data verification: FAILED")
else:
    print(f"\nWarning: Received {total_received} bytes, expected {EXPECTED_DATA_SIZE} bytes")

print("\nReception test complete!")

