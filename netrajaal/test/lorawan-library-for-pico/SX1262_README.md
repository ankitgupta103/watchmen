# SX1262 MicroPython Driver for OpenMV RT1062

Point-to-Point (P2P) LoRa Communication Driver for Waveshare Core1262-868M (SX1262) module on OpenMV Cam RT1062.

## Features

- ✅ Pure MicroPython implementation
- ✅ Point-to-point LoRa communication (no LoRaWAN)
- ✅ Simple TX/RX API
- ✅ BUSY pin handling
- ✅ IRQ support (polling-based)
- ✅ RSSI and SNR reporting
- ✅ Clean, minimal, and well-documented code

## Hardware Configuration

### Pin Mapping

| OpenMV RT1062 | Waveshare Core1262-868M | Description |
|---------------|-------------------------|-------------|
| P0            | MOSI                    | SPI MOSI    |
| P1            | MISO                    | SPI MISO    |
| P2            | SCK                     | SPI Clock   |
| P3            | NSS / CS                | SPI Chip Select |
| P7            | BUSY                    | BUSY signal |
| P13           | RESET                   | Reset pin   |
| P6            | DIO1                    | IRQ pin (optional) |
| GND           | GND                     | Ground      |
| 3.3V          | VCC                     | Power (3.3V) |

### SPI Configuration

- **Baudrate**: 2 MHz (safe for SX1262)
- **Mode**: SPI Mode 0 (CPOL=0, CPHA=0)
- **Bit Order**: MSB first

## Quick Start

### 1. Copy Files to OpenMV

Copy the following files to your OpenMV device:
- `sx1262.py` - Main driver
- `example_tx.py` - TX example
- `example_rx.py` - RX example

### 2. Run TX Example

```python
# On first OpenMV device
import example_tx
# Sends "HELLO_OPENMV" every 2 seconds
```

### 3. Run RX Example

```python
# On second OpenMV device
import example_rx
# Receives and prints packets with RSSI/SNR
```

## API Reference

### Initialization

```python
from machine import SPI, Pin
from sx1262 import SX1262

# Configure SPI
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)

# Configure pins
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)  # Optional

# Initialize radio
radio = SX1262(spi, cs, busy, reset, dio1, freq=868000000)
```

### Configuration

```python
from sx1262 import SF_7, BW_125, CR_4_5

radio.configure(
    frequency=868000000,  # 868 MHz
    sf=SF_7,             # Spreading Factor 7
    bw=BW_125,           # Bandwidth 125 kHz
    cr=CR_4_5,           # Coding Rate 4/5
    tx_power=14,         # TX Power in dBm
    preamble_length=12,  # Preamble length
    payload_length=0     # 0 = variable length
)
```

### Send Data

```python
# Send string
success = radio.send("HELLO_OPENMV", timeout_ms=5000)

# Send bytes
success = radio.send(b"\x01\x02\x03", timeout_ms=5000)
```

### Receive Data

```python
# Receive with timeout
data, rssi, snr = radio.receive(timeout_ms=5000)

# Receive continuously (wait forever)
data, rssi, snr = radio.receive(timeout_ms=0)

if data:
    print(f"Received: {data.decode()}")
    print(f"RSSI: {rssi:.1f} dBm")
    print(f"SNR: {snr:.1f} dB")
```

## LoRa Parameters

### Spreading Factors (SF)

- `SF_5` to `SF_12` (SF_7 recommended for most applications)
- Higher SF = longer range, slower data rate

### Bandwidth (BW)

- `BW_7_8` = 7.8 kHz
- `BW_10_4` = 10.4 kHz
- `BW_15_6` = 15.6 kHz
- `BW_20_8` = 20.8 kHz
- `BW_31_25` = 31.25 kHz
- `BW_41_7` = 41.7 kHz
- `BW_62_5` = 62.5 kHz
- `BW_125` = 125 kHz (recommended)
- `BW_250` = 250 kHz
- `BW_500` = 500 kHz

### Coding Rate (CR)

- `CR_4_5` = 4/5 (fastest, least error correction)
- `CR_4_6` = 4/6
- `CR_4_7` = 4/7
- `CR_4_8` = 4/8 (slowest, most error correction)

### Important Notes

1. **TX and RX must use identical parameters** (SF, BW, CR, frequency)
2. **Frequency must match** between TX and RX devices
3. **Preamble length must match** (typically 12)
4. **Variable length packets** (`payload_length=0`) are more flexible

## Troubleshooting

### No Communication

- Check SPI connections (MOSI, MISO, SCK, CS)
- Verify BUSY pin is connected and working
- Check RESET pin sequence
- Verify 3.3V power supply

### TX Success but RX Timeout

- Verify TX and RX use **identical** LoRa parameters
- Check frequency matches (868 MHz)
- Increase timeout value
- Check antenna connections

### CRC Errors

- Verify parameters match between TX and RX
- Check signal strength (RSSI)
- Reduce distance or increase TX power
- Check for interference

### BUSY Timeout

- Chip may be stuck - power cycle the module
- Check RESET pin connection
- Verify SPI communication is working

## Low-Level API

For advanced usage, you can access low-level methods:

```python
# Set to standby
radio.set_standby()

# Set RF frequency
radio.set_rf_frequency(868000000)

# Set modulation parameters
radio.set_modulation_params(SF_7, BW_125, CR_4_5, ldro=0)

# Set packet parameters
radio.set_packet_params(12, 0, 0, 1, 0)

# Write to FIFO
radio.write_buffer(0, b"Hello")

# Start TX
radio.set_tx(0)

# Check IRQ status
irq = radio.get_irq_status()
if irq & IRQ_TX_DONE:
    print("TX complete")
```

## Example: Custom TX/RX

```python
from machine import SPI, Pin
from sx1262 import SX1262, SF_7, BW_125, CR_4_5
import time

# Initialize
spi = SPI(1, baudrate=2000000, polarity=0, phase=0)
radio = SX1262(spi, Pin("P3"), Pin("P7"), Pin("P13"), Pin("P6"), 868000000)

# Configure
radio.configure(frequency=868000000, sf=SF_7, bw=BW_125, cr=CR_4_5, 
                tx_power=14, preamble_length=12, payload_length=0)

# TX Loop
while True:
    message = f"Packet at {time.ticks_ms()}"
    if radio.send(message):
        print(f"Sent: {message}")
    time.sleep_ms(1000)
```

## Technical Details

### Reset Sequence

1. Pull RESET low for >100us
2. Release RESET (high)
3. Wait for chip stabilization
4. Wait for BUSY to go low

### BUSY Pin Handling

- SX1262 sets BUSY high during command processing
- Driver waits for BUSY to go low before each SPI transaction
- Prevents command conflicts and ensures chip is ready

### IRQ Handling

- Currently uses polling (checking IRQ status periodically)
- DIO1 pin can be used for interrupt-driven operation (future enhancement)
- IRQ flags: TX_DONE, RX_DONE, RX_TX_TIMEOUT, CRC_ERROR

### FIFO Buffer

- TX: Write data to FIFO, then start TX
- RX: Wait for RX_DONE, then read from FIFO
- Buffer offset typically starts at 0

## License

This driver is provided as-is for educational and development purposes.

## References

- [SX1262 Datasheet](https://www.semtech.com/products/wireless-rf/lora-cores/sx1262)
- [Waveshare Core1262-868M Wiki](https://www.waveshare.com/wiki/Core1262-868M)
- [OpenMV Documentation](https://docs.openmv.io/)

