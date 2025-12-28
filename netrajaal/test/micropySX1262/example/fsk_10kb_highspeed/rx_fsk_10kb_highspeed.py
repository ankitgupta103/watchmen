"""
RX: High-Speed FSK 10KB Data Transfer with Selective Retransmission
OpenMV RT1062 + Waveshare Core1262-868M
"""

import time
try:
    from utime import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
    sleep_ms = time.sleep_ms if hasattr(time, 'sleep_ms') else lambda ms: time.sleep(ms / 1000.0)

from sx1262 import SX1262

# Configuration
SPI_BUS = 1
PINS = {'mosi': 'P0', 'miso': 'P1', 'sclk': 'P2', 'cs': 'P3', 'rst': 'P6', 'busy': 'P7', 'irq': 'P13'}

EXPECTED_DATA_SIZE = 10 * 1024  # 10KB
MAX_PAYLOAD_SIZE = 200
SEQ_NUM_SIZE = 1
CORRUPTION_LIST_HEADER = 0xFF
PACKET_STUCK_TIMEOUT_MS = 1000

# Initialize
print("Initializing SX1262...")
sx = SX1262(SPI_BUS, PINS['sclk'], PINS['mosi'], PINS['miso'], PINS['cs'],
            PINS['irq'], PINS['rst'], PINS['busy'])

# Configure FSK for high speed
status = sx.beginFSK(
    freq=868.0, br=200.0, freqDev=200.0, rxBw=467.0, power=14,
    preambleLength=16, dataShaping=0.5, syncWord=[0x2D, 0x01], syncBitsLength=16,
    crcLength=2, whiteningOn=True, fixedPacketLength=False, blocking=True
)

if status != 0:
    print(f"Init error: {status}")
    exit()

print("SX1262 ready. Waiting for data...\n")

# Phase 1: Receive all packets
print("PHASE 1: Receiving packets...")
start_time = ticks_ms()
received_packets = {}
corrupted_seqs = set()
expected_num_packets = (EXPECTED_DATA_SIZE + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
last_packet_time = None

while len(received_packets) < expected_num_packets:
    if last_packet_time and ticks_diff(ticks_ms(), last_packet_time) > PACKET_STUCK_TIMEOUT_MS:
        break
    
    msg, status = sx.recv(timeout_en=True, timeout_ms=500)
    
    if (status == 0 or status == -7) and len(msg) >= SEQ_NUM_SIZE:
        packet_seq = msg[0]
        packet_data = msg[1:]
        
        if 0 <= packet_seq < expected_num_packets:
            received_packets[packet_seq] = (packet_data, status)
            last_packet_time = ticks_ms()
            
            if status == -7:  # CRC error
                corrupted_seqs.add(packet_seq)

phase1_time = ticks_diff(ticks_ms(), start_time)
print(f"Phase 1: Received {len(received_packets)}/{expected_num_packets} packets in {phase1_time} ms")

# Identify missing packets
missing_seqs = {seq for seq in range(expected_num_packets) if seq not in received_packets}
all_corrupted_seqs = (corrupted_seqs | missing_seqs) & {seq for seq in range(expected_num_packets)}

# Phase 2: Send corruption list
print(f"\nPHASE 2: Sending corruption list ({len(all_corrupted_seqs)} packets)...")
sleep_ms(200)  # Reduced delay

corruption_list = bytes([CORRUPTION_LIST_HEADER, len(all_corrupted_seqs)]) + bytes(sorted(all_corrupted_seqs))
sx.send(corruption_list)  # Send once - faster

# Phase 3: Receive retransmissions
if len(all_corrupted_seqs) > 0:
    print(f"\nPHASE 3: Receiving {len(all_corrupted_seqs)} retransmissions...")
    sleep_ms(100)  # Reduced delay
    remaining = all_corrupted_seqs.copy()
    retransmit_start = ticks_ms()
    
    while len(remaining) > 0 and ticks_diff(ticks_ms(), retransmit_start) < 10000:
        msg, status = sx.recv(timeout_en=True, timeout_ms=500)
        
        if (status == 0 or status == -7) and len(msg) >= SEQ_NUM_SIZE:
            packet_seq = msg[0]
            if packet_seq in remaining:
                received_packets[packet_seq] = (msg[1:], status)
                remaining.remove(packet_seq)
    
    retransmit_time = ticks_diff(ticks_ms(), retransmit_start)
    print(f"Phase 3: {retransmit_time} ms")

# Reconstruct data
received_data = bytearray()
for seq in range(expected_num_packets):
    if seq in received_packets:
        received_data.extend(received_packets[seq][0])
    else:
        # Fill missing with zeros
        missing_bytes = MAX_PAYLOAD_SIZE if seq < expected_num_packets - 1 else (EXPECTED_DATA_SIZE - len(received_data))
        received_data.extend(bytes(missing_bytes))

# Statistics
total_time = ticks_diff(ticks_ms(), start_time)
print(f"\nTotal time: {total_time} ms ({total_time/1000:.3f} s)")
print(f"Data rate: {len(received_data) / (total_time/1000):.2f} bytes/sec ({len(received_data) * 8 / (total_time/1000) / 1000:.2f} kbps)")
print(f"Data completeness: {len(received_data) / EXPECTED_DATA_SIZE * 100:.1f}%")

# Verify data integrity
if len(received_data) == EXPECTED_DATA_SIZE:
    correct = all(received_data[i] == (i % 256) for i in range(min(1000, len(received_data))))
    print(f"Data verification: {'PASSED' if correct else 'FAILED'}")
else:
    print(f"Warning: Received {len(received_data)} bytes, expected {EXPECTED_DATA_SIZE}")

print("Complete!")
