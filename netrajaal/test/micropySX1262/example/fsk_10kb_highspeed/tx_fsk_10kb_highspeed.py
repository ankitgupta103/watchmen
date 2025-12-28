"""
TX: High-Speed FSK 10KB Data Transfer with Selective Retransmission
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

DATA_SIZE = 10 * 1024  # 10KB
MAX_PAYLOAD_SIZE = 200  # bytes per packet
SEQ_NUM_SIZE = 1
CORRUPTION_LIST_HEADER = 0xFF
CORRUPTION_LIST_TIMEOUT_MS = 5000

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

print("SX1262 ready. Generating test data...")
test_data = bytes([i % 256 for i in range(DATA_SIZE)])
num_packets = (DATA_SIZE + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
print(f"Sending {DATA_SIZE} bytes in {num_packets} packets\n")

# Phase 1: Send all packets
print("PHASE 1: Sending packets...")
start_time = ticks_ms()
packets = []

for packet_num in range(num_packets):
    start_idx = packet_num * MAX_PAYLOAD_SIZE
    end_idx = min(start_idx + MAX_PAYLOAD_SIZE, DATA_SIZE)
    chunk = test_data[start_idx:end_idx]
    packet = bytes([packet_num & 0xFF]) + chunk
    packets.append((packet_num & 0xFF, packet, chunk))
    sx.send(packet)  # No delays - maximum speed

phase1_time = ticks_diff(ticks_ms(), start_time)
print(f"Phase 1: {phase1_time} ms\n")

# Phase 2: Receive corruption list
print("PHASE 2: Waiting for corruption list...")
sleep_ms(100)  # Minimal delay for receiver processing
corrupted_seqs = set()
corruption_list_received = False
timeout_start = ticks_ms()

while ticks_diff(ticks_ms(), timeout_start) < CORRUPTION_LIST_TIMEOUT_MS:
    msg, status = sx.recv(timeout_en=True, timeout_ms=500)
    
    if status == 0 and len(msg) > 0 and msg[0] == CORRUPTION_LIST_HEADER:
        if len(msg) >= 2:
            count = msg[1]
            if count == 0:
                corrupted_seqs = set()
                corruption_list_received = True
                print("All packets received successfully")
                break
            elif len(msg) >= (2 + count):
                corrupted_seqs = set(msg[2:2+count])
                corruption_list_received = True
                print(f"Corrupted packets: {sorted(corrupted_seqs)}")
                break

if not corruption_list_received:
    print("No corruption list received, assuming success")
    corrupted_seqs = set()

# Phase 3: Retransmit corrupted packets
if len(corrupted_seqs) > 0:
    print(f"\nPHASE 3: Retransmitting {len(corrupted_seqs)} packets...")
    sleep_ms(100)  # Minimal delay for receiver
    retransmit_start = ticks_ms()
    
    for seq in sorted(corrupted_seqs):
        for stored_seq, packet, chunk in packets:
            if stored_seq == seq:
                sx.send(packet)  # No delays - maximum speed
                break
    
    retransmit_time = ticks_diff(ticks_ms(), retransmit_start)
    print(f"Phase 3: {retransmit_time} ms")

# Statistics
total_time = ticks_diff(ticks_ms(), start_time)
print(f"\nTotal time: {total_time} ms ({total_time/1000:.3f} s)")
print(f"Data rate: {DATA_SIZE / (total_time/1000):.2f} bytes/sec ({DATA_SIZE * 8 / (total_time/1000) / 1000:.2f} kbps)")
print("Complete!")
