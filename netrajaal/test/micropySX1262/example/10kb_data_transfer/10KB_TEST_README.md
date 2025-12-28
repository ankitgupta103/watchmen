# 10KB Data Rate Test

This test sends 10KB of data at the highest possible LoRa data rate and measures the transmission time.

## Test Configuration

The test uses the highest data rate LoRa configuration:
- **Spreading Factor:** 5 (lowest for highest data rate)
- **Bandwidth:** 500 kHz (highest available)
- **Coding Rate:** 5 (4/5, lowest for highest data rate)
- **Preamble Length:** 8 (minimum)
- **Frequency:** 868.0 MHz
- **CRC:** Enabled

## Files

### `tx_10kb_test.py`
Transmitter script that:
- Generates 10KB (10,240 bytes) of test data
- Sends data in packets (max 255 bytes per packet = ~41 packets)
- Measures the total time to send all data
- Displays transmission statistics (data rate, packet rate, etc.)

### `rx_10kb_test.py`
Receiver script that:
- Receives 10KB of data with the same configuration
- Measures the time from first packet to last packet
- Calculates effective data rate
- Verifies data integrity

## Usage

### Setup

1. Connect two OpenMV RT1062 boards with Waveshare Core1262-868M modules
2. Ensure both modules are powered and antennas are connected
3. Copy both scripts to their respective boards

### Running the Test

1. **On the receiver device**, run:
   ```python
   import rx_10kb_test
   ```

2. **On the transmitter device**, run:
   ```python
   import tx_10kb_test
   ```

The transmitter will start sending immediately. The receiver should be running first to catch all packets.

### Expected Output

**TX Script Output:**
- Initialization status
- Data generation confirmation
- Packet-by-packet transmission progress
- Final statistics:
  - Total data sent
  - Number of packets
  - Total transmission time
  - Data rate (bytes/sec and kbps)
  - Time per packet
  - Packet rate

**RX Script Output:**
- Initialization status
- Packet-by-packet reception progress with RSSI/SNR
- Final statistics:
  - Total data received
  - Number of packets received
  - Reception duration (first to last packet)
  - Effective data rate
  - Data integrity verification

## Notes

- Both devices must use the same LoRa parameters (frequency, SF, BW, CR, sync word)
- The maximum packet size is 255 bytes, so 10KB requires ~41 packets
- Actual transmission time depends on radio conditions and distance
- The receiver may need to be started before the transmitter to avoid missing initial packets

