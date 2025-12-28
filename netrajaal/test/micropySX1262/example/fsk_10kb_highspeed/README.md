# FSK High-Speed 10KB Data Transfer with Selective Retransmission

A simplified, high-performance FSK data transfer test implementing selective retransmission for efficient bulk data transfer. This test uses a batch transfer approach where all packets are sent first, then only corrupted packets are retransmitted.

## Protocol Overview

The test uses a three-phase protocol:

1. **Phase 1 - Initial Transmission**: TX sends all 10KB packets sequentially without waiting for ACKs
2. **Phase 2 - Corruption Report**: RX receives all packets, tracks corrupted/missing packets, and sends a corruption list to TX
3. **Phase 3 - Selective Retransmission**: TX resends only the corrupted packets identified in the corruption list

This approach is more efficient than per-packet ACK protocols because:
- No per-packet ACK overhead during initial transmission
- Faster overall transfer time for good channel conditions
- Only corrupted packets are retransmitted, minimizing retransmission overhead

## Test Configuration

High-speed FSK configuration:
- **Bit Rate:** 200 kbps
- **Frequency Deviation:** 200 kHz
- **RX Bandwidth:** 467 kHz
- **Data Shaping:** 0.5 (Gaussian filter)
- **Preamble Length:** 16 bits
- **Frequency:** 868.0 MHz (EU ISM band)
- **CRC:** Enabled (2 bytes)
- **Whitening:** Enabled
- **Packet Size:** 200 bytes payload + 1 byte sequence number

## Files

### `tx_fsk_10kb_highspeed.py`
Transmitter script (~110 lines):
- Generates 10KB (10,240 bytes) of test data
- Sends all packets sequentially in Phase 1 (back-to-back, no delays)
- Receives corruption list from RX device in Phase 2
- Retransmits only corrupted packets in Phase 3
- Measures and displays total transfer time and data rate

### `rx_fsk_10kb_highspeed.py`
Receiver script (~125 lines):
- Receives all packets in Phase 1
- Tracks corrupted packets (CRC errors) and missing packets
- Sends corruption list to TX device in Phase 2
- Receives retransmitted packets in Phase 3
- Reconstructs data and verifies integrity
- Measures and displays effective data rate

## Usage

### Setup

1. Connect two OpenMV RT1062 boards with Waveshare Core1262-868M modules
2. Ensure both modules are powered and antennas are connected
3. Place devices within range (FSK at 200 kbps: typically 100-300 meters line-of-sight)
4. Copy both scripts to their respective boards

### Running the Test

1. **On the receiver device**, run:
   ```python
   import example.fsk_10kb_highspeed.rx_fsk_10kb_highspeed
   ```

2. **On the transmitter device**, run:
   ```python
   import example.fsk_10kb_highspeed.tx_fsk_10kb_highspeed
   ```

**Important:** The receiver should be started first to catch all packets.

### Expected Output

**TX Script Output:**
```
Initializing SX1262...
SX1262 ready. Generating test data...
Sending 10240 bytes in 52 packets

PHASE 1: Sending packets...
Phase 1: 1182 ms

PHASE 2: Waiting for corruption list...
Corrupted packets: [3, 9, 12, 16, 19, 21, 23, 26, 33, 39, 45, 51]

PHASE 3: Retransmitting 12 packets...
Phase 3: 259 ms

Total time: 2767 ms (2.767 s)
Data rate: 3700.76 bytes/sec (29.61 kbps)
Complete!
```

**RX Script Output:**
```
Initializing SX1262...
SX1262 ready. Waiting for data...

PHASE 1: Receiving packets...
Phase 1: 45/52 packets in 1200 ms

PHASE 2: Sending corruption list (12 packets)...
PHASE 3: Receiving 12 retransmissions...
Phase 3: 250 ms

Total time: 1500 ms (1.500 s)
Data rate: 6826.67 bytes/sec (54.61 kbps)
Data completeness: 100.0%
Data verification: PASSED
Complete!
```

## Protocol Details

### Packet Format

Each data packet has the format:
```
[sequence_number (1 byte), data (200 bytes)]
```

The sequence number is a single byte (0-255), allowing up to 255 packets per transfer.

### Corruption List Format

The corruption list packet has the format:
```
[0xFF (header), count (1 byte), seq1, seq2, ..., seqN]
```

- Header byte `0xFF` identifies this as a corruption list packet
- Count byte indicates how many corrupted sequence numbers follow
- Sequence numbers are the corrupted/missing packet sequence numbers

### Error Detection

The receiver identifies corrupted packets by:
1. **CRC Errors**: Packets received with CRC mismatch (status = -7)
2. **Missing Packets**: Sequence gaps indicating packets that were never received

Both types are included in the corruption list sent to the transmitter.

## Performance

### Typical Performance

- **Phase 1 (initial send):** ~1.2-1.5 seconds for 52 packets
- **Phase 2 (corruption list):** ~100-200 ms
- **Phase 3 (retransmission):** ~200-300 ms for typical corruption rates
- **Total time:** ~1.5-2.5 seconds for 10KB transfer
- **Effective data rate:** 30-60 kbps (application level)

### Why Not 200-300 kbps?

The radio bit rate is 200 kbps, but application-level throughput is lower due to:
- **Protocol overhead**: Sequence numbers, corruption list exchange
- **Processing overhead**: Python/MicroPython processing between packets
- **Packet structure**: Each packet has overhead (preamble, sync, CRC)
- **Sequential sending**: Packets sent one at a time with processing

To approach 200-300 kbps, you would need:
- Hardware-level optimization (C code, not Python)
- Larger packet sizes (but may reduce reliability)
- Simpler protocol (no error checking)
- Continuous transmission mode (if supported)

### Comparison with Per-Packet ACK Protocol

| Metric | Per-Packet ACK | Selective Retransmission |
|--------|----------------|-------------------------|
| Phase 1 Time | ~2-3 seconds | ~1.2-1.5 seconds |
| Overhead | High (ACK per packet) | Low (corruption list once) |
| Best Case | Slower | Faster |
| Worst Case | Similar | Similar |
| Efficiency | Lower | Higher |

## Code Features

- **Simple and Clean**: ~110-125 lines per file
- **Optimized**: Pre-built packets, direct array access, minimal delays
- **Efficient**: Back-to-back packet transmission, streamlined loops
- **Reliable**: CRC checking, selective retransmission, data verification

## Notes

- Both devices must use the same FSK parameters (frequency, bit rate, frequency deviation, RX bandwidth, sync word)
- The maximum packet size is 255 bytes, so 10KB requires ~52 packets (200 bytes payload each)
- Actual transmission time depends on:
  - Radio conditions and distance
  - Corruption rate
  - Processing delays
- FSK mode provides RSSI but not SNR (unlike LoRa)
- Range is shorter than LoRa: typically 100-300 meters at 200 kbps
- For longer range, reduce bit rate (e.g., 48-100 kbps)
- For maximum speed, use 200-300 kbps but expect shorter range

## Troubleshooting

### No Packets Received
- Check that both devices use identical FSK parameters
- Verify frequency matches (868.0 MHz)
- Ensure sync word matches: `[0x2D, 0x01]`
- Check antenna connections
- Reduce distance between devices
- Try reducing bit rate (e.g., 100 kbps) for better range

### High Corruption Rate
- Reduce distance between devices
- Check antenna connections
- Try reducing bit rate for better reliability
- Increase TX power (if within regulatory limits)
- Check for interference sources

### Corruption List Not Received
- Ensure receiver completes Phase 1 before transmitter times out
- Check that transmitter is in RX mode when corruption list is sent
- Increase delays if needed (but will reduce speed)

### Low Data Rate
- This is normal for Python/MicroPython implementation
- Protocol overhead and processing delays are inherent
- For higher speeds, consider C/C++ implementation
- Larger packet sizes may help (but test reliability)

## Configuration Options

### For Maximum Speed (Short Range)
```python
br=200.0,        # 200 kbps
freqDev=200.0,   # 200 kHz
rxBw=467.0,      # 467 kHz
MAX_PAYLOAD_SIZE = 200  # bytes
```

### For Better Range (Medium Speed)
```python
br=100.0,        # 100 kbps
freqDev=100.0,   # 100 kHz
rxBw=234.3,      # 234.3 kHz
MAX_PAYLOAD_SIZE = 200  # bytes
```

### For Maximum Range (Lower Speed)
```python
br=48.0,         # 48 kbps
freqDev=50.0,    # 50 kHz
rxBw=156.2,      # 156.2 kHz
MAX_PAYLOAD_SIZE = 200  # bytes
```

## See Also

- `example/fsk_10kb_data_transfer/` - FSK mode 10KB test with per-packet ACK protocol
- `example/10kb_data_transfer/` - LoRa mode 10KB test (for comparison)
- `LORA_VS_FSK.md` - Detailed comparison between LoRa and FSK modes
- `README.md` - Main library documentation
