"""
RX Test: High-Speed FSK 10KB Data Transfer with Selective Retransmission
OpenMV RT1062 + Waveshare Core1262-868M

This script implements a high-speed FSK data transfer protocol:
1. Receives all 10KB packets sequentially
2. Tracks corrupted packets (CRC errors or missing packets)
3. Sends corruption list to TX device
4. Receives retransmitted corrupted packets
5. Calculates total transfer time

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

# Expected data size: 10KB = 10,240 bytes
EXPECTED_DATA_SIZE = 10 * 1024  # 10,240 bytes
MAX_PACKET_SIZE = 255  # Maximum FSK packet size
SEQ_NUM_SIZE = 1  # Sequence number size in bytes
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - SEQ_NUM_SIZE  # Max data per packet

# Protocol constants
CORRUPTION_LIST_HEADER = 0xFF  # Header byte to identify corruption list packet
INITIAL_RECEIVE_TIMEOUT_MS = 60000  # Timeout for initial receive phase (60 seconds)
RETRANSMISSION_TIMEOUT_MS = 30000  # Timeout for retransmission phase (30 seconds)
PACKET_STUCK_TIMEOUT_MS = 5000  # If we haven't received any packet for 5 seconds, consider phase complete

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

# Configure FSK for HIGH SPEED DATA RATE (must match TX configuration)
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
    syncWord=[0x2D, 0x01],   # Sync word (must match TX)
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
    print("Waiting for data transmission to start...")
    print()

# Error code constants
ERR_CRC_MISMATCH = -7
ERR_RX_TIMEOUT = -6

# ============================================================================
# PHASE 1: Receive all packets and track corrupted/missing packets
# ============================================================================
print("=" * 60)
print("PHASE 1: Receiving all packets...")
print("=" * 60)

received_data = bytearray()
received_packets = {}  # Dictionary: seq_num -> (data, status, timestamp)
corrupted_seqs = set()  # Set of corrupted sequence numbers
missing_seqs = set()  # Set of missing sequence numbers
packet_count = 0
crc_error_count = 0
first_packet_time = None
last_packet_time = None

# Calculate expected number of packets
expected_num_packets = (EXPECTED_DATA_SIZE + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE

phase1_start_time = ticks_ms()
last_packet_received_time = None

# Receive packets until we have all expected packets or timeout
while len(received_packets) < expected_num_packets:
    # Check for timeout
    elapsed = ticks_diff(ticks_ms(), phase1_start_time)
    if elapsed > INITIAL_RECEIVE_TIMEOUT_MS:
        print(f"\nTimeout waiting for initial packets (waited {elapsed} ms)")
        break
    
    # Check if we're stuck (no packets received for a while)
    if last_packet_received_time is not None:
        time_since_last_packet = ticks_diff(ticks_ms(), last_packet_received_time)
        if time_since_last_packet > PACKET_STUCK_TIMEOUT_MS:
            print(f"\nNo packets received for {time_since_last_packet} ms, assuming transmission complete")
            print(f"Received {len(received_packets)}/{expected_num_packets} packets")
            break
    
    # Receive a packet with shorter timeout to allow more frequent checks
    msg, status = sx.recv(timeout_en=True, timeout_ms=2000)  # 2 second timeout per packet
    
    # Accept packets with status 0 (OK) or -7 (CRC_MISMATCH but data still provided)
    # In FSK variable length mode, the packet structure depends on chip implementation
    # It could be: [length_byte, seq_num, data...] or [seq_num, data...]
    if (status == 0 or status == ERR_CRC_MISMATCH) and len(msg) >= SEQ_NUM_SIZE:
        # Debug: Print raw packet info for first few packets to understand structure
        if packet_count < 5:
            print(f"DEBUG: Packet {packet_count + 1} - len={len(msg)}, status={status}, "
                  f"first_bytes={[hex(b) for b in msg[:min(5, len(msg))]]}")
        
        # Extract sequence number and data
        # For FSK variable length mode: first byte is length, second byte is sequence number
        # But handle both cases: with length byte and without (fallback)
        packet_seq = None
        packet_data = None
        packet_length_byte = None
        
        if len(msg) >= (1 + SEQ_NUM_SIZE):
            # Normal case: [length_byte, seq_num, data...]
            packet_length_byte = msg[0]  # Length byte (automatically added by chip)
            packet_seq = msg[1]  # Sequence number is in second byte
            packet_data = msg[2:]  # Data starts from third byte
            
            # Verify length byte matches actual packet length (should be len(msg))
            if packet_count < 5:
                print(f"DEBUG: Packet {packet_count + 1} - len={len(msg)}, length_byte={packet_length_byte}, "
                      f"seq={packet_seq}, first_bytes={[hex(b) for b in msg[:min(5, len(msg))]]}")
            
            if packet_length_byte != len(msg) and packet_count < 10:
                print(f"WARNING: Length byte mismatch - length_byte={packet_length_byte}, actual_len={len(msg)}")
            
            # Sanity check: If sequence number seems wrong, try alternative parsing
            if packet_count == 0 and packet_seq > 200:
                print(f"WARNING: First packet has seq {packet_seq}, expected 0.")
                print(f"  -> Length byte: {packet_length_byte}, First 10 bytes: {[hex(b) for b in msg[:min(10, len(msg))]]}")
                # Check if maybe the length byte is being interpreted as seq
                if packet_length_byte == 0 or packet_length_byte == 1:
                    print(f"  -> Length byte ({packet_length_byte}) looks like a valid seq, checking if packet is misaligned...")
                # Try alternative: maybe length byte is not included?
                if len(msg) >= SEQ_NUM_SIZE:
                    alt_seq = msg[0]
                    if alt_seq <= expected_num_packets:
                        print(f"  -> Trying alternative: first byte as seq = {alt_seq}")
                        packet_seq = alt_seq
                        packet_data = msg[1:]
                        packet_length_byte = None
        else:
            # Fallback: maybe length byte is not included? Try first byte as seq
            print(f"WARNING: Short packet (len={len(msg)}), trying first byte as sequence number")
            packet_length_byte = None
            packet_seq = msg[0]
            packet_data = msg[1:] if len(msg) > 1 else b''
        
        # Validate sequence number
        if packet_seq is None:
            print(f"WARNING: Could not extract sequence number, skipping packet")
            continue
        
        if packet_seq > 255:
            print(f"WARNING: Invalid sequence number {packet_seq} (>255), skipping packet")
            continue
        
        # Update last packet received time
        last_packet_received_time = ticks_ms()
        current_time = ticks_ms()
        
        if first_packet_time is None:
            first_packet_time = current_time
        
        last_packet_time = current_time
        
        # Store packet information
        received_packets[packet_seq] = (packet_data, status, current_time)
        
        # Track CRC errors
        if status == ERR_CRC_MISMATCH:
            crc_error_count += 1
            corrupted_seqs.add(packet_seq)
        
        packet_count += 1
        rssi = sx.getRSSI()
        status_str = "CRC_ERROR" if status == ERR_CRC_MISMATCH else "OK"
        
        if packet_count % 10 == 0 or packet_count <= 3:
            print(f"Packet {packet_count} (seq {packet_seq}): Received {len(packet_data)} bytes [{status_str}] "
                  f"(Total packets: {len(received_packets)}/{expected_num_packets}) "
                  f"RSSI: {rssi:.1f} dBm")
    
    elif status == ERR_RX_TIMEOUT:  # RX_TIMEOUT
        # No packet received, continue waiting
        continue
    else:
        # Error receiving, log and continue
        if len(received_packets) == 0:
            # If we haven't received anything yet, continue waiting
            continue
        else:
            # If we received some data but got an error, continue waiting
            continue

phase1_end_time = ticks_ms()
phase1_duration_ms = ticks_diff(phase1_end_time, phase1_start_time)
phase1_duration_s = phase1_duration_ms / 1000.0

# Identify missing packets
for seq in range(expected_num_packets):
    if seq not in received_packets:
        missing_seqs.add(seq)

# Combine corrupted and missing packets
all_corrupted_seqs = corrupted_seqs | missing_seqs

print()
print(f"Phase 1 complete: Received {len(received_packets)}/{expected_num_packets} packets in {phase1_duration_ms} ms ({phase1_duration_s:.3f} seconds)")
print(f"CRC errors: {crc_error_count}")
print(f"Missing packets: {len(missing_seqs)}")
print(f"Total corrupted/missing packets: {len(all_corrupted_seqs)}")
if len(all_corrupted_seqs) > 0:
    print(f"Corrupted/missing sequence numbers: {sorted(all_corrupted_seqs)}")
print()

# ============================================================================
# PHASE 2: Send corruption list to TX device
# ============================================================================
print("=" * 60)
print("PHASE 2: Sending corruption list to TX device...")
print("=" * 60)

# Create corruption list packet: [0xFF, count, seq1, seq2, ...]
# Convert to bytes immediately to avoid buffer protocol issues
corruption_list_bytes = bytes([CORRUPTION_LIST_HEADER, len(all_corrupted_seqs)])
if len(all_corrupted_seqs) > 0:
    corruption_list_bytes += bytes(sorted(all_corrupted_seqs))

# Small delay before sending
sleep_ms(100)

# Send corruption list
corruption_list_len, status = sx.send(corruption_list_bytes)

if status == 0:
    print(f"Corruption list sent: {len(all_corrupted_seqs)} corrupted/missing packet(s)")
    if len(all_corrupted_seqs) > 0:
        print(f"Sequence numbers: {sorted(all_corrupted_seqs)}")
else:
    print(f"Error sending corruption list: {status}")

print()

# ============================================================================
# PHASE 3: Receive retransmitted corrupted packets
# ============================================================================
phase3_start_time = ticks_ms()
retransmitted_count = 0

if len(all_corrupted_seqs) > 0:
    print("=" * 60)
    print(f"PHASE 3: Receiving {len(all_corrupted_seqs)} retransmitted packet(s)...")
    print("=" * 60)
    
    remaining_corrupted = all_corrupted_seqs.copy()
    last_retransmission_time = None
    
    while len(remaining_corrupted) > 0:
        # Check for timeout
        elapsed = ticks_diff(ticks_ms(), phase3_start_time)
        if elapsed > RETRANSMISSION_TIMEOUT_MS:
            print(f"\nTimeout waiting for retransmissions (waited {elapsed} ms)")
            print(f"Still missing: {sorted(remaining_corrupted)}")
            break
        
        # Check if we're stuck
        if last_retransmission_time is not None:
            time_since_last = ticks_diff(ticks_ms(), last_retransmission_time)
            if time_since_last > PACKET_STUCK_TIMEOUT_MS:
                print(f"\nNo retransmissions received for {time_since_last} ms, assuming complete")
                print(f"Still missing: {sorted(remaining_corrupted)}")
                break
        
        # Receive a retransmitted packet
        msg, status = sx.recv(timeout_en=True, timeout_ms=2000)
        
        if (status == 0 or status == ERR_CRC_MISMATCH) and len(msg) >= SEQ_NUM_SIZE:
            # Extract sequence number using same logic as Phase 1
            packet_seq = None
            packet_data = None
            
            if len(msg) >= (1 + SEQ_NUM_SIZE):
                first_byte = msg[0]
                if abs(first_byte - len(msg)) <= 2:
                    # Format: [length_byte, seq_num, data...]
                    packet_seq = msg[1]
                    packet_data = msg[2:]
                else:
                    # Format: [seq_num, data...]
                    packet_seq = msg[0]
                    packet_data = msg[1:]
            else:
                packet_seq = msg[0]
                packet_data = msg[1:] if len(msg) > 1 else b''
            
            if packet_seq is None or packet_seq > 255:
                continue
            
            # Check if this is a corrupted packet we're waiting for
            if packet_seq in remaining_corrupted:
                last_retransmission_time = ticks_ms()
                received_packets[packet_seq] = (packet_data, status, last_retransmission_time)
                remaining_corrupted.remove(packet_seq)
                retransmitted_count += 1
                
                status_str = "CRC_ERROR" if status == ERR_CRC_MISMATCH else "OK"
                rssi = sx.getRSSI()
                print(f"Retransmitted packet seq {packet_seq}: Received {len(packet_data)} bytes [{status_str}] "
                      f"RSSI: {rssi:.1f} dBm "
                      f"({retransmitted_count}/{len(all_corrupted_seqs)} received)")
                
                if status == ERR_CRC_MISMATCH:
                    # Still corrupted after retransmission
                    print(f"  Warning: Packet seq {packet_seq} still has CRC error after retransmission")
        
        elif status == ERR_RX_TIMEOUT:
            continue
        else:
            continue
    
    phase3_end_time = ticks_ms()
    phase3_duration_ms = ticks_diff(phase3_end_time, phase3_start_time)
    phase3_duration_s = phase3_duration_ms / 1000.0
    
    print()
    print(f"Phase 3 complete: Received {retransmitted_count}/{len(all_corrupted_seqs)} retransmitted packets "
          f"in {phase3_duration_ms} ms ({phase3_duration_s:.3f} seconds)")
    if len(remaining_corrupted) > 0:
        print(f"Warning: Still missing {len(remaining_corrupted)} packet(s): {sorted(remaining_corrupted)}")
else:
    print("=" * 60)
    print("PHASE 3: No corrupted packets to receive")
    print("=" * 60)
    phase3_duration_ms = 0
    phase3_duration_s = 0.0

print()

# ============================================================================
# Reconstruct received data in order
# ============================================================================
print("Reconstructing received data...")
for seq in range(expected_num_packets):
    if seq in received_packets:
        packet_data, packet_status, packet_time = received_packets[seq]
        received_data.extend(packet_data)
    else:
        # Missing packet - fill with zeros (or could use error marker)
        missing_bytes = MAX_PAYLOAD_SIZE
        if seq == expected_num_packets - 1:
            # Last packet might be smaller
            remaining = EXPECTED_DATA_SIZE - len(received_data)
            missing_bytes = remaining
        received_data.extend(bytes(missing_bytes))
        print(f"Warning: Packet seq {seq} still missing, filled with zeros")

total_received = len(received_data)

# ============================================================================
# Calculate total statistics
# ============================================================================
total_end_time = ticks_ms()
total_duration_ms = ticks_diff(total_end_time, phase1_start_time)
total_duration_s = total_duration_ms / 1000.0

reception_duration_ms = 0
reception_duration_s = 0.0
if first_packet_time is not None and last_packet_time is not None:
    reception_duration_ms = ticks_diff(last_packet_time, first_packet_time)
    reception_duration_s = reception_duration_ms / 1000.0

print()
print("=" * 60)
print("RECEPTION COMPLETE")
print("=" * 60)
print(f"Total data received: {total_received} bytes ({total_received / 1024:.2f} KB)")
print(f"Expected data size: {EXPECTED_DATA_SIZE} bytes ({EXPECTED_DATA_SIZE / 1024:.2f} KB)")
print(f"Number of packets received: {len(received_packets)}/{expected_num_packets}")
print(f"Packets with CRC errors: {crc_error_count}")
print(f"Missing packets: {len(missing_seqs)}")
print(f"Retransmitted packets: {retransmitted_count}")
print(f"Data completeness: {total_received / EXPECTED_DATA_SIZE * 100:.1f}%")
print()
print(f"Phase 1 (initial receive) time: {phase1_duration_ms} ms ({phase1_duration_s:.3f} seconds)")
if phase3_duration_ms > 0:
    print(f"Phase 3 (retransmission) time: {phase3_duration_ms} ms ({phase3_duration_s:.3f} seconds)")
print(f"Total receive time: {total_duration_ms} ms ({total_duration_s:.3f} seconds)")
print()

if reception_duration_s > 0:
    print(f"Effective data rate: {total_received / reception_duration_s:.2f} bytes/sec "
          f"({total_received * 8 / reception_duration_s / 1000:.2f} kbps)")
    print(f"Average time per packet: {reception_duration_ms / len(received_packets) if len(received_packets) > 0 else 0:.2f} ms")
    print(f"Packet rate: {len(received_packets) / reception_duration_s if reception_duration_s > 0 else 0:.2f} packets/sec")
print("=" * 60)

# Verify data integrity (check pattern)
if total_received == EXPECTED_DATA_SIZE:
    print("\nVerifying data integrity...")
    data_correct = True
    errors_found = 0
    for i in range(min(1000, total_received)):  # Check first 1000 bytes as sample
        expected_byte = i % 256
        if received_data[i] != expected_byte:
            if errors_found < 10:  # Only print first 10 errors
                print(f"Data mismatch at position {i}: expected {expected_byte}, got {received_data[i]}")
            errors_found += 1
            data_correct = False
    
    if data_correct:
        print("Data verification: PASSED (sample check)")
    else:
        print(f"Data verification: FAILED ({errors_found} errors found in sample)")
else:
    print(f"\nWarning: Received {total_received} bytes, expected {EXPECTED_DATA_SIZE} bytes")

print("\nReception test complete!")

