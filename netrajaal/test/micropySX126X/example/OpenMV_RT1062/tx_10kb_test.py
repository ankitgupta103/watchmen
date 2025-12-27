"""
TX Test: Send 10KB of data at highest data rate
OpenMV RT1062 + Waveshare Core1262-868M

This script sends 10KB (10,240 bytes) of data using the highest data rate configuration:
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

# Data size: 10KB = 10,240 bytes
DATA_SIZE = 10 * 1024  # 10,240 bytes
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

# Configure LoRa for HIGHEST DATA RATE
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
    print()

# Generate 10KB of test data
print(f"Generating {DATA_SIZE} bytes of test data...")
# Create a pattern that's easy to verify: sequential bytes
test_data = bytes([i % 256 for i in range(DATA_SIZE)])
print(f"Test data generated: {len(test_data)} bytes")
print()

# Calculate number of packets needed
num_packets = (DATA_SIZE + MAX_PACKET_SIZE - 1) // MAX_PACKET_SIZE
print(f"Will send {DATA_SIZE} bytes in {num_packets} packets (max {MAX_PACKET_SIZE} bytes per packet)")
print()

# Send data and measure time
print("Starting transmission...")
print("=" * 60)

start_time = ticks_ms()

# Send data in chunks
total_sent = 0
for packet_num in range(num_packets):
    # Calculate chunk boundaries
    start_idx = packet_num * MAX_PACKET_SIZE
    end_idx = min(start_idx + MAX_PACKET_SIZE, DATA_SIZE)
    chunk = test_data[start_idx:end_idx]
    
    # Send the chunk
    payload_len, status = sx.send(chunk)
    
    if status == 0:
        total_sent += payload_len
        print(f"Packet {packet_num + 1}/{num_packets}: Sent {payload_len} bytes "
              f"(Total: {total_sent}/{DATA_SIZE} bytes)")
    else:
        print(f"Packet {packet_num + 1}/{num_packets}: Error {status}")
        break

end_time = ticks_ms()
elapsed_time_ms = ticks_diff(end_time, start_time)
elapsed_time_s = elapsed_time_ms / 1000.0

print("=" * 60)
print()
print("TRANSMISSION COMPLETE")
print("=" * 60)
print(f"Total data sent: {total_sent} bytes ({total_sent / 1024:.2f} KB)")
print(f"Number of packets: {num_packets}")
print(f"Total time: {elapsed_time_ms} ms ({elapsed_time_s:.3f} seconds)")
print(f"Data rate: {total_sent / elapsed_time_s:.2f} bytes/sec ({total_sent * 8 / elapsed_time_s / 1000:.2f} kbps)")
print(f"Time per packet: {elapsed_time_ms / num_packets:.2f} ms")
print(f"Packet rate: {num_packets / elapsed_time_s:.2f} packets/sec")
print("=" * 60)

# Calculate expected time on air for one packet (for reference)
if num_packets > 0:
    time_on_air_us = sx.getTimeOnAir(MAX_PACKET_SIZE)
    time_on_air_ms = time_on_air_us / 1000.0
    print(f"\nTheoretical time on air per packet ({MAX_PACKET_SIZE} bytes): {time_on_air_ms:.2f} ms")
    print(f"Theoretical total time on air: {time_on_air_ms * num_packets:.2f} ms")

print("\nTransmission test complete!")

