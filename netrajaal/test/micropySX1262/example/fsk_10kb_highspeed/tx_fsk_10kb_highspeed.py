"""
TX Test: High-Speed FSK 10KB Data Transfer with Selective Retransmission
OpenMV RT1062 + Waveshare Core1262-868M

This script implements a high-speed FSK data transfer protocol:
1. Sends all 10KB packets sequentially (no ACK waiting)
2. Receives corruption list from RX device
3. Resends only corrupted packets
4. Calculates total transfer time

High-speed FSK configuration:
- Bit Rate: 200 kbps (high speed)
- Frequency Deviation: 200 kHz
- RX Bandwidth: 467 kHz (wide bandwidth for high speed)
- Data Shaping: 0.5 (Gaussian filter)
- Preamble Length: 16 bits (minimum for reliability)
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
MAX_PACKET_SIZE = 255  # Maximum FSK packet size
SEQ_NUM_SIZE = 1  # Sequence number size in bytes
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - SEQ_NUM_SIZE  # Max data per packet

# Protocol constants
CORRUPTION_LIST_TIMEOUT_MS = 10000  # Timeout for waiting for corruption list (10 seconds)
CORRUPTION_LIST_HEADER = 0xFF  # Header byte to identify corruption list packet
RETRANSMISSION_TIMEOUT_MS = 30000  # Timeout for retransmission phase (30 seconds)

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

# Configure FSK for HIGH SPEED DATA RATE
# 200 kbps, 200 kHz freq deviation, 467 kHz RX bandwidth
print("Configuring FSK for high-speed data transfer...")
print("  - Bit Rate: 200 kbps")
print("  - Frequency Deviation: 200 kHz")
print("  - RX Bandwidth: 467 kHz")
print("  - Data Shaping: 0.5 (Gaussian)")
print("  - Preamble Length: 16 bits")
print("  - Frequency: 868.0 MHz")
print("  - CRC: Enabled (2 bytes)")
print()

status = sx.beginFSK(
    freq=868.0,              # 868 MHz (EU ISM band)
    br=200.0,                # 200 kbps - high speed bit rate
    freqDev=200.0,           # 200 kHz frequency deviation (matches bit rate)
    rxBw=467.0,             # 467 kHz - wide RX bandwidth for high speed
    power=14,                # 14 dBm TX power
    currentLimit=60.0,
    preambleLength=16,       # 16-bit preamble (minimum for reliability)
    dataShaping=0.5,         # Gaussian filter 0.5
    syncWord=[0x2D, 0x01],   # Sync word (must match RX)
    syncBitsLength=16,       # 16-bit sync word
    addrFilter=0,            # No address filtering
    crcLength=2,             # 2-byte CRC for error detection
    crcInitial=0x1D0F,
    crcPolynomial=0x1021,
    crcInverted=True,
    whiteningOn=True,        # Enable whitening for better data integrity
    whiteningInitial=0x0100,
    fixedPacketLength=False, # Variable packet length mode
    packetLength=0xFF,       # Max packet length
    preambleDetectorLength=16, # Preamble detector length
    tcxoVoltage=1.6,
    useRegulatorLDO=False,
    blocking=True
)

if status != 0:
    print(f"Error initializing SX1262: {status}")
else:
    print("SX1262 initialized successfully in FSK mode!")
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
print()

# ============================================================================
# PHASE 1: Send all packets sequentially (no ACK waiting)
# ============================================================================
print("=" * 60)
print("PHASE 1: Sending all packets sequentially...")
print("=" * 60)

phase1_start_time = ticks_ms()
total_sent = 0

# Store all packets for potential retransmission
packets = []

for packet_num in range(num_packets):
    # Calculate chunk boundaries
    start_idx = packet_num * MAX_PAYLOAD_SIZE
    end_idx = min(start_idx + MAX_PAYLOAD_SIZE, DATA_SIZE)
    chunk = test_data[start_idx:end_idx]
    
    # Create packet with sequence number: [seq_num, data...]
    packet_seq = packet_num & 0xFF  # Ensure it fits in 1 byte
    packet = bytes([packet_seq]) + chunk
    
    # Store packet for potential retransmission
    packets.append((packet_seq, packet, chunk))
    
    # Send the packet
    payload_len, status = sx.send(packet)
    
    if status != 0:
        print(f"Packet {packet_num + 1}/{num_packets} (seq {packet_seq}): Send error {status}")
    else:
        total_sent += len(chunk)
        if (packet_num + 1) % 10 == 0 or packet_num == 0:
            print(f"Packet {packet_num + 1}/{num_packets} (seq {packet_seq}): Sent {len(chunk)} bytes "
                  f"(Total: {total_sent}/{DATA_SIZE} bytes)")
    
    # Small delay between packets to avoid overwhelming the receiver
    sleep_ms(10)

phase1_end_time = ticks_ms()
phase1_duration_ms = ticks_diff(phase1_end_time, phase1_start_time)
phase1_duration_s = phase1_duration_ms / 1000.0

print()
print(f"Phase 1 complete: Sent {num_packets} packets in {phase1_duration_ms} ms ({phase1_duration_s:.3f} seconds)")
print()

# ============================================================================
# PHASE 2: Receive corruption list from RX device
# ============================================================================
print("=" * 60)
print("PHASE 2: Waiting for corruption list from RX device...")
print("=" * 60)

corrupted_seqs = set()
corruption_list_received = False
corruption_list_start_time = ticks_ms()

while ticks_diff(ticks_ms(), corruption_list_start_time) < CORRUPTION_LIST_TIMEOUT_MS:
    # Wait for corruption list packet
    msg, status = sx.recv(timeout_en=True, timeout_ms=2000)
    
    if status == 0 and len(msg) > 0:
        # In FSK variable length mode, first byte is length byte added by chip
        # Corruption list format: [length_byte, 0xFF, count, seq1, seq2, ...]
        # Check if this is a corruption list packet (second byte should be header)
        if len(msg) >= 2 and msg[1] == CORRUPTION_LIST_HEADER:
            # Parse corruption list: [length_byte, 0xFF, count, seq1, seq2, ...]
            if len(msg) >= 3:
                count = msg[2]
                if len(msg) >= (3 + count):
                    corrupted_seqs = set(msg[3:3+count])
                    corruption_list_received = True
                    print(f"Received corruption list: {count} corrupted packet(s)")
                    if count > 0:
                        print(f"Corrupted sequence numbers: {sorted(corrupted_seqs)}")
                    else:
                        print("No corrupted packets! All packets received successfully.")
                    break
                else:
                    print(f"Warning: Corruption list packet too short (expected {3+count} bytes, got {len(msg)})")
            else:
                print(f"Warning: Corruption list packet too short (got {len(msg)} bytes)")
        else:
            # Not a corruption list packet, continue waiting
            continue
    elif status == -6:  # RX_TIMEOUT
        # Continue waiting
        continue
    else:
        # Error receiving, continue waiting
        continue

if not corruption_list_received:
    print(f"Timeout waiting for corruption list after {CORRUPTION_LIST_TIMEOUT_MS} ms")
    print("Assuming all packets were received correctly (no corruption list)")
    corrupted_seqs = set()

print()

# ============================================================================
# PHASE 3: Retransmit corrupted packets
# ============================================================================
phase3_start_time = ticks_ms()
retransmitted_count = 0

if len(corrupted_seqs) > 0:
    print("=" * 60)
    print(f"PHASE 3: Retransmitting {len(corrupted_seqs)} corrupted packet(s)...")
    print("=" * 60)
    
    for seq in sorted(corrupted_seqs):
        # Find the packet with this sequence number
        packet_found = False
        for stored_seq, packet, chunk in packets:
            if stored_seq == seq:
                # Retransmit the packet
                payload_len, status = sx.send(packet)
                
                if status != 0:
                    print(f"Retransmission error for seq {seq}: {status}")
                else:
                    retransmitted_count += 1
                    print(f"Retransmitted packet seq {seq} ({len(chunk)} bytes)")
                
                # Small delay between retransmissions
                sleep_ms(10)
                packet_found = True
                break
        
        if not packet_found:
            print(f"Warning: Could not find packet with seq {seq} for retransmission")
    
    phase3_end_time = ticks_ms()
    phase3_duration_ms = ticks_diff(phase3_end_time, phase3_start_time)
    phase3_duration_s = phase3_duration_ms / 1000.0
    
    print()
    print(f"Phase 3 complete: Retransmitted {retransmitted_count} packets in {phase3_duration_ms} ms ({phase3_duration_s:.3f} seconds)")
else:
    print("=" * 60)
    print("PHASE 3: No corrupted packets to retransmit")
    print("=" * 60)
    phase3_duration_ms = 0
    phase3_duration_s = 0.0

print()

# ============================================================================
# Calculate total statistics
# ============================================================================
total_end_time = ticks_ms()
total_duration_ms = ticks_diff(total_end_time, phase1_start_time)
total_duration_s = total_duration_ms / 1000.0

print("=" * 60)
print("TRANSMISSION COMPLETE")
print("=" * 60)
print(f"Total data sent: {DATA_SIZE} bytes ({DATA_SIZE / 1024:.2f} KB)")
print(f"Number of packets: {num_packets}")
print(f"Corrupted packets: {len(corrupted_seqs)}")
print(f"Retransmitted packets: {retransmitted_count}")
print()
print(f"Phase 1 (initial send) time: {phase1_duration_ms} ms ({phase1_duration_s:.3f} seconds)")
if phase3_duration_ms > 0:
    print(f"Phase 3 (retransmission) time: {phase3_duration_ms} ms ({phase3_duration_s:.3f} seconds)")
print(f"Total transfer time: {total_duration_ms} ms ({total_duration_s:.3f} seconds)")
print()

if total_duration_s > 0:
    print(f"Overall data rate: {DATA_SIZE / total_duration_s:.2f} bytes/sec ({DATA_SIZE * 8 / total_duration_s / 1000:.2f} kbps)")
    print(f"Average time per packet: {total_duration_ms / num_packets:.2f} ms")
    print(f"Packet rate: {num_packets / total_duration_s:.2f} packets/sec")
    if len(corrupted_seqs) > 0:
        print(f"Retransmission overhead: {phase3_duration_s / total_duration_s * 100:.1f}%")
print("=" * 60)

# Calculate theoretical time on air for one packet (for reference)
if num_packets > 0:
    # Preamble: 16 bits, Sync: 16 bits, Packet length byte: 8 bits, Data: MAX_PACKET_SIZE*8 bits, CRC: 16 bits
    bits_per_packet = 16 + 16 + 8 + (MAX_PACKET_SIZE * 8) + 16
    time_on_air_ms = (bits_per_packet / 200000.0) * 1000.0  # 200 kbps = 200000 bps
    print(f"\nTheoretical time on air per packet ({MAX_PACKET_SIZE} bytes): {time_on_air_ms:.2f} ms")
    print(f"Theoretical total time on air: {time_on_air_ms * num_packets:.2f} ms")

print("\nTransmission test complete!")

