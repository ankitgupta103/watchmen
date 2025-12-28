# micropySX126X - SX126X LoRa Driver for MicroPython

A comprehensive MicroPython/CircuitPython driver for Semtech SX126X LoRa transceivers (SX1261, SX1262, SX1268). This library provides a complete API for LoRa and FSK communication modes with support for various MicroPython platforms including OpenMV RT1062.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Support](#hardware-support)
3. [Library Structure](#library-structure)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Example Scripts](#example-scripts)
7. [API Reference](#api-reference)
8. [Configuration](#configuration)
9. [Applications](#applications)
10. [Troubleshooting](#troubleshooting)

## Overview

The micropySX126X library provides a high-level interface for controlling Semtech SX126X LoRa transceivers. It supports:

- **LoRa Modulation**: Long-range, low-power communication
- **FSK Modulation**: High-speed data transmission
- **Blocking and Non-blocking Modes**: Flexible operation modes
- **Multiple Platforms**: Generic MicroPython, Pycom, CircuitPython, OpenMV RT1062

## Hardware Support

### Tested Platforms

- WiPy3.0 + Semtech SX1262MB1PAS shield
- WiPy3.0 + Ebyte E22-400M22S (LoRa)
- WiPy3.0 + Ebyte E22-400M30S (LoRa with 10dB amplifier)
- LilyGO® T-Echo
- Raspberry Pi Pico + Waveshare SX126x Pico LoRa HAT
- HelTec Lora 32 v3
- **OpenMV RT1062 + Waveshare Core1262-868M** (Primary focus of this project)

## Library Structure

```
micropySX126X/
├── _sx126x.py          # Low-level constants and definitions
├── sx126x.py           # Core SX126X base class implementation
├── sx1262.py           # SX1262-specific implementation (inherits from SX126X)
└── example/
    └── OpenMV_RT1062/
        ├── simple_tx_rx/          # Basic TX/RX examples
        │   ├── tx_example.py
        │   └── rx_example.py
        └── 10kb_data_transfer/    # Reliable data transfer with ACK protocol
            ├── tx_10kb_test.py
            └── rx_10kb_test.py
```

## Installation

1. Copy the library files to your device:
   - `_sx126x.py`
   - `sx126x.py`
   - `sx1262.py`

2. For OpenMV RT1062, place files in the root directory or ensure they're accessible via import path.

**Note**: It's recommended to compile to `.mpy` or compile into the MicroPython image to prevent memory issues.

## Quick Start

### Basic Usage

```python
from sx1262 import SX1262

# Initialize the module
sx = SX1262(
    spi_bus=1,
    clk='P2',    # SCLK
    mosi='P0',   # MOSI
    miso='P1',   # MISO
    cs='P3',     # Chip Select
    irq='P13',   # DIO1 (IRQ)
    rst='P6',    # Reset
    gpio='P7',   # Busy
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure for LoRa mode
sx.begin(
    freq=868.0,      # Frequency in MHz
    bw=125.0,        # Bandwidth in kHz
    sf=9,            # Spreading Factor (5-12)
    cr=7,            # Coding Rate (5-8)
    syncWord=0x12,   # Sync word
    power=14,        # TX power in dBm
    blocking=True    # Blocking mode
)

# Send data
sx.send(b"Hello, LoRa!")

# Receive data
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if status == 0:
    print(f"Received: {msg}")
```

## Example Scripts

### 1. Simple TX/RX Examples

**Location**: `example/OpenMV_RT1062/simple_tx_rx/`

#### `tx_example.py` - Simple Transmitter

**Application**: Basic one-way data transmission demonstration

**Features**:
- Continuous transmission of counter messages
- Simple blocking mode operation
- Standard LoRa configuration (SF9, BW125kHz, CR7)

**Usage**:
```python
import tx_example
```

**Configuration**:
- Frequency: 868.0 MHz
- Spreading Factor: 9
- Bandwidth: 125 kHz
- Coding Rate: 7 (4/7)
- TX Power: 14 dBm
- Transmits every 5 seconds

**Use Cases**:
- Learning LoRa basics
- Simple telemetry transmission
- Beacon/node identification
- Testing radio connectivity

#### `rx_example.py` - Simple Receiver

**Application**: Basic one-way data reception demonstration

**Features**:
- Continuous reception loop
- RSSI and SNR reporting
- Error handling for timeouts
- Displays received data in ASCII or raw format

**Usage**:
```python
import rx_example
```

**Configuration**: Same as TX example (must match for communication)

**Use Cases**:
- Learning LoRa basics
- Simple data logging
- Monitoring radio transmissions
- Testing radio connectivity

### 2. Reliable 10KB Data Transfer with ACK Protocol

**Location**: `example/OpenMV_RT1062/10kb_data_transfer/`

#### `tx_10kb_test.py` - High-Speed Reliable Transmitter

**Application**: Reliable large data transfer with acknowledgment protocol

**Features**:
- Transmits 10KB (10,240 bytes) of data
- Highest data rate configuration (SF5, BW500kHz, CR5)
- ACK-based retransmission protocol
- Packet sequence numbering
- Automatic retry mechanism (up to 5 retries per packet)
- Comprehensive transmission statistics

**Usage**:
```python
import tx_10kb_test
```

**Configuration**:
- Frequency: 868.0 MHz
- Spreading Factor: 5 (highest data rate)
- Bandwidth: 500 kHz (maximum)
- Coding Rate: 5 (4/5, highest data rate)
- Preamble Length: 8 (minimum)
- Max packet size: 254 bytes payload (255 bytes total with seq num)
- ACK timeout: 5 seconds
- Max retries: 5 per packet

**Protocol**:
1. Sends packet with sequence number: `[seq_num, data...]`
2. Waits for ACK from receiver
3. If ACK received with matching sequence number, continues to next packet
4. If timeout or wrong ACK, retries (up to 5 times)

**Use Cases**:
- High-speed data transfer
- Firmware updates over LoRa
- Large sensor data uploads
- Image/file transfer
- Performance testing and benchmarking

#### `rx_10kb_test.py` - High-Speed Reliable Receiver

**Application**: Reliable large data reception with acknowledgment protocol

**Features**:
- Receives 10KB of data reliably
- Sends ACK after each packet
- Handles duplicate and out-of-order packets
- CRC error tracking
- Data integrity verification
- Comprehensive reception statistics

**Usage**:
```python
import rx_10kb_test
```

**Configuration**: Must match TX script exactly

**Protocol**:
1. Receives packet with sequence number
2. Extracts sequence number and data payload
3. If sequence matches expected, stores data and sends ACK
4. Handles duplicates and out-of-order packets gracefully

**Statistics Provided**:
- Total data received
- Number of packets
- ACKs sent
- CRC error count and rate
- Reception duration
- Effective data rate
- Data completeness percentage

**Use Cases**:
- High-speed data reception
- Reliable firmware download
- Large sensor data collection
- Image/file reception
- Performance testing and benchmarking

## API Reference

### Constructor

```python
SX1262(spi_bus, clk, mosi, miso, cs, irq, rst, gpio, 
       spi_baudrate=2000000, spi_polarity=0, spi_phase=0)
```

**Parameters**:
- `spi_bus`: SPI bus ID (integer)
- `clk`: Clock pin (pin number or string like 'P2')
- `mosi`: MOSI pin
- `miso`: MISO pin
- `cs`: Chip Select pin
- `irq`: DIO1/IRQ pin
- `rst`: Reset pin
- `gpio`: BUSY pin
- `spi_baudrate`: SPI baudrate (default: 2000000 Hz)
- `spi_polarity`: SPI polarity (default: 0)
- `spi_phase`: SPI phase (default: 0)

### LoRa Configuration

#### `begin()`

Configure the module for LoRa operation.

```python
status = sx.begin(
    freq=434.0,              # Frequency in MHz (150-960)
    bw=125.0,                # Bandwidth in kHz (7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500)
    sf=9,                    # Spreading Factor (5-12)
    cr=7,                    # Coding Rate (5-8, represents 4/5 to 4/8)
    syncWord=0x12,           # Sync word (0x12 private, 0x34 public)
    power=14,                # TX power in dBm (-9 to 22)
    currentLimit=60.0,       # Current limit in mA
    preambleLength=8,        # Preamble length
    implicit=False,          # Implicit header mode
    implicitLen=0xFF,        # Implicit header length
    crcOn=True,              # Enable CRC
    txIq=False,              # TX invert IQ
    rxIq=False,              # RX invert IQ
    tcxoVoltage=1.6,         # TCXO voltage in V
    useRegulatorLDO=False,   # Use LDO (True) or DC-DC (False) regulator
    blocking=True            # Blocking mode (True) or non-blocking (False)
)
```

**Returns**: Status code (0 = success)

**Common Configurations**:

| Application | SF | BW (kHz) | CR | Data Rate | Range | Notes |
|------------|----|---------|----|-----------|-------|-------|
| Maximum Range | 12 | 125 | 8 | ~250 bps | Longest | Lowest data rate |
| Long Range | 9 | 125 | 7 | ~5.5 kbps | Long | Balanced |
| Medium Range | 7 | 125 | 7 | ~22 kbps | Medium | Good balance |
| **High Speed** | **5** | **500** | **5** | **~38 kbps** | **Short** | **Maximum data rate** |

### Transmission

#### `send(data)`

Send data over LoRa.

```python
payload_len, status = sx.send(data)
```

**Parameters**:
- `data`: Bytes or bytearray to send (max 255 bytes)

**Returns**: Tuple of (payload_length, status)
- `payload_length`: Number of bytes sent
- `status`: Status code (0 = success)

**Example**:
```python
payload_len, status = sx.send(b"Hello, World!")
if status == 0:
    print(f"Sent {payload_len} bytes successfully")
```

### Reception

#### `recv(len=0, timeout_en=False, timeout_ms=0)`

Receive data over LoRa.

```python
msg, status = sx.recv(len=0, timeout_en=False, timeout_ms=0)
```

**Parameters**:
- `len`: Expected message length (0 = auto-detect, max 255)
- `timeout_en`: Enable timeout (True/False)
- `timeout_ms`: Timeout in milliseconds (0 = default timeout)

**Returns**: Tuple of (message, status)
- `message`: Received data as bytes
- `status`: Status code (0 = success, -6 = timeout, -7 = CRC error)

**Example**:
```python
# Blocking receive (no timeout)
msg, status = sx.recv()

# Receive with timeout
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if status == 0:
    print(f"Received: {msg}")
elif status == -6:
    print("Receive timeout")
```

### Configuration Methods

#### `setFrequency(freq, calibrate=True)`

Set operating frequency.

```python
status = sx.setFrequency(868.0)  # 868.0 MHz
```

**Parameters**:
- `freq`: Frequency in MHz (150-960)
- `calibrate`: Auto-calibrate image (default: True)

#### `setOutputPower(power)`

Set TX output power.

```python
status = sx.setOutputPower(14)  # 14 dBm
```

**Parameters**:
- `power`: Output power in dBm (-9 to 22)

#### `setSpreadingFactor(sf)`

Set LoRa spreading factor.

```python
status = sx.setSpreadingFactor(9)  # SF9
```

**Parameters**:
- `sf`: Spreading factor (5-12)

#### `setBandwidth(bw)`

Set LoRa bandwidth.

```python
status = sx.setBandwidth(125.0)  # 125 kHz
```

**Parameters**:
- `bw`: Bandwidth in kHz (7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500)

#### `setCodingRate(cr)`

Set LoRa coding rate.

```python
status = sx.setCodingRate(7)  # CR 4/7
```

**Parameters**:
- `cr`: Coding rate (5-8, represents 4/5 to 4/8)

#### `setPreambleLength(preambleLength)`

Set preamble length.

```python
status = sx.setPreambleLength(8)
```

#### `setSyncWord(syncWord, controlBits=0x44)`

Set sync word.

```python
status = sx.setSyncWord(0x12)  # Private network
# or
status = sx.setSyncWord(0x34)  # Public network
```

### Status and Information Methods

#### `getRSSI()`

Get received signal strength indicator.

```python
rssi = sx.getRSSI()  # Returns RSSI in dBm
print(f"RSSI: {rssi:.2f} dBm")
```

#### `getSNR()`

Get signal-to-noise ratio (LoRa only).

```python
snr = sx.getSNR()  # Returns SNR in dB
print(f"SNR: {snr:.2f} dB")
```

#### `getTimeOnAir(len)`

Calculate time on air for a packet.

```python
time_us = sx.getTimeOnAir(100)  # Time for 100 bytes in microseconds
time_ms = time_us / 1000.0
print(f"Time on air: {time_ms:.2f} ms")
```

### Blocking/Non-blocking Mode

#### `setBlockingCallback(blocking, callback=None)`

Set blocking or non-blocking mode.

```python
# Blocking mode (default)
sx.setBlockingCallback(blocking=True)

# Non-blocking mode with callback
def my_callback(events):
    if events & SX1262.RX_DONE:
        msg, err = sx.recv()
        print(f"Received: {msg}")
    elif events & SX1262.TX_DONE:
        print("Transmission complete")

sx.setBlockingCallback(blocking=False, callback=my_callback)
```

## Configuration

### OpenMV RT1062 Pin Configuration

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

Default SPI settings for OpenMV RT1062:
- **Baudrate**: 2,000,000 Hz (2 MHz)
- **Polarity**: 0
- **Phase**: 0
- **Bits**: 8
- **First bit**: MSB

### LoRa Parameter Selection Guide

#### Spreading Factor (SF)

| SF | Symbol Duration | Data Rate | Range | Sensitivity |
|----|----------------|-----------|-------|-------------|
| 5 | Shortest | Highest | Shortest | Lowest |
| 6 | Short | Very High | Short | Low |
| 7 | Medium-Short | High | Medium | Medium |
| 8 | Medium | Medium-High | Medium-Long | Good |
| 9 | Medium-Long | Medium | Long | Very Good |
| 10 | Long | Low | Very Long | Excellent |
| 11 | Very Long | Very Low | Very Long | Excellent |
| 12 | Longest | Lowest | Longest | Best |

#### Bandwidth (BW)

| BW (kHz) | Data Rate | Range | Interference Resistance |
|----------|-----------|-------|------------------------|
| 7.8 | Lowest | Longest | Best |
| 125 | Medium | Medium | Medium |
| 250 | High | Short | Medium |
| **500** | **Highest** | **Shortest** | **Lowest** |

#### Coding Rate (CR)

| CR | Overhead | Error Correction | Data Rate |
|----|----------|------------------|-----------|
| 5 (4/5) | 20% | Basic | Highest |
| 6 (4/6) | 33% | Good | High |
| 7 (4/7) | 43% | Better | Medium |
| 8 (4/8) | 50% | Best | Lowest |

### Regional Frequency Bands

| Region | Frequency Range | Notes |
|--------|----------------|-------|
| EU | 868.0 - 868.6 MHz | ISM band, duty cycle limits |
| US | 902 - 928 MHz | Requires SX1262 variant supporting this range |
| Asia | Varies | Check local regulations |
| Global | 433.05 - 434.79 MHz | Amateur radio band (license required) |

## Channels and Multi-Stream Communication

Channels in LoRa refer to different operating frequencies. By using multiple channels (frequencies), you can create parallel communication streams that reduce packet collisions, improve throughput, and minimize packet loss in dense networks.

### Understanding Channels

A **channel** is simply a specific frequency within the allowed ISM band. In the 868 MHz band (EU), you can use multiple frequencies to create separate channels:

- **Channel 1**: 868.0 MHz
- **Channel 2**: 868.1 MHz  
- **Channel 3**: 868.2 MHz
- **Channel 4**: 868.3 MHz
- etc.

**Benefits of Multi-Channel Communication**:
- **Reduced Collisions**: Different nodes can transmit on different channels simultaneously
- **Higher Throughput**: Parallel data streams increase overall network capacity
- **Lower Packet Loss**: Fewer collisions mean fewer lost packets
- **Better Network Performance**: Distributes traffic across multiple frequencies

### Channel Configuration

The SX1262 can switch frequencies dynamically using the `setFrequency()` method. You can change the operating frequency at runtime without re-initializing the entire module.

#### Defining Channels

```python
# Define multiple channels (frequencies in MHz)
CHANNELS = {
    0: 868.0,   # Channel 0
    1: 868.1,   # Channel 1
    2: 868.2,   # Channel 2
    3: 868.3,   # Channel 3
    4: 868.4,   # Channel 4
    5: 868.5,   # Channel 5
}

NUM_CHANNELS = len(CHANNELS)

def get_channel_frequency(channel):
    """Get frequency for a given channel number"""
    return CHANNELS.get(channel, 868.0)  # Default to 868.0 if invalid
```

**Important Considerations**:
- **Frequency Spacing**: Channels should be separated by at least the bandwidth used (e.g., for 125 kHz BW, use at least 125 kHz spacing)
- **Regulatory Limits**: Check local regulations for allowed frequencies and duty cycle limits
- **Bandwidth**: Ensure channels don't overlap (channel spacing >= bandwidth)
- **EU 868 MHz Band**: Typically allows 868.0-868.6 MHz (6 channels at 125 kHz spacing)

### Switching Channels

#### Basic Channel Switching

```python
from sx1262 import SX1262

# Initialize SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

# Initial configuration
sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Switch to a different channel
def switch_to_channel(channel_num):
    """Switch to a different channel (frequency)"""
    freq = get_channel_frequency(channel_num)
    status = sx.setFrequency(freq, calibrate=True)
    if status == 0:
        print(f"Switched to channel {channel_num} ({freq} MHz)")
    else:
        print(f"Failed to switch channel: {status}")
    return status == 0

# Switch to channel 2 (868.2 MHz)
switch_to_channel(2)

# Now all send/recv operations use this channel
sx.send(b"Hello on channel 2!")
```

### Multi-Stream Communication Pattern

Multi-stream communication uses multiple channels to send data in parallel, reducing packet loss and increasing throughput.

#### Round-Robin Channel Allocation

Assign channels to nodes in a round-robin fashion:

```python
# Channel allocation for multiple nodes
def get_node_channel(node_address, num_channels):
    """Assign channel based on node address (round-robin)"""
    return node_address % num_channels

# Example: Node 0x01 -> Channel 1, Node 0x02 -> Channel 2, Node 0x03 -> Channel 3, etc.
MY_NODE_ADDRESS = 0x01
my_channel = get_node_channel(MY_NODE_ADDRESS, NUM_CHANNELS)
switch_to_channel(my_channel)
print(f"Node {MY_NODE_ADDRESS:02X} assigned to channel {my_channel}")
```

#### Time-Sliced Multi-Channel Reception

A receiver can cycle through multiple channels to receive from different streams:

```python
import time
from sx1262 import SX1262

# Initialize SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Multi-channel reception
CHANNEL_DWELL_TIME_MS = 500  # Time to spend on each channel (ms)

current_channel = 0
last_channel_switch = time.ticks_ms()

print("Starting multi-channel reception...")

while True:
    # Check if it's time to switch channels
    now = time.ticks_ms()
    if time.ticks_diff(now, last_channel_switch) >= CHANNEL_DWELL_TIME_MS:
        # Switch to next channel
        current_channel = (current_channel + 1) % NUM_CHANNELS
        freq = get_channel_frequency(current_channel)
        sx.setFrequency(freq, calibrate=False)  # Don't recalibrate every time for speed
        last_channel_switch = now
        print(f"Switched to channel {current_channel} ({freq} MHz)")
    
    # Try to receive on current channel (non-blocking with short timeout)
    msg, status = sx.recv(timeout_en=True, timeout_ms=100)
    
    if status == 0 and len(msg) > 0:
        print(f"[Channel {current_channel}] Received: {msg}")
        print(f"RSSI: {sx.getRSSI():.2f} dBm, SNR: {sx.getSNR():.2f} dB")
```

#### Channel Hopping Pattern

For better coverage, use a channel hopping pattern instead of round-robin:

```python
# Channel hopping sequence (pseudorandom or predefined)
CHANNEL_HOP_SEQUENCE = [0, 3, 1, 4, 2, 5, 0, 3, ...]  # Spreads out channel usage

hop_index = 0

def get_next_channel():
    """Get next channel in hopping sequence"""
    global hop_index
    channel = CHANNEL_HOP_SEQUENCE[hop_index]
    hop_index = (hop_index + 1) % len(CHANNEL_HOP_SEQUENCE)
    return channel
```

### Multi-Channel Transmitter Example

Transmitter that uses multiple channels to send data streams in parallel:

```python
from sx1262 import SX1262
import time

# Initialize SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

MY_NODE_ADDRESS = 0x01
NUM_CHANNELS = 6

def send_on_channel(channel, data):
    """Send data on a specific channel"""
    freq = get_channel_frequency(channel)
    sx.setFrequency(freq, calibrate=False)
    payload_len, status = sx.send(data)
    return status == 0

# Example: Send different data streams on different channels
data_streams = [
    b"Stream 0 data",
    b"Stream 1 data",
    b"Stream 2 data",
    b"Stream 3 data",
]

# Send each stream on its corresponding channel
for channel, data in enumerate(data_streams):
    if send_on_channel(channel, data):
        print(f"Sent on channel {channel}: {data}")
    time.sleep_ms(100)  # Small delay between transmissions
```

### Complete Multi-Channel Network Example

This example shows a complete multi-channel communication system:

```python
from sx1262 import SX1262
import time

# Initialize SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

# Channel configuration
CHANNELS = {
    0: 868.0, 1: 868.1, 2: 868.2, 3: 868.3, 4: 868.4, 5: 868.5
}
NUM_CHANNELS = len(CHANNELS)
MY_NODE_ADDRESS = 0x01
BROADCAST_ADDRESS = 0xFF

# Initial configuration
sx.begin(freq=CHANNELS[0], bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

def get_channel_frequency(channel):
    return CHANNELS.get(channel, 868.0)

def switch_channel(channel):
    """Switch to specified channel"""
    freq = get_channel_frequency(channel)
    return sx.setFrequency(freq, calibrate=False) == 0

def get_my_channel():
    """Determine which channel this node should use"""
    # Option 1: Round-robin based on node address
    return MY_NODE_ADDRESS % NUM_CHANNELS
    
    # Option 2: Fixed channel assignment
    # return 1  # Node always uses channel 1

def send_with_channel(dest_addr, data, channel=None):
    """Send packet on specific channel (or default channel)"""
    if channel is None:
        channel = get_my_channel()
    
    # Switch to channel
    if not switch_channel(channel):
        return False
    
    # Create packet: [dest, src, data...]
    packet = bytes([dest_addr, MY_NODE_ADDRESS]) + data
    
    # Send
    payload_len, status = sx.send(packet)
    return status == 0

def receive_on_channel(channel, timeout_ms=1000):
    """Receive packet on specific channel"""
    if not switch_channel(channel):
        return None, None
    
    msg, status = sx.recv(timeout_en=True, timeout_ms=timeout_ms)
    
    if status == 0 and len(msg) >= 2:
        dest_addr = msg[0]
        src_addr = msg[1]
        data = msg[2:]
        
        # Check if for this node or broadcast
        if dest_addr == MY_NODE_ADDRESS or dest_addr == BROADCAST_ADDRESS:
            return src_addr, data
    
    return None, None

# Main loop: Multi-channel operation
my_channel = get_my_channel()
print(f"Node {MY_NODE_ADDRESS:02X} operating on channel {my_channel}")

# Option 1: Stay on assigned channel
switch_channel(my_channel)
while True:
    # Receive on my channel
    src, data = receive_on_channel(my_channel, timeout_ms=1000)
    if src is not None:
        print(f"[Ch{my_channel}] From {src:02X}: {data}")
    
    # Periodically send data
    if time.ticks_ms() % 5000 < 100:  # Every 5 seconds
        send_with_channel(BROADCAST_ADDRESS, b"Heartbeat", my_channel)
```

### Channel Selection Strategies

#### 1. Static Channel Assignment

Each node is permanently assigned to one channel:

```python
# Node 0x01 -> Channel 0
# Node 0x02 -> Channel 1
# Node 0x03 -> Channel 2
# etc.

def assign_channel_static(node_addr, num_channels):
    return node_addr % num_channels
```

**Pros**: Simple, predictable  
**Cons**: Uneven load distribution if nodes have different traffic

#### 2. Dynamic Channel Assignment

Nodes negotiate or discover available channels:

```python
# Broadcast channel request
def request_channel():
    # Send discovery on all channels
    for ch in range(NUM_CHANNELS):
        switch_channel(ch)
        sx.send(bytes([BROADCAST_ADDRESS, MY_NODE_ADDRESS, 0x01]))  # 0x01 = channel request
        time.sleep_ms(50)

# Use least loaded channel
def select_least_loaded_channel():
    # Measure RSSI on each channel (lower = less traffic)
    channel_load = {}
    for ch in range(NUM_CHANNELS):
        switch_channel(ch)
        time.sleep_ms(100)
        rssi = sx.getRSSI()
        channel_load[ch] = abs(rssi)  # Lower RSSI = less interference
    
    # Return channel with lowest load
    return min(channel_load, key=channel_load.get)
```

#### 3. Frequency Hopping

Nodes hop between channels in a synchronized pattern:

```python
# Synchronized hopping pattern (all nodes use same sequence)
HOP_SEQUENCE = [0, 2, 4, 1, 3, 5]  # Spreads out usage
HOP_INTERVAL_MS = 1000  # Hop every second

def get_current_channel_from_time():
    """Determine current channel based on time"""
    seconds = time.ticks_ms() // 1000
    hop_index = (seconds // (HOP_INTERVAL_MS // 1000)) % len(HOP_SEQUENCE)
    return HOP_SEQUENCE[hop_index]

# Use in main loop
current_ch = get_current_channel_from_time()
switch_channel(current_ch)
```

### Reducing Packet Loss with Multiple Channels

#### Problem: Collisions in Single Channel

In a single-channel network, when multiple nodes transmit simultaneously:
- Packets collide
- Packets are lost
- Network throughput decreases

#### Solution: Multi-Channel Operation

By using multiple channels:

1. **Spatial Separation**: Different nodes use different channels
2. **Parallel Transmission**: Multiple packets can be in the air simultaneously
3. **Reduced Collisions**: Fewer nodes per channel = fewer collisions
4. **Higher Throughput**: Total network capacity = sum of all channels

#### Channel Load Balancing

Distribute nodes evenly across channels:

```python
def balance_channel_load(nodes, channels):
    """Assign nodes to channels for balanced load"""
    nodes_per_channel = len(nodes) // len(channels)
    assignments = {}
    
    for i, node in enumerate(nodes):
        channel = (i // nodes_per_channel) % len(channels)
        assignments[node] = channel
    
    return assignments

# Example: 12 nodes, 6 channels = 2 nodes per channel
nodes = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C]
channels = [0, 1, 2, 3, 4, 5]
assignments = balance_channel_load(nodes, channels)
```

### Best Practices for Multi-Channel Networks

1. **Channel Spacing**: Ensure channels are spaced by at least the bandwidth used
   - For 125 kHz BW: Use at least 125 kHz spacing (868.0, 868.1, 868.2...)
   - For 500 kHz BW: Use at least 500 kHz spacing (868.0, 868.5, 869.0...)

2. **Frequency Calibration**: Calibrate when switching channels initially, then skip calibration for faster switching:
   ```python
   sx.setFrequency(freq, calibrate=True)   # First switch - calibrate
   sx.setFrequency(freq, calibrate=False)  # Subsequent switches - faster
   ```

3. **Channel Coordination**: Use a central coordinator or predefined pattern so nodes know which channel to use

4. **Regulatory Compliance**: Ensure all channels are within allowed frequency bands and respect duty cycle limits

5. **Channel Monitoring**: Periodically check channel quality (RSSI, SNR) and switch if channel is noisy

6. **Sync Word**: Can use different sync words per channel for additional isolation:
   ```python
   # Channel 0: sync word 0x12
   # Channel 1: sync word 0x34
   # Channel 2: sync word 0x56
   ```

### Channel vs. Sync Word

**Channels (Frequency)**:
- Physical layer separation
- Completely independent communication paths
- Requires frequency switching
- More effective for reducing collisions

**Sync Words**:
- Logical separation within same frequency
- Same physical channel, different logical networks
- No frequency switching needed
- Less effective for reducing collisions (same RF medium)

**Combined Approach** (Most Effective):
```python
# Different sync words on different channels
CHANNEL_CONFIG = {
    0: {'freq': 868.0, 'sync': 0x12},
    1: {'freq': 868.1, 'sync': 0x34},
    2: {'freq': 868.2, 'sync': 0x56},
}

def switch_to_channel_with_sync(channel):
    config = CHANNEL_CONFIG[channel]
    sx.setFrequency(config['freq'], calibrate=False)
    sx.setSyncWord(config['sync'])
```

This provides both physical (frequency) and logical (sync word) separation for maximum network isolation and reduced packet loss.

## Point-to-Point and Broadcast Communication

LoRa modulation does not have built-in hardware address filtering (unlike FSK mode). Therefore, addressing must be implemented at the application layer by including address information in the packet payload. This section explains how to implement point-to-point and broadcast communication.

### Understanding Addressing in LoRa

**Important**: LoRa mode does not support hardware-level address filtering. All nodes on the same frequency with matching LoRa parameters (SF, BW, CR, sync word) will receive all packets. Address filtering must be done in software by checking addresses in the packet payload.

### Packet Format for Addressing

A typical addressed packet format:

```
[Destination Address] [Source Address] [Data...]
```

For example:
- 1 byte destination address
- 1 byte source address  
- Up to 253 bytes of actual data

### Point-to-Point Communication

Point-to-point communication allows sending data to a specific node based on its address.

#### Transmitter (Sending to Specific Node)

```python
from sx1262 import SX1262

# Initialize and configure SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Define addresses
MY_NODE_ADDRESS = 0x01  # This node's address
DESTINATION_ADDRESS = 0x02  # Target node address
BROADCAST_ADDRESS = 0xFF  # Broadcast address (all nodes)

# Function to send data to a specific node
def send_to_node(dest_addr, data):
    # Create packet: [destination, source, data...]
    packet = bytes([dest_addr, MY_NODE_ADDRESS]) + data
    
    # Send the packet
    payload_len, status = sx.send(packet)
    if status == 0:
        print(f"Sent {len(data)} bytes to node {dest_addr:02X}")
    else:
        print(f"Send failed: {status}")
    return status

# Example: Send a message to node 0x02
message = b"Hello Node 0x02!"
send_to_node(DESTINATION_ADDRESS, message)
```

#### Receiver (Filtering by Address)

```python
from sx1262 import SX1262

# Initialize and configure SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Define this node's address
MY_NODE_ADDRESS = 0x02
BROADCAST_ADDRESS = 0xFF

# Receive loop with address filtering
print(f"Node {MY_NODE_ADDRESS:02X} listening...")
while True:
    msg, status = sx.recv()
    
    if status == 0 and len(msg) >= 2:
        # Extract addresses from packet
        dest_addr = msg[0]
        src_addr = msg[1]
        data = msg[2:]  # Rest of the packet is data
        
        # Check if packet is for this node or broadcast
        if dest_addr == MY_NODE_ADDRESS or dest_addr == BROADCAST_ADDRESS:
            print(f"Received from node {src_addr:02X}: {data}")
            print(f"RSSI: {sx.getRSSI():.2f} dBm, SNR: {sx.getSNR():.2f} dB")
            # Process the data here
        else:
            # Packet not for this node, ignore it
            print(f"Ignored packet: dest={dest_addr:02X}, src={src_addr:02X}")
    elif status == -6:  # RX_TIMEOUT
        pass  # No message received, continue
    else:
        print(f"Receive error: {status}")
```

### Broadcast Communication

Broadcast allows sending data to all nodes in the network simultaneously. Use a reserved broadcast address (commonly 0xFF).

#### Broadcast Transmitter

```python
# Broadcast to all nodes
BROADCAST_ADDRESS = 0xFF
message = b"Network Announcement: All nodes must update!"

# Create broadcast packet: [0xFF, source, data...]
packet = bytes([BROADCAST_ADDRESS, MY_NODE_ADDRESS]) + message
payload_len, status = sx.send(packet)

if status == 0:
    print(f"Broadcast sent to all nodes")
```

#### Broadcast Receiver

All nodes receive broadcast packets. The receiver code shown above already handles broadcasts by checking for `dest_addr == BROADCAST_ADDRESS`.

### Complete Network Example

Here's a complete example showing point-to-point and broadcast in one application:

```python
from sx1262 import SX1262
import time

# Initialize SX1262
sx = SX1262(spi_bus=1, clk='P2', mosi='P0', miso='P1', cs='P3', 
            irq='P13', rst='P6', gpio='P7', 
            spi_baudrate=2000000, spi_polarity=0, spi_phase=0)

sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Network configuration
MY_NODE_ADDRESS = 0x01  # Change this for each node (0x01, 0x02, 0x03, etc.)
BROADCAST_ADDRESS = 0xFF

def send_packet(dest_addr, data):
    """Send packet to destination address"""
    packet = bytes([dest_addr, MY_NODE_ADDRESS]) + data
    payload_len, status = sx.send(packet)
    return status == 0

def receive_packet():
    """Receive and filter packets by address"""
    msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
    
    if status == 0 and len(msg) >= 2:
        dest_addr = msg[0]
        src_addr = msg[1]
        data = msg[2:]
        
        # Accept if for this node or broadcast
        if dest_addr == MY_NODE_ADDRESS or dest_addr == BROADCAST_ADDRESS:
            return src_addr, data
    return None, None

# Main loop
print(f"Node {MY_NODE_ADDRESS:02X} started")

# Example 1: Broadcast a message every 30 seconds
broadcast_counter = 0

while True:
    # Try to receive packets (non-blocking with timeout)
    src, data = receive_packet()
    if src is not None:
        print(f"[{MY_NODE_ADDRESS:02X}] Received from {src:02X}: {data}")
    
    # Broadcast example (every 30 seconds)
    broadcast_counter += 1
    if broadcast_counter >= 30:  # ~30 seconds at 1 second intervals
        broadcast_counter = 0
        send_packet(BROADCAST_ADDRESS, b"Network heartbeat from node 0x01")
        print(f"[{MY_NODE_ADDRESS:02X}] Broadcast sent")
    
    time.sleep(1)
```

### Address Assignment Strategy

1. **Static Addressing**: Assign fixed addresses to each node (e.g., 0x01, 0x02, 0x03...)
2. **Reserved Addresses**: 
   - `0x00`: Unassigned/null address
   - `0xFF`: Broadcast address (all nodes)
   - `0x01-0xFE`: Available for node addresses (254 nodes max)

3. **Address Discovery**: Implement a protocol for nodes to discover each other:
   ```python
   # Discovery request (broadcast)
   discovery_request = bytes([BROADCAST_ADDRESS, MY_NODE_ADDRESS, 0x01])  # 0x01 = discovery
   sx.send(discovery_request)
   
   # Other nodes respond with their address
   ```

### Extended Packet Format (Recommended)

For more complex networks, use an extended format:

```
[Flags] [Destination] [Source] [Data Length] [Data...] [CRC/Checksum]
```

Example implementation:

```python
# Extended packet format constants
PACKET_FLAG_ACK_REQUIRED = 0x01
PACKET_FLAG_FRAGMENTED = 0x02
PACKET_TYPE_DATA = 0x10
PACKET_TYPE_ACK = 0x20
PACKET_TYPE_DISCOVERY = 0x30

def create_packet(dest_addr, src_addr, packet_type, data, flags=0):
    """Create packet with extended format"""
    packet_type_byte = packet_type | flags
    length = len(data)
    
    # Format: [type/flags, dest, src, length, data...]
    packet = bytes([packet_type_byte, dest_addr, src_addr, length]) + data
    return packet

def parse_packet(msg):
    """Parse extended format packet"""
    if len(msg) < 4:
        return None
    
    packet_type_byte = msg[0]
    dest_addr = msg[1]
    src_addr = msg[2]
    length = msg[3]
    
    if len(msg) < 4 + length:
        return None  # Incomplete packet
    
    packet_type = packet_type_byte & 0xF0
    flags = packet_type_byte & 0x0F
    data = msg[4:4+length]
    
    return {
        'type': packet_type,
        'flags': flags,
        'dest': dest_addr,
        'src': src_addr,
        'length': length,
        'data': data
    }
```

### FSK Mode Addressing (Hardware-Level)

**Note**: FSK mode supports hardware-level address filtering, but it's less commonly used than LoRa. If you need hardware filtering, use FSK mode:

```python
# Initialize in FSK mode
sx.beginFSK(freq=868.0, br=48.0, freqDev=50.0, rxBw=156.2, power=14, blocking=True)

# Set node address (hardware filtering - only accepts packets with this address)
sx.setNodeAddress(0x01)

# Set broadcast address (accepts packets with node address OR broadcast address)
sx.setBroadcastAddress(0xFF)

# Disable address filtering (accept all packets)
sx.disableAddressFiltering()
```

**Important**: Hardware address filtering in FSK mode only works for FSK modulation, not LoRa. Most LoRa applications use application-layer addressing as described above.

### Best Practices

1. **Use Reserved Broadcast Address**: Always use `0xFF` for broadcast to avoid conflicts
2. **Validate Addresses**: Check that source/destination addresses are valid before processing
3. **Address Length**: Use 1 byte (0-255) for simplicity, or extend to 2 bytes for larger networks
4. **Error Handling**: Handle cases where received packets are too short or malformed
5. **Network Size**: With 1-byte addressing, you can have up to 254 nodes (0x01-0xFE)
6. **Sync Word**: Use different sync words (0x12 private, 0x34 public) to create separate networks
7. **Security**: For sensitive data, add encryption after addressing layer

### Example: Multi-Node Network

```python
# Node 1: Coordinator
NODE_COORDINATOR = 0x01

# Node 2-10: Sensor nodes
NODE_SENSOR_BASE = 0x02

# Function to send sensor data to coordinator
def send_sensor_data(sensor_node_addr, sensor_data):
    packet = bytes([NODE_COORDINATOR, sensor_node_addr]) + sensor_data
    sx.send(packet)

# Coordinator receives from all sensors
# Sensors broadcast or send to coordinator
# Coordinator can send commands to specific sensors
```

This addressing scheme allows you to build complex multi-node networks where each node knows which messages are intended for it, while still supporting broadcast for network-wide messages.

## Power Saving and Sleep Mode

Power saving is crucial for battery-powered applications. The SX1262 module and OpenMV RT1062 can be put into sleep mode to minimize power consumption, and can be woken up either by receiving data on SX1262 (via interrupt) or by external wakeup from OpenMV.

### SX1262 Sleep Modes

The SX1262 module supports different sleep modes:

1. **Sleep Mode (Lowest Power)**: Complete shutdown, configuration may be retained
2. **Standby Mode**: Low power state, configuration retained, faster wakeup

### Putting SX1262 to Sleep

#### Basic Sleep

```python
# Put SX1262 to sleep (retain configuration)
status = sx.sleep(retainConfig=True)

# Put SX1262 to sleep (cold start - don't retain config)
status = sx.sleep(retainConfig=False)
```

**Parameters**:
- `retainConfig`: If `True`, configuration is retained (warm start). If `False`, configuration is lost (cold start, requires re-initialization).

**Returns**: Status code (0 = success)

**Power Consumption**:
- Sleep mode with retained config: ~0.85 µA (typical)
- Sleep mode without retained config: ~0.4 µA (typical)
- Standby mode: ~720 nA (typical)

#### Standby Mode (Alternative to Sleep)

For applications that need faster wakeup while still saving power:

```python
# Put SX1262 to standby mode
status = sx.standby()
```

Standby mode keeps the configuration in memory and allows faster wakeup than sleep mode.

### Wakeup from SX1262 Interrupt (RX Data Received)

The SX1262 can wake up the OpenMV RT1062 when data is received using the DIO1 interrupt pin (P13). This allows the OpenMV to sleep while the SX1262 actively listens for incoming packets.

**Important**: The SX1262 must be in RX (receive) mode, not sleep mode, to receive packets. Sleep mode is used when you don't need to receive data. For power-efficient reception, keep SX1262 in RX mode (~4.6 mA) and let OpenMV sleep.

#### Setting Up Interrupt-Based Wakeup

```python
from machine import Pin
import pyb  # For OpenMV RT1062

# Initialize and configure SX1262
sx = SX1262(
    spi_bus=1,
    clk='P2',
    mosi='P0',
    miso='P1',
    cs='P3',
    irq='P13',  # DIO1 - interrupt pin
    rst='P6',
    gpio='P7',
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure LoRa for reception
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=False  # Use non-blocking mode for interrupt-based operation
)

# Start receiving - this puts radio in RX mode and configures DIO1 interrupt
# The radio will trigger DIO1 (P13) when a packet is received
sx.setBlockingCallback(blocking=False)

# Define interrupt handler
def rx_interrupt_handler(pin):
    """Called when DIO1 (P13) goes high due to received packet"""
    # Read the received packet
    msg, status = sx.recv()
    if status == 0:
        print(f"Received: {msg}")
        print(f"RSSI: {sx.getRSSI():.2f} dBm")
        # Process received data here
    
    # Restart reception for next packet
    sx.setBlockingCallback(blocking=False)

# Set up interrupt on DIO1 pin (P13)
irq_pin = Pin('P13', Pin.IN, Pin.PULL_DOWN)
irq_pin.irq(trigger=Pin.IRQ_RISING, handler=rx_interrupt_handler)

print("SX1262 in RX mode, OpenMV sleeping - waiting for incoming data...")

# Put OpenMV RT1062 to sleep (wakes on interrupt from SX1262 DIO1)
while True:
    pyb.sleep()  # OpenMV sleep - wakes on interrupt
    # When packet arrives, DIO1 interrupt fires and rx_interrupt_handler is called
    # After handler completes, OpenMV wakes up and continues here
```

**Key Points**:
- DIO1 pin (P13) must be connected and configured as interrupt pin
- Radio must be configured for reception before sleep
- Use non-blocking mode (`blocking=False`) for interrupt-based operation
- The SX1262 module can listen for packets even in sleep mode (low power listening)
- When a packet is detected, DIO1 goes high, triggering the interrupt

#### Complete Power-Saving Example

```python
from sx1262 import SX1262
from machine import Pin
import pyb
import time

# Initialize SX1262
sx = SX1262(
    spi_bus=1,
    clk='P2',
    mosi='P0',
    miso='P1',
    cs='P3',
    irq='P13',  # DIO1 - interrupt pin
    rst='P6',
    gpio='P7',
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure LoRa
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=False  # Non-blocking for interrupts
)

# Global flag for received data
data_received = False
received_message = None

# Interrupt handler
def on_rx_interrupt(pin):
    global data_received, received_message
    # Read received packet
    msg, status = sx.recv()
    if status == 0:
        received_message = msg
        data_received = True
        print(f"Received: {msg}")
    
    # Restart reception
    sx.setBlockingCallback(blocking=False)

# Configure interrupt pin
irq_pin = Pin('P13', Pin.IN, Pin.PULL_DOWN)
irq_pin.irq(trigger=Pin.IRQ_RISING, handler=on_rx_interrupt)

print("SX1262 in RX mode, OpenMV entering sleep mode...")

# Main loop - SX1262 stays in RX mode (~4.6 mA), OpenMV sleeps
while True:
    # Note: SX1262 is already in RX mode (via setBlockingCallback)
    # Do NOT put SX1262 to sleep if you want to receive packets
    # The radio needs to be active in RX mode to receive data
    # This consumes ~4.6 mA, which is acceptable for most applications
    
    # Put OpenMV RT1062 to sleep (wakes on interrupt from SX1262 DIO1)
    pyb.sleep()
    
    # When interrupt occurs, handler is called automatically
    # After handler completes, we continue here
    if data_received:
        # Process received data
        print(f"Processing: {received_message}")
        data_received = False
    
    # Small delay to prevent tight loop
    time.sleep_ms(10)
```

### Wakeup from OpenMV (Manual Wakeup)

For scenarios where you don't need continuous reception, you can put SX1262 to sleep and wake it up manually from OpenMV code when needed (e.g., time-based transmission, sensor trigger):

```python
# Put SX1262 to sleep to save power
sx.sleep(retainConfig=True)

# ... OpenMV RT1062 continues processing or sleeps ...

# Wake up SX1262 when needed (e.g., time-based, sensor trigger)
status = sx.standby()  # Wake from sleep to standby

# If configuration was retained, you can immediately use the module
# If configuration was NOT retained (retainConfig=False), re-initialize:
# sx.begin(freq=868.0, bw=125.0, sf=9, cr=7, syncWord=0x12, power=14, blocking=True)

# Configure for reception if needed
sx.setBlockingCallback(blocking=False)

# Or send data immediately
sx.send(b"Hello!")

# After use, put back to sleep
sx.sleep(retainConfig=True)
```

**Use Case Example**: Periodic transmission
```python
import time
import pyb

while True:
    # Wake up SX1262
    sx.standby()
    
    # Send periodic data
    sx.send(b"Periodic update")
    
    # Put SX1262 back to sleep
    sx.sleep(retainConfig=True)
    
    # Put OpenMV to sleep for 60 seconds
    pyb.sleep(60000)  # Sleep for 60 seconds
```

### Power Saving Best Practices

1. **Use Sleep Mode**: Always put the module to sleep when not actively transmitting/receiving
2. **Retain Configuration**: Use `retainConfig=True` to avoid re-initialization overhead
3. **Interrupt-Based Reception**: Use DIO1 interrupt for lowest power consumption during RX
4. **Minimize Active Time**: Keep the radio active only when necessary
5. **Lower TX Power**: Use lower TX power when possible to save energy
6. **Duty Cycling**: Periodically wake, check for data, then sleep again

### Power Consumption Comparison

| Mode | SX1262 Current | Notes |
|------|----------------|-------|
| Sleep (retain config) | ~0.85 µA | Configuration retained, can wake on interrupt |
| Sleep (cold) | ~0.4 µA | Configuration lost, requires re-init |
| Standby | ~720 nA | Faster wakeup, config retained |
| RX Continuous | ~4.6 mA | Actively receiving |
| TX (14 dBm) | ~45 mA | Transmitting at full power |
| TX (0 dBm) | ~28 mA | Transmitting at low power |

### Important Notes

- **Interrupt Pin (P13/DIO1)**: Must be properly configured as an input with pull-down resistor
- **BUSY Pin (P7)**: The BUSY pin indicates when the module is processing commands. Check BUSY before sleep operations
- **Configuration Retention**: If `retainConfig=False`, you must call `begin()` again after wakeup
- **SPI Communication**: SPI communication is not possible while module is in sleep mode
- **Standby vs Sleep**: Use standby for faster wakeup, sleep for lowest power consumption
- **OpenMV Sleep**: Use `pyb.sleep()` to put the entire OpenMV RT1062 to sleep, which wakes on interrupts

## Troubleshooting

### Common Issues

#### 1. Module Not Responding

**Symptoms**: Initialization fails, SPI errors

**Solutions**:
- Verify all pin connections
- Check power supply (3.3V required)
- Ensure proper ground connections
- Verify SPI configuration matches module requirements
- Try reducing SPI baudrate if issues persist

#### 2. No Messages Received

**Symptoms**: TX works but RX doesn't receive

**Solutions**:
- Ensure both TX and RX use **identical** parameters:
  - Frequency
  - Spreading Factor
  - Bandwidth
  - Coding Rate
  - Sync Word
- Check antenna connections
- Verify antennas are properly mounted
- Increase TX power if distance is large
- Check for interference on frequency

#### 3. Timeout Errors

**Symptoms**: RX_TIMEOUT (-6) errors

**Solutions**:
- Increase timeout values
- Verify DIO1 (P13) is properly connected for interrupt signaling
- Check BUSY pin (P7) is working correctly
- Ensure TX is actually transmitting
- Check frequency and parameter matching

#### 4. CRC Errors

**Symptoms**: ERR_CRC_MISMATCH (-7)

**Solutions**:
- CRC errors are normal in noisy environments
- Increase TX power
- Reduce distance between TX and RX
- Use higher spreading factor (lower data rate) for better sensitivity
- Check antenna connections
- Verify proper grounding

#### 5. High Data Rate Issues

**Symptoms**: Many packet losses with SF5/BW500kHz configuration

**Solutions**:
- High data rate = shorter range and lower sensitivity
- Reduce distance between devices
- Ensure good line-of-sight
- Reduce interference
- Consider using lower data rate for better reliability

#### 6. ACK Protocol Issues

**Symptoms**: TX script retries repeatedly, RX doesn't receive

**Solutions**:
- Ensure RX script is running before TX starts
- Verify both scripts use same configuration
- Check that RX is properly sending ACKs
- Increase ACK timeout if needed
- Verify proper mode switching delays (50ms delays in code)

### Status Codes Reference

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

### Performance Tips

1. **For Maximum Range**:
   - Use SF12, BW125kHz, CR8
   - Increase TX power
   - Use directional antennas

2. **For Maximum Data Rate**:
   - Use SF5, BW500kHz, CR5
   - Keep devices close together
   - Ensure good line-of-sight

3. **For Balanced Performance**:
   - Use SF7-SF9, BW125kHz, CR7
   - Standard TX power (14 dBm)
   - Good general-purpose configuration

4. **For Low Power**:
   - Use higher spreading factors
   - Reduce TX power
   - Increase preamble length for better reception sensitivity

## License

Refer to the LICENSE file in the project root.

## References

- [Semtech SX1262 Datasheet](https://www.semtech.com/products/wireless-rf/lora-transceivers/sx1262)
- [Waveshare Core1262-868M Wiki](https://www.waveshare.com/wiki/Core1262-868M)
- [OpenMV RT1062 Documentation](https://docs.openmv.io/)
- Original library ported from [RadioLib](https://github.com/jgromes/RadioLib) by jgromes

