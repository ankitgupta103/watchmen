# micropySX126X - SX126X LoRa Driver for OpenMV RT1062

A MicroPython driver for Semtech SX126X LoRa transceivers SX1262 specifically designed for OpenMV RT1062. This library provides a complete API for LoRa and FSK communication modes via SPI interface with the Waveshare Core1262-868M module.

## Overview

The micropySX126X library provides a high-level interface for controlling Semtech SX126X LoRa transceivers on OpenMV RT1062. It supports:

- **LoRa Modulation**: Long-range, low-power communication
- **FSK Modulation**: High-speed data transmission
- **Blocking and Non-blocking Modes**: Flexible operation modes
- **OpenMV RT1062 Optimized**: Specifically designed for OpenMV RT1062 SPI interface

## Installation

1. Copy the library files to your device:
   - `_sx126x.py`
   - `sx126x.py`
   - `sx1262.py`

2. Place files in the root directory or ensure they're accessible via import path.

## Examples

### API Test Examples

Comprehensive test examples for all API methods are located in `example/api_tests/`:

- **01_initialization.py** - Tests constructor and `begin()` method with various configurations
- **02_transmission.py** - Tests `send()` method with different data types and sizes
- **03_reception.py** - Tests `recv()` method with blocking, timeout, and error handling
- **04_configuration.py** - Tests all configuration methods (`setFrequency()`, `setOutputPower()`, etc.)
- **05_status_info.py** - Tests status methods (`getRSSI()`, `getSNR()`, `getTimeOnAir()`)
- **06_power_management.py** - Tests power management (`sleep()`, `standby()`)
- **07_blocking_modes.py** - Tests blocking and non-blocking modes with callbacks

**Usage**: Run any test file to understand specific API functionality:
```python
import example.api_tests.01_initialization
```

See `example/api_tests/README.md` for detailed documentation on each test.

## API Reference

### Constructor

```python
SX1262(spi_bus, clk, mosi, miso, cs, irq, rst, gpio, 
       spi_baudrate=2000000, spi_polarity=0, spi_phase=0)
```

**Test Example**: `example/api_tests/01_initialization.py`

**Parameters**:
- `spi_bus` (int): SPI bus ID
- `clk` (str/int): Clock pin (e.g., 'P2')
- `mosi` (str/int): MOSI pin (e.g., 'P0')
- `miso` (str/int): MISO pin (e.g., 'P1')
- `cs` (str/int): Chip Select pin (e.g., 'P3')
- `irq` (str/int): DIO1/IRQ pin (e.g., 'P13')
- `rst` (str/int): Reset pin (e.g., 'P6')
- `gpio` (str/int): BUSY pin (e.g., 'P7')
- `spi_baudrate` (int): SPI baudrate in Hz (default: 2000000)
- `spi_polarity` (int): SPI polarity (default: 0)
- `spi_phase` (int): SPI phase (default: 0)

### LoRa Configuration

#### `begin(freq, bw, sf, cr, syncWord, power, currentLimit=60.0, preambleLength=8, implicit=False, implicitLen=0xFF, crcOn=True, txIq=False, rxIq=False, tcxoVoltage=1.6, useRegulatorLDO=False, blocking=True)`

Configure the module for LoRa operation.

**Test Example**: `example/api_tests/01_initialization.py`

**Parameters**:
- `freq` (float): Frequency in MHz. **Range**: 150.0 - 960.0
- `bw` (float): Bandwidth in kHz. **Valid values**: 7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125.0, 250.0, 500.0
- `sf` (int): Spreading Factor. **Range**: 5 - 12
- `cr` (int): Coding Rate. **Range**: 5 - 8 (represents 4/5 to 4/8)
- `syncWord` (int): Sync word. **Values**: 0x12 (private), 0x34 (public)
- `power` (int): TX power in dBm. **Range**: -9 to 22
- `currentLimit` (float): Current limit in mA. **Range**: 0.0 - 140.0 (default: 60.0)
- `preambleLength` (int): Preamble length in symbols (default: 8)
- `implicit` (bool): Implicit header mode (default: False)
- `implicitLen` (int): Implicit header length (default: 0xFF)
- `crcOn` (bool): Enable CRC (default: True)
- `txIq` (bool): TX invert IQ (default: False)
- `rxIq` (bool): RX invert IQ (default: False)
- `tcxoVoltage` (float): TCXO voltage in V. **Valid values**: 0.0, 1.6, 1.7, 1.8, 2.2, 2.4, 2.7, 3.0, 3.3 (default: 1.6)
- `useRegulatorLDO` (bool): Use LDO regulator instead of DC-DC (default: False)
- `blocking` (bool): Blocking mode (default: True)

**Returns**: Status code (0 = ERR_NONE = success)

**Common Configurations**:

| Application | SF | BW (kHz) | CR | Data Rate | Range | Est. Distance |
|------------|----|---------|----|-----------|-------|--------------|
| Maximum Range | 12 | 125 | 8 | ~250 bps | Longest | 15-20 km (rural), 5-8 km (urban) need be tested |
| Long Range | 9 | 125 | 7 | ~5.5 kbps | Long | 10-15 km (rural), 3-5 km (urban) need be tested |
| Medium Range | 7 | 125 | 7 | ~22 kbps | Medium | 5-10 km (rural), 2-4 km (urban) need be tested |
| High Speed | 5 | 500 | 5 | ~38 kbps | Short | 2-5 km (rural), 1-2 km (urban) need be tested |

*Note: Distance estimates based on real-world tests:*
- *Rural/open field: Line-of-sight conditions, minimal obstacles*
- *Urban: Dense areas with buildings and interference*
- *Actual range varies significantly with terrain, antenna height (gateway 20-30m typical), obstacles, interference, and weather conditions*
- *Exceptional cases: Up to 100+ km in mountainous terrain with elevated positions*

### Transmission

#### `send(data)`

Send data over LoRa.

**Test Example**: `example/api_tests/02_transmission.py`

**Parameters**:
- `data` (bytes/bytearray): Data to send. **Max length**: 255 bytes

**Returns**: Tuple `(payload_length, status)`
- `payload_length` (int): Number of bytes sent
- `status` (int): Status code (0 = success)

**Example**:
```python
payload_len, status = sx.send(b"Hello, World!")
if status == 0:
    print(f"Sent {payload_len} bytes successfully")
```

### Reception

#### `recv(len=0, timeout_en=False, timeout_ms=0)`

Receive data over LoRa.

**Test Example**: `example/api_tests/03_reception.py`

**Parameters**:
- `len` (int): Expected message length. **0** = auto-detect, **max**: 255
- `timeout_en` (bool): Enable timeout (default: False)
- `timeout_ms` (int): Timeout in milliseconds. **0** = default timeout

**Returns**: Tuple `(message, status)`
- `message` (bytes): Received data
- `status` (int): Status code. **0** = success, **-6** = timeout, **-7** = CRC error

**Example**:
```python
# Blocking receive (no timeout)
msg, status = sx.recv()

# Receive with timeout
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if status == 0:
    print(f"Received: {msg}")
```

### Configuration Methods

#### `setFrequency(freq, calibrate=True)`

Set operating frequency.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `freq` (float): Frequency in MHz. **Range**: 150.0 - 960.0
- `calibrate` (bool): Auto-calibrate image (default: True)

**Returns**: Status code (0 = success)

#### `setOutputPower(power)`

Set TX output power.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `power` (int): Output power in dBm. **Range**: -9 to 22

**Returns**: Status code (0 = success)

#### `setSpreadingFactor(sf)`

Set LoRa spreading factor.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `sf` (int): Spreading factor. **Range**: 5 - 12

**Returns**: Status code (0 = success)

#### `setBandwidth(bw)`

Set LoRa bandwidth.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `bw` (float): Bandwidth in kHz. **Valid values**: 7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125.0, 250.0, 500.0

**Returns**: Status code (0 = success)

#### `setCodingRate(cr)`

Set LoRa coding rate.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `cr` (int): Coding rate. **Range**: 5 - 8 (represents 4/5 to 4/8)

**Returns**: Status code (0 = success)

#### `setPreambleLength(preambleLength)`

Set preamble length.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `preambleLength` (int): Preamble length in symbols

**Returns**: Status code (0 = success)

#### `setSyncWord(syncWord, controlBits=0x44)`

Set sync word.

**Test Example**: `example/api_tests/04_configuration.py`

**Parameters**:
- `syncWord` (int): Sync word. **Values**: 0x12 (private), 0x34 (public)
- `controlBits` (int): Control bits (default: 0x44)

**Returns**: Status code (0 = success)

### Status and Information Methods

#### `getRSSI()`

Get received signal strength indicator.

**Test Example**: `example/api_tests/05_status_info.py`

**Returns**: RSSI in dBm (float)

**What is RSSI?** RSSI (Received Signal Strength Indicator) tells you how strong the radio signal is at the receiver. Think of it like the volume of a radio station - higher values (closer to 0) mean a stronger signal, while lower values (like -120 dBm) mean a weaker signal. A typical good signal is above -100 dBm, while signals below -120 dBm are very weak and may have trouble getting through. RSSI helps you understand if your devices are close enough to communicate reliably, and can be used to estimate distance or find the best location for your antenna.

**Application Uses**: Use RSSI to monitor link quality, detect when devices move too far apart, optimize antenna placement, create signal strength maps, and trigger alerts when signal becomes too weak. For example, you might send a warning when RSSI drops below -110 dBm, indicating the connection might be lost soon.

**Example**:
```python
rssi = sx.getRSSI()
print(f"RSSI: {rssi:.2f} dBm")
if rssi < -110:
    print("Warning: Weak signal!")
```

#### `getSNR()`

Get signal-to-noise ratio (LoRa only).

**Test Example**: `example/api_tests/05_status_info.py`

**Returns**: SNR in dB (float)

**What is SNR?** SNR (Signal-to-Noise Ratio) compares how strong your signal is compared to background noise and interference. Imagine trying to hear someone talk in a quiet room (high SNR) versus a noisy factory (low SNR). Higher SNR values (like +10 dB) mean a clean, clear signal, while negative SNR values mean the noise is stronger than your signal. SNR is especially useful in LoRa because it helps you understand signal quality beyond just strength - you can have a strong signal (good RSSI) but still have problems if there's too much interference (poor SNR).

**Application Uses**: Use SNR to assess communication quality, detect interference problems, optimize network performance, and make decisions about retransmission. For example, if SNR is below 0 dB, you might want to increase transmission power or change frequency. High SNR (above +5 dB) indicates excellent conditions, while negative SNR suggests you may need to adjust your configuration or location.

**Example**:
```python
snr = sx.getSNR()
print(f"SNR: {snr:.2f} dB")
if snr < 0:
    print("Poor signal quality - high interference")
```

#### `getTimeOnAir(len)`

Calculate time on air for a packet.

**Test Example**: `example/api_tests/05_status_info.py`

**Parameters**:
- `len` (int): Packet length in bytes

**Returns**: Time in microseconds (int)

**What is Time on Air?** Time on Air is how long your radio transmission actually takes to send a packet over the air. It's like measuring how long it takes to say a sentence - longer messages take more time. This time depends on your packet size, spreading factor, bandwidth, and coding rate. For example, a small 10-byte message with SF7 might take 50 milliseconds, while a 255-byte message with SF12 could take several seconds. Knowing the time on air helps you plan your communication schedule, calculate battery life, and ensure you don't exceed duty cycle limits in regulated frequency bands.

**Application Uses**: Use Time on Air to calculate battery consumption (longer air time = more power used), plan transmission schedules, ensure compliance with duty cycle regulations (especially in EU 868 MHz band), estimate network capacity, and optimize packet sizes. For example, if you're limited to 1% duty cycle (36 seconds per hour), you can calculate how many packets you can send per hour based on their time on air.

**Example**:
```python
time_us = sx.getTimeOnAir(100)
time_ms = time_us / 1000.0
print(f"Time on air: {time_ms:.2f} ms")
# Calculate packets per hour with 1% duty cycle
packets_per_hour = (3600 * 0.01) / (time_ms / 1000.0)
print(f"Can send ~{packets_per_hour:.0f} packets/hour at 1% duty cycle")
```

### Blocking/Non-blocking Mode

#### `setBlockingCallback(blocking, callback=None)`

Set blocking or non-blocking mode.

**Test Example**: `example/api_tests/07_blocking_modes.py`

**Parameters**:
- `blocking` (bool): Blocking mode (True) or non-blocking (False)
- `callback` (function): Callback function for non-blocking mode (default: None)

**Returns**: Status code (0 = success)

**Example**:
```python
# Blocking mode (default)
sx.setBlockingCallback(blocking=True)

# Non-blocking mode with callback
def my_callback(events):
    if events & SX1262.RX_DONE:
        msg, err = sx.recv()
        print(f"Received: {msg}")

sx.setBlockingCallback(blocking=False, callback=my_callback)
```

### Power Management

#### `sleep(retainConfig=True)`

Put SX1262 to sleep mode.

**Test Example**: `example/api_tests/06_power_management.py`

**Parameters**:
- `retainConfig` (bool): Retain configuration (default: True)

**Returns**: Status code (0 = success)

**Power Consumption**:
- Sleep (retain config): ~0.85 µA
- Sleep (cold): ~0.4 µA

#### `standby(mode=SX126X_STANDBY_RC)`

Put SX1262 to standby mode.

**Test Example**: `example/api_tests/06_power_management.py`

**Parameters**:
- `mode` (int): Standby mode. **Values**: SX126X_STANDBY_RC (0x00), SX126X_STANDBY_XOSC (0x01)

**Returns**: Status code (0 = success)

**Power Consumption**: ~720 nA

## Configuration

### Pin Configuration

| OpenMV RT1062 Pin | Function | Core1262-868M Pin |
|------------------|----------|-------------------|
| P0 | MOSI | MOSI |
| P1 | MISO | MISO |
| P2 | SCLK | SCLK |
| P3 | CS | Chip Select |
| P6 | RESET | Reset |
| P7 | BUSY | Busy |
| P13 | DIO1/IRQ | DIO1 |

### SPI Configuration

**Default**: 2 MHz, polarity=0, phase=0, 8 bits, MSB first

### LoRa Parameters Quick Reference

- **Spreading Factor (SF)**: 5-12 (higher = longer range, lower data rate)
- **Bandwidth (BW)**: 7.8-500 kHz (lower = longer range, lower data rate)
- **Coding Rate (CR)**: 5-8 (higher = better error correction, lower data rate)

See `begin()` method parameters for detailed values. Common configurations are shown in the API reference above.

### Regional Frequency Bands

| Region | Frequency Range | Notes |
|--------|----------------|-------|
| EU | 868.0 - 868.6 MHz | ISM band, duty cycle limits |
| US | 902 - 928 MHz | Requires SX1262 variant supporting this range |
| Asia | Varies | Check local regulations |
| Global | 433.05 - 434.79 MHz | Amateur radio band (license required) |

## Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | ERR_NONE | Success |
| -1 | ERR_UNKNOWN | Unknown error |
| -2 | ERR_CHIP_NOT_FOUND | Chip not responding |
| -4 | ERR_PACKET_TOO_LONG | Packet exceeds 255 bytes |
| -5 | ERR_TX_TIMEOUT | Transmission timeout |
| -6 | ERR_RX_TIMEOUT | Reception timeout |
| -7 | ERR_CRC_MISMATCH | CRC check failed (data still received) |
| -8 | ERR_INVALID_BANDWIDTH | Invalid bandwidth value |
| -9 | ERR_INVALID_SPREADING_FACTOR | Invalid SF (must be 5-12) |
| -10 | ERR_INVALID_CODING_RATE | Invalid CR (must be 5-8) |
| -12 | ERR_INVALID_FREQUENCY | Invalid frequency (must be 150-960 MHz) |
| -13 | ERR_INVALID_OUTPUT_POWER | Invalid power (must be -9 to 22 dBm) |

## References

- [Semtech SX1262 Datasheet](https://www.semtech.com/products/wireless-rf/lora-transceivers/sx1262)
- [Waveshare Core1262-868M Wiki](https://www.waveshare.com/wiki/Core1262-868M)
- [OpenMV RT1062 Documentation](https://docs.openmv.io/)
