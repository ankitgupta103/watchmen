"""
RX Test: Receive 10KB of data using high-speed FSK mode
OpenMV RT1062 + Waveshare Core1262-868M

This script receives 10KB (10,240 bytes) of data and calculates the time taken.
It must be configured with the same parameters as the TX script:
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
ACK_SIZE = 1  # ACK packet size (just sequence number)
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - SEQ_NUM_SIZE  # Max data per packet

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

# Receive data with ACK protocol
received_data = bytearray()
packet_count = 0
crc_error_count = 0
expected_seq = 0  # Expected sequence number
first_packet_time = None
last_packet_time = None
acks_sent = 0

# Error code constants
ERR_CRC_MISMATCH = -7
ERR_RX_TIMEOUT = -6

print("Starting reception with ACK protocol...")
print("=" * 60)

# Receive packets until we have 10KB or timeout
timeout_ms = 300000  # 5 minute timeout (longer due to ACK protocol)
receive_start_time = ticks_ms()
last_packet_received_time = None
PACKET_STUCK_TIMEOUT_MS = 10000  # If we haven't received any packet for 10 seconds, log a warning

while len(received_data) < EXPECTED_DATA_SIZE:
    # Check for timeout
    elapsed = ticks_diff(ticks_ms(), receive_start_time)
    if elapsed > timeout_ms:
        print(f"\nTimeout waiting for data (waited {elapsed} ms)")
        break
    
    # Check if we're stuck waiting for a packet
    if last_packet_received_time is not None:
        time_since_last_packet = ticks_diff(ticks_ms(), last_packet_received_time)
        if time_since_last_packet > PACKET_STUCK_TIMEOUT_MS:
            print(f"Warning: Haven't received any packet for {time_since_last_packet} ms (waiting for seq {expected_seq})")
            last_packet_received_time = ticks_ms()  # Reset to avoid spam
    
    # Receive a packet with shorter timeout to allow more frequent checks
    msg, status = sx.recv(timeout_en=True, timeout_ms=2000)  # 2 second timeout per packet
    
    # Accept packets with status 0 (OK) or -7 (CRC_MISMATCH but data still provided)
    # In FSK variable length mode, the packet structure is: [length_byte, seq_num, data...]
    # The length byte is automatically added by the chip
    if (status == 0 or status == ERR_CRC_MISMATCH) and len(msg) >= SEQ_NUM_SIZE:
        # Debug: Print raw packet info for first few packets or when we see issues
        if packet_count < 3 or (len(msg) > 0 and ((len(msg) > 1 and msg[1] != expected_seq) or (len(msg) == 1 and msg[0] != expected_seq))):
            print(f"DEBUG: Received packet - len={len(msg)}, status={status}, first_bytes={[hex(b) for b in msg[:min(5, len(msg))]]}")
        
        # Extract sequence number and data
        # For FSK variable length mode: first byte is length, second byte is sequence number
        # But handle both cases: with length byte and without (fallback)
        if len(msg) >= (1 + SEQ_NUM_SIZE):
            # Normal case: [length_byte, seq_num, data...]
            packet_length_byte = msg[0]  # Length byte (automatically added by chip)
            packet_seq = msg[1]  # Sequence number is in second byte
            packet_data = msg[2:]  # Data starts from third byte
            
            # Verify length byte matches actual packet length (should be len(msg))
            if packet_length_byte != len(msg) and packet_count < 3:
                print(f"WARNING: Length byte mismatch - length_byte={packet_length_byte}, actual_len={len(msg)}")
        else:
            # Fallback: maybe length byte is not included? Try first byte as seq
            print(f"WARNING: Short packet (len={len(msg)}), trying first byte as sequence number")
            packet_length_byte = None
            packet_seq = msg[0]
            packet_data = msg[1:] if len(msg) > 1 else b''
        
        # Sanity check: If we're at the start and seq is way off, might be a sync issue
        # In FSK variable length mode, the first byte should be the length
        if packet_count == 0 and packet_seq > 200:
            print(f"WARNING: First packet has seq {packet_seq}, expected 0.")
            print(f"  -> Length byte: {packet_length_byte}, First 10 bytes: {[hex(b) for b in msg[:min(10, len(msg))]]}")
            # Check if maybe the length byte is being interpreted as seq
            if packet_length_byte == 0 or packet_length_byte == 1:
                print(f"  -> Length byte ({packet_length_byte}) looks like a valid seq, checking if packet is misaligned...")
            # Reject if clearly wrong
            if packet_seq > 250:  # Very unlikely to be valid
                print(f"  -> Rejecting packet due to invalid sequence number ({packet_seq})")
                continue
        
        # Update last packet received time
        last_packet_received_time = ticks_ms()
        
        # Log all received packets for debugging
        rssi = sx.getRSSI()
        status_str = "CRC_ERROR" if status == ERR_CRC_MISMATCH else "OK"
        
        # Check if this is the expected packet (handle out-of-order or duplicates)
        if packet_seq == expected_seq:
            # Record timing for first and last packet
            current_time = ticks_ms()
            if first_packet_time is None:
                first_packet_time = current_time
            
            last_packet_time = current_time
            received_data.extend(packet_data)
            packet_count += 1
            expected_seq = (expected_seq + 1) & 0xFF  # Increment expected sequence
            
            # Track CRC errors
            if status == ERR_CRC_MISMATCH:
                crc_error_count += 1
            
            print(f"Packet {packet_count} (seq {packet_seq}): Received {len(packet_data)} bytes [{status_str}] "
                  f"(Total: {len(received_data)}/{EXPECTED_DATA_SIZE} bytes) "
                  f"RSSI: {rssi:.1f} dBm")
            
            # Small delay to ensure TX module has switched to RX mode
            sleep_ms(50)
            
            # Send ACK
            ack_packet = bytes([packet_seq])
            ack_len, ack_status = sx.send(ack_packet)
            if ack_status == 0:
                acks_sent += 1
                print(f"  -> ACK sent for seq {packet_seq}")
            else:
                print(f"  -> ACK send failed: {ack_status}")
            
            # If we received the expected amount, we're done
            if len(received_data) >= EXPECTED_DATA_SIZE:
                break
        elif packet_seq < expected_seq:
            # Old/duplicate packet, send ACK anyway but don't process data
            print(f"Received duplicate/old packet (seq {packet_seq}, expected {expected_seq}) [{status_str}], sending ACK...")
            ack_packet = bytes([packet_seq])
            ack_len, ack_status = sx.send(ack_packet)
            if ack_status == 0:
                acks_sent += 1
            else:
                print(f"  -> ACK send failed: {ack_status}")
        else:
            # Out-of-order packet (future sequence)
            seq_diff = (packet_seq - expected_seq) & 0xFF
            
            # Special handling for first packet sync issues
            if packet_count == 0 and packet_seq > 200:
                # If first packet has invalid seq, try to resync
                print(f"SYNC ISSUE: First packet seq={packet_seq}, expected 0. Attempting resync...")
                # Reject this packet and wait for a valid one
                print(f"  -> Rejecting packet, will wait for seq 0")
                continue
            
            # Accept it if we've been waiting too long (skip missing packets)
            if seq_diff <= 10:  # Accept packets up to 10 ahead (increased tolerance)
                print(f"Received out-of-order packet (seq {packet_seq}, expected {expected_seq}) [{status_str}]")
                print(f"  -> Accepting and skipping {seq_diff} missing packet(s)")
                # Fill in missing data with zeros (or we could buffer this packet)
                missing_bytes = seq_diff * MAX_PAYLOAD_SIZE
                if len(received_data) + missing_bytes <= EXPECTED_DATA_SIZE:
                    received_data.extend(bytes(missing_bytes))
                    packet_count += seq_diff
                
                # Process this packet
                current_time = ticks_ms()
                if first_packet_time is None:
                    first_packet_time = current_time
                last_packet_time = current_time
                
                received_data.extend(packet_data)
                packet_count += 1
                expected_seq = (packet_seq + 1) & 0xFF
                
                if status == ERR_CRC_MISMATCH:
                    crc_error_count += 1
                
                print(f"  -> Now at seq {expected_seq}, total: {len(received_data)}/{EXPECTED_DATA_SIZE} bytes")
            else:
                # Too far ahead, log and send ACK anyway
                print(f"Received out-of-order packet (seq {packet_seq}, expected {expected_seq}) [{status_str}], too far ahead (diff={seq_diff})")
                print(f"  -> Sending ACK but not processing")
            
            # Send ACK for this packet
            sleep_ms(50)
            ack_packet = bytes([packet_seq])
            ack_len, ack_status = sx.send(ack_packet)
            if ack_status == 0:
                acks_sent += 1
                if seq_diff > 10:
                    print(f"  -> ACK sent for seq {packet_seq} (but packet too far ahead)")
            else:
                print(f"  -> ACK send failed: {ack_status}")
    elif status == ERR_RX_TIMEOUT:  # RX_TIMEOUT
        # No packet received, continue waiting
        continue
    else:
        print(f"Error receiving packet: status={status}, msg_len={len(msg) if msg else 0}")
        if len(received_data) == 0:
            # If we haven't received anything yet, continue waiting
            continue
        else:
            # If we received some data but got an error, continue waiting (don't break)
            continue

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
print(f"ACKs sent: {acks_sent}")
print(f"Packets with CRC errors: {crc_error_count}")
print(f"Packets OK: {packet_count - crc_error_count}")
if packet_count > 0:
    print(f"CRC error rate: {crc_error_count / packet_count * 100:.1f}%")
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

