# SX1262 Implementation Notes

## Files Created

1. **sx1262.py** - Main driver implementation
   - Complete SX1262 command set
   - BUSY pin handling
   - SPI communication
   - High-level TX/RX API
   - Low-level register/command access

2. **example_tx.py** - TX example
   - Sends "HELLO_OPENMV" repeatedly
   - Shows basic TX usage

3. **example_rx.py** - RX example
   - Receives packets continuously
   - Displays RSSI and SNR

4. **SX1262_README.md** - Complete documentation
   - Hardware setup
   - API reference
   - Troubleshooting guide

## Key Implementation Details

### SPI Communication

- Uses `write_readinto()` for full-duplex SPI transfers
- All read operations write command + dummy bytes, then read response
- BUSY pin is checked before every SPI transaction

### Reset Sequence

1. Pull RESET low for 10ms
2. Release RESET (high)
3. Wait 10ms for stabilization
4. Wait for BUSY to go low

### Command Flow

**Write Command:**
1. Wait for BUSY low
2. CS low
3. Write command + data bytes
4. CS high
5. Wait for BUSY low (except SET_SLEEP)

**Read Command:**
1. Wait for BUSY low
2. CS low
3. Write command + dummy bytes
4. Read response bytes (via write_readinto)
5. CS high
6. Wait for BUSY low

### TX Sequence

1. Set to Standby
2. Clear IRQ flags
3. Write data to FIFO buffer
4. Set payload length register
5. Start TX
6. Poll IRQ status for TX_DONE
7. Return to Standby

### RX Sequence

1. Set to Standby
2. Clear IRQ flags
3. Start RX (continuous or timeout)
4. Poll IRQ status for RX_DONE
5. Read buffer status (payload length, offset)
6. Read payload from FIFO
7. Get packet status (RSSI, SNR)
8. Return to Standby

## Testing Checklist

- [ ] SPI communication works (get_status returns valid value)
- [ ] Reset sequence completes successfully
- [ ] TX sends packets (check with spectrum analyzer or second device)
- [ ] RX receives packets (from TX device)
- [ ] RSSI/SNR values are reasonable
- [ ] No BUSY timeouts
- [ ] IRQ flags work correctly

## Known Limitations

1. **Polling-based IRQ**: Currently uses polling instead of interrupts
   - DIO1 pin is configured but not used for interrupts
   - Can be enhanced for interrupt-driven operation

2. **Timeout handling**: RX timeout uses continuous mode
   - Symbol-based timeout calculation could be improved
   - Currently relies on software timeout

3. **Error recovery**: Limited error recovery
   - BUSY timeout raises exception
   - No automatic retry on failed TX/RX

## Future Enhancements

1. Interrupt-driven operation using DIO1
2. Better timeout handling (symbol-based calculations)
3. Automatic retry on TX failure
4. CAD (Channel Activity Detection) support
5. Frequency hopping support
6. Multiple packet buffer management

## Porting to Other Platforms

The driver is designed to be portable:

1. **SPI**: Uses standard MicroPython SPI interface
2. **GPIO**: Uses standard MicroPython Pin interface
3. **Time**: Uses standard `time` module

To port to ESP32 or other platforms:
- Adjust pin definitions
- Verify SPI configuration matches platform
- Test BUSY pin behavior (may need different timing)

## Debugging Tips

1. **Check BUSY pin**: Use oscilloscope/logic analyzer
   - Should go low after each command
   - If stuck high, chip may be in error state

2. **Check SPI signals**: Verify MOSI/MISO/SCK/CS
   - CS should pulse low for each transaction
   - MOSI should show command bytes
   - MISO should show response bytes

3. **Check IRQ flags**: Use `get_irq_status()` to debug
   - TX_DONE = 0x01
   - RX_DONE = 0x02
   - RX_TX_TIMEOUT = 0x80
   - CRC_ERROR = 0x40

4. **Verify parameters**: TX and RX must match exactly
   - Frequency
   - Spreading Factor
   - Bandwidth
   - Coding Rate
   - Preamble length

## References

- SX1262 Datasheet: Semtech SX1261/2 Datasheet
- LoRa Modulation: LoRa Modulation Basics
- OpenMV SPI: OpenMV SPI Documentation

