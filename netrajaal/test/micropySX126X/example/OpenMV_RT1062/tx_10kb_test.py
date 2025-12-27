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
    from utime import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    # Fallback for systems where time module provides these functions
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
    sleep_ms = time.sleep_ms if hasattr(time, 'sleep_ms') else lambda ms: time.sleep(ms / 1000.0)

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
SEQ_NUM_SIZE = 1  # Sequence number size in bytes
ACK_SIZE = 1  # ACK packet size (just sequence number)
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - SEQ_NUM_SIZE  # Max data per packet
MAX_RETRIES = 5  # Maximum retries per packet
ACK_TIMEOUT_MS = 5000  # Timeout for waiting for ACK (5 seconds)

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

# Calculate number of packets needed (accounting for sequence number byte)
num_packets = (DATA_SIZE + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
print(f"Will send {DATA_SIZE} bytes in {num_packets} packets")
print(f"Max payload per packet: {MAX_PAYLOAD_SIZE} bytes (with {SEQ_NUM_SIZE} byte seq num)")
print(f"ACK timeout: {ACK_TIMEOUT_MS} ms")
print(f"Max retries per packet: {MAX_RETRIES}")
print()

# Send data and measure time
print("Starting transmission with ACK protocol...")
print("=" * 60)

start_time = ticks_ms()
total_sent = 0
total_retries = 0
packets_retried = 0

# Send data in chunks with ACK protocol
for packet_num in range(num_packets):
    # Calculate chunk boundaries
    start_idx = packet_num * MAX_PAYLOAD_SIZE
    end_idx = min(start_idx + MAX_PAYLOAD_SIZE, DATA_SIZE)
    chunk = test_data[start_idx:end_idx]
    
    # Create packet with sequence number: [seq_num, data...]
    packet_seq = packet_num & 0xFF  # Ensure it fits in 1 byte
    packet = bytes([packet_seq]) + chunk
    
    # Try sending packet until we get ACK or max retries
    ack_received = False
    retry_count = 0
    
    while not ack_received and retry_count <= MAX_RETRIES:
        if retry_count > 0:
            print(f"  Retry {retry_count}/{MAX_RETRIES}...")
            total_retries += 1
        
        # Send the packet
        payload_len, status = sx.send(packet)
        
        if status != 0:
            print(f"Packet {packet_num + 1}/{num_packets}: Send error {status}")
            retry_count += 1
            continue
        
        # Small delay to allow RX module to process and prepare to send ACK
        sleep_ms(50)
        
        # Switch to RX mode to receive ACK
        ack_received = False
        ack_start_time = ticks_ms()
        
        while ticks_diff(ticks_ms(), ack_start_time) < ACK_TIMEOUT_MS:
            # Wait for ACK
            ack_msg, ack_status = sx.recv(timeout_en=True, timeout_ms=1000)
            
            if ack_status == 0 and len(ack_msg) >= ACK_SIZE:
                # Check if ACK matches our sequence number
                ack_seq = ack_msg[0]
                if ack_seq == packet_seq:
                    ack_received = True
                    total_sent += len(chunk)
                    print(f"Packet {packet_num + 1}/{num_packets}: Sent {len(chunk)} bytes, ACK received "
                          f"(Total: {total_sent}/{DATA_SIZE} bytes)")
                    break
                else:
                    # Wrong sequence number, continue waiting
                    print(f"  Received ACK with wrong seq: {ack_seq}, expected: {packet_seq}")
            elif ack_status == -6:  # RX_TIMEOUT
                # Continue waiting
                continue
            else:
                # Error receiving, continue waiting
                continue
        
        if not ack_received:
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                print(f"  ACK timeout for packet {packet_num + 1}, retrying...")
    
    if not ack_received:
        print(f"Packet {packet_num + 1}/{num_packets}: Failed after {MAX_RETRIES} retries, aborting")
        break
    
    if retry_count > 0:
        packets_retried += 1

end_time = ticks_ms()
elapsed_time_ms = ticks_diff(end_time, start_time)
elapsed_time_s = elapsed_time_ms / 1000.0

print("=" * 60)
print()
print("TRANSMISSION COMPLETE")
print("=" * 60)
print(f"Total data sent: {total_sent} bytes ({total_sent / 1024:.2f} KB)")
print(f"Number of packets: {num_packets}")
print(f"Total retries: {total_retries}")
print(f"Packets retried: {packets_retried}")
print(f"Total time: {elapsed_time_ms} ms ({elapsed_time_s:.3f} seconds)")
if elapsed_time_s > 0:
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

