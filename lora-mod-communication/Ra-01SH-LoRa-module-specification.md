# Ra-01SH LoRa Module Specification and Hardware info (from datasheet)

## 1. Module Overview

**Module:** Ra-01SH  
**Manufacturer:** Ai-Thinker  
**Chipset:** Semtech SX1262  
**Interface:** SPI (4-wire)  
**Frequency Band:** 803–930 MHz  
**Modulation:** LoRa™, FSK, GFSK, MSK, GMSK, OOK  
**Max Output Power:** +22 dBm  
**Sensitivity:** Up to -148 dBm  
**Packet Size:** Up to 256 bytes  
**Voltage Supply:** 3.3 V  
**Power Consumption:**
- Receive: ~4.2 mA
- Standby: ~1.6 mA
- TX: ~140 mA max

---

## 2. Working Principle

LoRa (Long Range) is a spread-spectrum modulation technique. The SX1262 inside Ra-01SH:
- Spreads bits across a wider bandwidth
- Provides longer communication range
- Supports robust error correction

---

## 3. Hardware Interface

### Required Pins on Raspberry Pi (SPI):

| Pi GPIO | Ra-01SH Pin | Function           |
|---------|-------------|--------------------|
| 19      | MOSI        | Data to Ra-01SH    |
| 21      | MISO        | Data from Ra-01SH  |
| 23      | SCK         | SPI Clock          |
| 24      | NSS         | Chip Select        |
| Any GPIO | DIO1/2/3, RESET, TXEN, RXEN | Control lines |
| GND     | GND         | Ground             |
| 3.3V    | VCC         | Power              |

> Antenna is required for proper RF operation.

---

## 4. Data Transmission Concept

The module supports **half-duplex SPI communication** using the LoRa modem. Data is packed into **frames**.

### Frame Structure (LoRa Packet Engine):

```
+------------+------------+-----------+-------------------+-------------+
| Preamble   | Header     | Length    | Payload (Data)    | CRC (opt.)  |
+------------+------------+-----------+-------------------+-------------+
```

- **Preamble:** Sync sequence
- **Header:** Contains configuration bits (like CRC on/off, fixed/variable length)
- **Length:** Byte count of payload
- **Payload:** Actual data (1–256 bytes)
- **CRC:** 2 bytes for checking data integrity

---

## CRC Error Check

- Enabled by configuring SX1262 registers
- If CRC check fails on receiver, the packet is discarded
- No retransmission by default (handle in software)

---

## 5. Connecting to Raspberry Pi

### Requirements (lib available)

- `spidev`, `RPi.GPIO` or `gpiozero` (Python libraries)
- SX126x LoRa driver library (based on PyLoRa or C driver for SX1262)

### Sample Pseudocode (Python)

```python
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)  # bus 0, device 0
spi.max_speed_hz = 1000000

def write_register(address, value):
    spi.xfer2([address | 0x80, value])

def read_register(address):
    return spi.xfer2([address & 0x7F, 0x00])[1]
```

### Basic Setup Steps

1. Reset the device
2. Configure radio (frequency, power, packet format)
3. Send/receive data using SPI
4. Monitor BUSY pin before each access

---

## 6. Data Send and Receive Flow

### Transmit Flow

1. Write payload to FIFO  
2. Configure packet params (length, CRC)  
3. Trigger TX mode  
4. Wait for IRQ flag (TX Done)

### Receive Flow

1. Configure FIFO and DIO mapping  
2. Trigger RX mode  
3. Wait for RX Done or Timeout IRQ  
4. Read payload from FIFO  
5. Check CRC 

---

## 7. basic communication info

- Always use ESD protection when handling the module
- Add filtering capacitors on power input
- Use external antenna and avoid metallic enclosure
- Keep SPI frequency below 10 MHz

---

## 8. Feature and Details

| Feature       | Details                                  |
|---------------|-------------------------------------------|
| Data Size     | Up to 256 bytes                          |
| Frame Format  | Preamble + Header + Payload + CRC        |
| Interface     | SPI, Half-Duplex                         |
| Error Checking| CRC (hardware-supported)                 |
| Control       | DIOx lines, BUSY, NSS                    |
| Reliability   | High (LoRa spread-spectrum with FEC)     |

---

## Resources

- [Ai-Thinker Ra-01SH Product Page](https://www.ai-thinker.com)
- [Ai-Thinker Documentation](https://docs.ai-thinker.com)
- [Semtech SX1262 Datasheet](https://www.semtech.com/products/wireless-rf/lora-transceivers/sx1262)

---