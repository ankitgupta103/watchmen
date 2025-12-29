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
# Generate 200-byte strings for each packet with clear identifiers
num_packets = (DATA_SIZE + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
message = b"At 3am my toaster judged my life choices, my WiFi ran away, and my coffee unionized, demanding better beans, shorter mornings, emotional support, and a written apology from the sleepy human. "
packets = []

# Pre-build all packets with 200-byte identifiable strings
for packet_num in range(num_packets):
    # Create packet identifier: "PKT_XXX: " where XXX is zero-padded packet number
    pkt_header = f"PKT_{packet_num:03d}: ".encode()
    # Fill remaining bytes with repeating message
    remaining = MAX_PAYLOAD_SIZE - len(pkt_header)
    fill_data = (message * ((remaining // len(message)) + 1))[:remaining]
    # Combine to create exactly 200-byte payload
    payload = pkt_header + fill_data
    # Add sequence number byte at the start
    packet = bytes([packet_num & 0xFF]) + payload
    packets.append(packet)

print(f"Sending {DATA_SIZE} bytes in {num_packets} packets\n")

# Phase 1: Send all packets (back-to-back for maximum speed)
print("PHASE 1: Sending packets...")
start_time = ticks_ms()

# Send all packets back-to-back
for packet in packets:
    print(f"packet:{packet}")
    sx.send(packet)

phase1_time = ticks_diff(ticks_ms(), start_time)
print(f"Phase 1: {phase1_time} ms\n")

# Phase 2: Receive corruption list
print("PHASE 2: Waiting for corruption list...")
sleep_ms(50)  # Minimal delay
corrupted_seqs = set()
timeout_start = ticks_ms()

while ticks_diff(ticks_ms(), timeout_start) < CORRUPTION_LIST_TIMEOUT_MS:
    msg, status = sx.recv(timeout_en=True, timeout_ms=300)

    if status == 0 and len(msg) > 0 and msg[0] == CORRUPTION_LIST_HEADER and len(msg) >= 2:
        count = msg[1]
        if count == 0:
            print("All packets OK")
            break
        elif len(msg) >= (2 + count):
            corrupted_seqs = set(msg[2:2+count])
            print(f"Corrupted: {sorted(corrupted_seqs)}")
            break

# Phase 3: Retransmit corrupted packets
if len(corrupted_seqs) > 0:
    print(f"\nPHASE 3: Retransmitting {len(corrupted_seqs)} packets...")
    sleep_ms(50)  # Minimal delay
    retransmit_start = ticks_ms()

    # Direct access by index for speed
    for seq in sorted(corrupted_seqs):
        if seq < len(packets):
            sx.send(packets[seq])
            print(f"packet:{packet[seq]}")

    retransmit_time = ticks_diff(ticks_ms(), retransmit_start)
    print(f"Phase 3: {retransmit_time} ms")

# Statistics
total_time = ticks_diff(ticks_ms(), start_time)
print(f"\nTotal time: {total_time} ms ({total_time/1000:.3f} s)")
print(f"Data rate: {DATA_SIZE / (total_time/1000):.2f} bytes/sec ({DATA_SIZE * 8 / (total_time/1000) / 1000:.2f} kbps)")
print("Complete!")
