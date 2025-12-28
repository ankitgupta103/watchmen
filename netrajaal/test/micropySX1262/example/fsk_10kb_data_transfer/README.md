# FSK High-Speed 10KB Data Transfer Test

This test sends 10KB of data using high-speed FSK (GFSK) mode and measures the transmission time. FSK mode is optimized for high-speed data transmission compared to LoRa mode.

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

## Why FSK for High-Speed Transfer?

FSK (Frequency Shift Keying) mode offers:
- **Higher Data Rates:** Up to 300 kbps (vs ~50 kbps max for LoRa)
- **Faster Transmission:** Lower air time per packet
- **Better for Large Data:** More efficient for bulk data transfer

**Trade-off:** FSK has shorter range compared to LoRa, making it ideal for short to medium-range high-speed transfers.

## Files

### `tx_fsk_10kb_test.py`
Transmitter script that:
- Generates 10KB (10,240 bytes) of test data
- Sends data in packets (max 255 bytes per packet = ~41 packets)
- Uses ACK protocol for reliable delivery
- Measures the total time to send all data
- Displays transmission statistics (data rate, packet rate, etc.)

### `rx_fsk_10kb_test.py`
Receiver script that:
- Receives 10KB of data with the same FSK configuration
- Sends ACK packets for each received packet
- Measures the time from first packet to last packet
- Calculates effective data rate
- Verifies data integrity

## Usage

### Setup

1. Connect two OpenMV RT1062 boards with Waveshare Core1262-868M modules
2. Ensure both modules are powered and antennas are connected
3. Place devices within range (FSK at 200 kbps: typically 100-300 meters line-of-sight)
4. Copy both scripts to their respective boards

### Running the Test

1. **On the receiver device**, run:
   ```python
   import example.fsk_10kb_data_transfer.rx_fsk_10kb_test
   ```
   Or if running from the example directory:
   ```python
   import rx_fsk_10kb_test
   ```

2. **On the transmitter device**, run:
   ```python
   import example.fsk_10kb_data_transfer.tx_fsk_10kb_test
   ```
   Or if running from the example directory:
   ```python
   import tx_fsk_10kb_test
   ```

**Important:** The receiver should be started first to catch all packets. The transmitter will start sending immediately.

### Expected Output

**TX Script Output:**
- Initialization status
- FSK configuration details
- Data generation confirmation
- Packet-by-packet transmission progress with ACK confirmation
- Final statistics:
  - Total data sent
  - Number of packets
  - Total retries
  - Total transmission time
  - Data rate (bytes/sec and kbps)
  - Time per packet
  - Packet rate
  - Theoretical time on air

**RX Script Output:**
- Initialization status
- FSK configuration details
- Packet-by-packet reception progress with RSSI
- ACK confirmation for each packet
- Final statistics:
  - Total data received
  - Number of packets received
  - CRC error count
  - Reception duration (first to last packet)
  - Effective data rate
  - Data integrity verification

## Performance Expectations

### Theoretical Performance (200 kbps FSK)
- **Time per packet (255 bytes):** ~10-12 ms (including overhead)
- **Total time for 10KB:** ~500-600 ms (theoretical, without ACK delays)
- **Actual time:** ~1-2 seconds (with ACK protocol and processing delays)

### Comparison with LoRa
- **LoRa (SF5, BW500kHz):** ~2-3 seconds for 10KB
- **FSK (200 kbps):** ~1-2 seconds for 10KB
- **Speed improvement:** ~2x faster with FSK

## Notes

- Both devices must use the same FSK parameters (frequency, bit rate, frequency deviation, RX bandwidth, sync word)
- The maximum packet size is 255 bytes, so 10KB requires ~41 packets
- Actual transmission time depends on:
  - Radio conditions and distance
  - ACK protocol overhead
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

### CRC Errors
- Reduce distance between devices
- Check antenna connections
- Try reducing bit rate for better reliability
- Increase TX power (if within regulatory limits)

### Timeout Issues
- Ensure receiver is started before transmitter
- Increase timeout values if needed
- Check that devices are within range

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
rxBw=156.2,     # 156.2 kHz
```

## See Also

- `example/10kb_data_transfer/` - LoRa mode 10KB test (for comparison)
- `LORA_VS_FSK.md` - Detailed comparison between LoRa and FSK modes
- `README.md` - Main library documentation

