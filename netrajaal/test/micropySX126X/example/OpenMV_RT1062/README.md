# OpenMV RT1062 + Waveshare Core1262-868M Examples

This directory contains examples for using the micropySX126X library with OpenMV RT1062 and the Waveshare Core1262-868M LoRa module.

## Hardware Connections

Connect the OpenMV RT1062 to the Waveshare Core1262-868M module as follows:

| OpenMV RT1062 Pin | Core1262-868M Pin | Function |
|------------------|-------------------|----------|
| P0               | MOSI              | SPI Master Out Slave In |
| P1               | MISO              | SPI Master In Slave Out |
| P2               | SCLK              | SPI Clock |
| P3               | CS                | Chip Select |
| P6               | RESET             | Reset |
| P7               | BUSY              | Busy signal |
| P13              | DIO1              | Interrupt/Status |

**Additional pins available:** P8, P14 (not used in these examples)

**Note:** Ensure proper power supply (3.3V) and ground connections between the boards.

## SPI Configuration

The examples use the following SPI configuration (as specified for OpenMV RT1062):
- Bus: SPI(1)
- Baudrate: 2,000,000 Hz (2 MHz)
- Polarity: 0
- Phase: 0
- Bits: 8
- First bit: MSB

## Files

### `test_sx1262.py`
Comprehensive test suite that demonstrates:
- Module initialization
- LoRa mode configuration
- Operation mode changes (Sleep, Standby, TX, RX)
- LoRa parameter modifications (frequency, bandwidth, spreading factor, coding rate, power)
- RSSI and SNR readings
- Transmit operations (blocking mode)
- Receive operations (blocking mode)
- Blocking/non-blocking mode changes
- Frequency scanning
- Power level testing

Run this to verify all functionality:
```python
import test_sx1262
test_sx1262.run_all_tests()
```

### `tx_example.py`
Simple transmitter example that sends a counter message every 5 seconds.

### `rx_example.py`
Simple receiver example that continuously listens for messages and displays received data with RSSI/SNR.

### `rx_receive.py`
Comprehensive receiver script with detailed packet information:
- Displays received data in multiple formats (hex, ASCII, bytes)
- Shows RSSI and SNR for each packet
- Configurable timeout options
- Packet counting
- Better error handling

### `rx_simple.py`
Minimal receiver script - simplest possible code to receive and print messages.

## Usage

1. Copy the `lib` directory to your OpenMV RT1062 (if not already present).

2. Copy the example file(s) you want to use to your OpenMV RT1062.

3. Connect the hardware as specified above.

4. Run the example:
   ```python
   import tx_example  # or rx_example, test_sx1262
   ```

## LoRa Configuration

The examples use the following default LoRa parameters:
- **Frequency:** 868.0 MHz (EU ISM band)
- **Bandwidth:** 125 kHz
- **Spreading Factor:** 9
- **Coding Rate:** 7 (4/7)
- **Sync Word:** 0x12 (private)
- **TX Power:** 14 dBm
- **Preamble Length:** 8
- **CRC:** Enabled

**Important:** Adjust the frequency according to your region's regulations:
- EU: 868.0 - 868.6 MHz
- US: 902 - 928 MHz (requires SX1262 variant that supports this range)
- Asia: Check local regulations

## Troubleshooting

1. **Module not responding:**
   - Verify all connections
   - Check power supply (3.3V)
   - Ensure SPI pins are correctly connected

2. **SPI communication errors:**
   - Verify SPI configuration matches the module requirements
   - Check that pins P0-P3 are correctly connected
   - Try reducing SPI baudrate if issues persist

3. **No messages received:**
   - Ensure both TX and RX are on the same frequency
   - Check that spreading factor, bandwidth, and coding rate match
   - Verify sync word matches between TX and RX
   - Check antenna connections

4. **Timeout errors:**
   - Increase timeout values in receive functions
   - Check that DIO1 (P13) is properly connected for interrupt signaling
   - Verify BUSY pin (P7) is working correctly

## References

- [Waveshare Core1262-868M Wiki](https://www.waveshare.com/wiki/Core1262-868M)
- [OpenMV RT1062 Documentation](https://docs.openmv.io/)
- [Semtech SX1262 Datasheet](https://www.semtech.com/products/wireless-rf/lora-transceivers/sx1262)

