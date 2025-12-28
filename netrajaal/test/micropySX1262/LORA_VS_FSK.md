# LoRa vs FSK: Understanding the Two Modulation Modes

This document explains the differences between LoRa and FSK (GFSK) modulation modes available in the SX1262 transceiver.
## Overview

The SX1262 chip supports two distinct modulation schemes:
- **LoRa (Long Range)**: Chirp Spread Spectrum modulation optimized for long-range, low-power communication
- **FSK/GFSK (Gaussian Frequency Shift Keying)**: Traditional digital modulation optimized for high-speed data transmission

## What is LoRa?

**LoRa** (Long Range) is a proprietary spread spectrum modulation technique that uses chirp spread spectrum (CSS) technology. It's designed for long-range, low-power wireless communication.

### Key Characteristics:
- **Long Range**: Can communicate over several kilometers (depending on conditions)
- **Low Power**: Optimized for battery-powered applications
- **Low Data Rate**: Typically 0.3 kbps to 50 kbps
- **High Sensitivity**: Excellent receiver sensitivity (down to -148 dBm)
- **Interference Resistance**: Good resistance to interference and multipath fading
- **SNR Measurement**: Provides Signal-to-Noise Ratio (SNR) information

### How LoRa Works:
- Uses **Spreading Factor (SF)**: 5-12, determines data rate and range
- Uses **Bandwidth (BW)**: 7.8 kHz to 500 kHz
- Uses **Coding Rate (CR)**: 4/5 to 4/8 for error correction
- Chirp signals spread data across the frequency band, making it robust to interference

## What is FSK/GFSK?

**FSK** (Frequency Shift Keying) is a digital modulation scheme where data is transmitted by shifting the carrier frequency. **GFSK** (Gaussian FSK) applies Gaussian filtering to reduce spectral bandwidth.

### Key Characteristics:
- **High Data Rate**: Can achieve up to 300 kbps
- **Short to Medium Range**: Typically hundreds of meters
- **Standard Modulation**: Widely used, compatible with many systems
- **Address Filtering**: Built-in address filtering for network support
- **No SNR**: Does not provide SNR measurement (only RSSI)
- **Lower Sensitivity**: Less sensitive than LoRa (typically -123 dBm)

### How FSK Works:
- Uses **Bit Rate (BR)**: Data rate in kbps (e.g., 48 kbps)
- Uses **Frequency Deviation**: Frequency shift for encoding (e.g., 50 kHz)
- Uses **RX Bandwidth**: Receiver bandwidth (e.g., 156.2 kHz)
- Binary data encoded as frequency shifts

## Comparison Table

| Feature | LoRa | FSK/GFSK |
|---------|------|----------|
| **Range** | Very Long (km) | Short-Medium (100s of meters) |
| **Data Rate** | Low (0.3-50 kbps) | High (up to 300 kbps) |
| **Power Consumption** | Very Low | Low-Medium |
| **Receiver Sensitivity** | Excellent (-148 dBm) | Good (-123 dBm) |
| **Interference Resistance** | Excellent | Good |
| **SNR Information** | Yes | No (RSSI only) |
| **Address Filtering** | No | Yes |
| **Network Support** | LoRaWAN compatible | Generic wireless |
| **Use Case** | IoT, sensors, long-range | High-speed data, short-range |
| **Configuration Complexity** | Medium | Medium-High |

## Technical Parameters Comparison

### LoRa Parameters

| Parameter | Range/Values | Description |
|-----------|--------------|-------------|
| **Frequency** | 150-960 MHz | Operating frequency |
| **Spreading Factor (SF)** | 5-12 | Higher = longer range, lower data rate |
| **Bandwidth (BW)** | 7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500 kHz | Channel bandwidth |
| **Coding Rate (CR)** | 5-8 (4/5 to 4/8) | Error correction overhead |
| **Sync Word** | 0x12 (private), 0x34 (public) | Network identifier |
| **Preamble Length** | 6-65535 symbols | Packet preamble |
| **Max Packet Size** | 255 bytes | Maximum payload |

### FSK Parameters

| Parameter | Range/Values | Description |
|-----------|--------------|-------------|
| **Frequency** | 150-960 MHz | Operating frequency |
| **Bit Rate (BR)** | 0.6-300 kbps | Data transmission rate |
| **Frequency Deviation** | 0.6-200 kHz | Frequency shift for encoding |
| **RX Bandwidth** | 4.8-467 kHz | Receiver bandwidth |
| **Data Shaping** | 0.3, 0.5, 0.7, 1.0 | Gaussian filter shape |
| **Sync Word** | Custom (1-8 bytes) | Packet synchronization |
| **Address Filtering** | Off, Node, Broadcast | Network addressing |
| **Preamble Length** | 0-65535 bits | Packet preamble |
| **Max Packet Size** | 255 bytes | Maximum payload |

## Code Examples

### LoRa Configuration

```python
from sx1262 import SX1262

sx = SX1262(
    spi_bus=1,
    clk='P2', mosi='P0', miso='P1', cs='P3',
    irq='P13', rst='P6', gpio='P7'
)

# Configure for LoRa mode
sx.begin(
    freq=868.0,      # 868 MHz (EU ISM band)
    bw=125.0,        # 125 kHz bandwidth
    sf=9,            # Spreading factor 9
    cr=7,            # Coding rate 4/7
    syncWord=0x12,   # Private sync word
    power=14,        # 14 dBm TX power
    blocking=True
)

# Send data
sx.send(b"Hello, LoRa!")

# Receive data
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if status == 0:
    print(f"Received: {msg}")
```

### FSK Configuration

```python
from sx1262 import SX1262

sx = SX1262(
    spi_bus=1,
    clk='P2', mosi='P0', miso='P1', cs='P3',
    irq='P13', rst='P6', gpio='P7'
)

# Configure for FSK mode
sx.beginFSK(
    freq=868.0,              # 868 MHz
    br=48.0,                  # 48 kbps bit rate
    freqDev=50.0,             # 50 kHz frequency deviation
    rxBw=156.2,               # 156.2 kHz RX bandwidth
    power=14,                 # 14 dBm TX power
    preambleLength=16,        # 16-bit preamble
    dataShaping=0.5,          # Gaussian filter 0.5
    syncWord=[0x2D, 0x01],    # Sync word
    syncBitsLength=16,        # 16-bit sync word
    addrFilter=0,             # No address filtering
    blocking=True
)

# Send data
sx.send(b"Hello, FSK!")

# Receive data
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if status == 0:
    print(f"Received: {msg}")
```

## Data Rate Comparison

### LoRa Data Rates (SF=9, BW=125 kHz, CR=7)

| Spreading Factor | Data Rate | Range | Air Time (100 bytes) |
|------------------|-----------|-------|---------------------|
| SF5 | ~38 kbps | Short | ~26 ms |
| SF7 | ~22 kbps | Medium | ~45 ms |
| SF9 | ~5.5 kbps | Long | ~180 ms |
| SF12 | ~0.25 kbps | Longest | ~3.6 s |

### FSK Data Rates (Typical Configurations)

| Bit Rate | Frequency Dev | Range | Air Time (100 bytes) |
|----------|---------------|-------|---------------------|
| 48 kbps | 50 kHz | Medium | ~17 ms |
| 100 kbps | 100 kHz | Short | ~8 ms |
| 200 kbps | 200 kHz | Short | ~4 ms |

## Power Consumption

### LoRa Power Consumption
- **TX (14 dBm)**: ~45 mA
- **RX Continuous**: ~4.6 mA
- **Standby**: ~720 nA
- **Sleep**: ~0.85 µA (retain config), ~0.4 µA (cold)

### FSK Power Consumption
- **TX (14 dBm)**: ~45 mA
- **RX Continuous**: ~4.6 mA
- **Standby**: ~720 nA
- **Sleep**: ~0.85 µA (retain config), ~0.4 µA (cold)

*Note: Power consumption is similar for both modes; the difference is in transmission time (air time).*

## Range Estimation

### LoRa Range (Typical, Line of Sight)
- **SF5, BW=500 kHz**: ~2-5 km
- **SF7, BW=125 kHz**: ~5-10 km
- **SF9, BW=125 kHz**: ~10-15 km
- **SF12, BW=125 kHz**: ~15-20+ km

*Range varies significantly with:*
- *Antenna height and gain*
- *Obstacles and terrain*
- *Interference levels*
- *Weather conditions*

### FSK Range (Typical, Line of Sight)
- **48 kbps**: ~500 m - 1 km
- **100 kbps**: ~300-500 m
- **200+ kbps**: ~100-300 m

*Range decreases with higher data rates.*

## Choosing the Right Mode: Decision Guide


## Switching Between Modes

You can switch between LoRa and FSK modes by calling the appropriate `begin()` or `beginFSK()` method:

```python
# Start with LoRa
sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14)

# ... use LoRa ...

# Switch to FSK
sx.beginFSK(freq=868.0, br=48.0, freqDev=50.0, rxBw=156.2, power=14)

# ... use FSK ...

# Switch back to LoRa
sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14)
```

**Important**: Both TX and RX must use the same mode and compatible parameters for successful communication.

## Summary

- **LoRa**: Best for long-range, low-power, low-data-rate applications (IoT, sensors, monitoring)
- **FSK**: Best for high-speed, short-range, high-data-rate applications (file transfer, images, local networks)

Both modes are supported by the SX1262 and can be used in the same application by switching modes as needed. Choose based on your specific requirements for range, data rate, and power consumption.

