# FSK High-Speed 10KB Data Transfer with Selective Retransmission

This test implements a high-speed FSK data transfer protocol with selective retransmission for efficient bulk data transfer. Unlike the per-packet ACK protocol, this test uses a batch transfer approach where all packets are sent first, then only corrupted packets are retransmitted.

## Protocol Overview

The test uses a three-phase protocol:

1. **Phase 1 - Initial Transmission**: TX device sends all 10KB packets sequentially without waiting for ACKs
2. **Phase 2 - Corruption Report**: RX device receives all packets, tracks corrupted/missing packets, and sends a corruption list to TX
3. **Phase 3 - Selective Retransmission**: TX device resends only the corrupted packets identified in the corruption list

This approach is more efficient for high-speed transfers because:
- No per-packet ACK overhead during initial transmission
- Faster overall transfer time for good channel conditions
- Only corrupted packets are retransmitted, minimizing retransmission overhead

## Test Configuration

The test uses a high-speed FSK configuration:
- **Bit Rate:** 200 kbps (high speed)
- **Frequency Deviation:** 200 kHz (matches bit rate)
- **RX Bandwidth:** 467 kHz (wide bandwidth for high speed)
- **Data Shaping:** 0.5 (Gaussian filter)
- **Preamble Length:** 16 bits (minimum for reliability)
- **Frequency:** 868.0 MHz (EU ISM band)
- **CRC:** Enabled (2 bytes)
- **Whitening:** Enabled (for better data integrity)

## Files

### `tx_fsk_10kb_highspeed.py`
Transmitter script that:
- Generates 10KB (10,240 bytes) of test data
- Sends all packets sequentially in Phase 1 (no ACK waiting)
- Receives corruption list from RX device in Phase 2
- Retransmits only corrupted packets in Phase 3
- Measures and displays:
  - Phase 1 time (initial transmission)
  - Phase 3 time (retransmission)
  - Total transfer time
  - Data rate and packet statistics

### `rx_fsk_10kb_highspeed.py`
Receiver script that:
- Receives all packets in Phase 1
- Tracks corrupted packets (CRC errors) and missing packets
- Sends corruption list to TX device in Phase 2
- Receives retransmitted packets in Phase 3
- Measures and displays:
  - Reception statistics
  - CRC error count
  - Missing packet count
  - Data integrity verification
  - Effective data rate

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
   Or if running from the example directory:
   ```python
   import rx_fsk_10kb_highspeed
   ```

2. **On the transmitter device**, run:
   ```python
   import example.fsk_10kb_highspeed.tx_fsk_10kb_highspeed
   ```
   Or if running from the example directory:
   ```python
   import tx_fsk_10kb_highspeed
   ```

**Important:** The receiver should be started first to catch all packets. The transmitter will start sending immediately.

### Expected Output

**TX Script Output:**
- Initialization status
- FSK configuration details
- Phase 1: Packet-by-packet transmission progress
- Phase 2: Corruption list reception
- Phase 3: Retransmission of corrupted packets
- Final statistics:
  - Total data sent
  - Number of packets
  - Corrupted packets count
  - Retransmitted packets count
  - Phase 1 time
  - Phase 3 time
  - Total transfer time
  - Overall data rate
  - Retransmission overhead percentage

**RX Script Output:**
- Initialization status
- FSK configuration details
- Phase 1: Packet-by-packet reception progress with RSSI
- Phase 2: Corruption list transmission
- Phase 3: Retransmission reception
- Final statistics:
  - Total data received
  - Number of packets received
  - CRC error count
  - Missing packet count
  - Retransmitted packets count
  - Phase 1 time
  - Phase 3 time
  - Total receive time
  - Effective data rate
  - Data integrity verification

## Protocol Details

### Packet Format

Each data packet has the format:
```
[sequence_number (1 byte), data (up to 254 bytes)]
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

## Performance Expectations

### Theoretical Performance (200 kbps FSK)
- **Time per packet (255 bytes):** ~10-12 ms (including overhead)
- **Total time for 10KB (41 packets):** ~410-500 ms (theoretical, without retransmission)
- **Actual time (Phase 1):** ~500-800 ms (with processing delays)
- **Total time (with retransmission):** Depends on corruption rate

### Comparison with Per-Packet ACK Protocol

| Metric | Per-Packet ACK | Selective Retransmission |
|--------|----------------|-------------------------|
| Phase 1 Time | ~1-2 seconds | ~0.5-0.8 seconds |
| Overhead | High (ACK per packet) | Low (corruption list once) |
| Best Case | Slower | Faster |
| Worst Case | Similar | Similar |
| Efficiency | Lower | Higher |

**Advantages of Selective Retransmission:**
- Faster for good channel conditions (no per-packet ACK delay)
- Lower overhead (single corruption list vs. many ACKs)
- Better suited for high-speed bulk transfers

**Disadvantages:**
- Requires more memory to store all packets for retransmission
- Slightly more complex protocol
- May have longer delay if many packets are corrupted

## Notes

- Both devices must use the same FSK parameters (frequency, bit rate, frequency deviation, RX bandwidth, sync word)
- The maximum packet size is 255 bytes, so 10KB requires ~41 packets
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
- Increase `CORRUPTION_LIST_TIMEOUT_MS` if needed
- Check that receiver is in RX mode when sending corruption list

### Retransmissions Not Received
- Check that corruption list was correctly received by transmitter
- Verify sequence numbers in corruption list are valid
- Increase `RETRANSMISSION_TIMEOUT_MS` if needed
- Check that transmitter is in RX mode when receiving retransmissions

## Configuration Options

### For Maximum Speed (Short Range)
```python
br=200.0,        # 200 kbps
freqDev=200.0,   # 200 kHz
rxBw=467.0,      # 467 kHz
```

### For Better Range (Medium Speed)
```python
br=100.0,        # 100 kbps
freqDev=100.0,   # 100 kHz
rxBw=234.3,      # 234.3 kHz
```

### For Maximum Range (Lower Speed)
```python
br=48.0,         # 48 kbps
freqDev=50.0,    # 50 kHz
rxBw=156.2,      # 156.2 kHz
```

## See Also

- `example/fsk_10kb_data_transfer/` - FSK mode 10KB test with per-packet ACK protocol
- `example/10kb_data_transfer/` - LoRa mode 10KB test (for comparison)
- `LORA_VS_FSK.md` - Detailed comparison between LoRa and FSK modes
- `README.md` - Main library documentation

