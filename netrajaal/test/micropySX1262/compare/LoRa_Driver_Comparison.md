# LoRa Driver Comparison: SX1262 868M LoRa HAT vs Core1262-868M

## Executive Summary

This document compares two different LoRa module drivers for OpenMV RT1062:
- **SX1262 868M LoRa HAT** (`sx1262_lora_hat.py`) - UART-based module with proprietary protocol
- **Core1262-868M** (`sx126x.py`, `sx1262.py`, `_sx126x.py`) - SPI-based module with direct chip control

---

## 1. Module Overview

### 1.1 SX1262 868M LoRa HAT (UART-based)

**Hardware Interface:**
- **Communication:** UART (Serial)
- **Initial Baud Rate:** 9600 bps (configuration mode)
- **Operating Baud Rate:** 115200 bps (normal mode)
- **Control Pins:** M0, M1 (GPIO for mode switching)
- **Protocol:** Proprietary AT-like command protocol

**Module Type:** Pre-configured LoRa module with built-in firmware that handles LoRa modulation internally.

### 1.2 Core1262-868M (SPI-based)

**Hardware Interface:**
- **Communication:** SPI (Serial Peripheral Interface)
- **SPI Baud Rate:** 2,000,000 bps (configurable)
- **Control Pins:** CS (Chip Select), IRQ (Interrupt), RST (Reset), GPIO (Busy)
- **Protocol:** Direct register access to SX1262 chip

**Module Type:** Bare SX1262 chip with direct hardware control.

---

## 2. Communication Interface Comparison

### 2.1 SX1262 LoRa HAT (UART)

| Aspect | Details |
|--------|---------|
| **Interface** | UART (Universal Asynchronous Receiver-Transmitter) |
| **Speed** | 9600 bps (config), 115200 bps (operation) |
| **Pins Required** | TX, RX, M0, M1 (4 pins minimum) |
| **Protocol** | Proprietary 12-byte configuration register |
| **Mode Switching** | Hardware-based via M0/M1 pins |
| **Latency** | Higher (UART overhead + protocol parsing) |
| **Throughput** | Limited by UART speed and protocol overhead |

**Characteristics:**
- Simple serial communication
- Requires mode switching (M0/M1 pins) for configuration
- Configuration done via 12-byte register writes
- Built-in protocol handling on module side
- Message format includes addressing headers (7 bytes overhead)

### 2.2 Core1262-868M (SPI)

| Aspect | Details |
|--------|---------|
| **Interface** | SPI (Serial Peripheral Interface) |
| **Speed** | 2,000,000 bps (configurable) |
| **Pins Required** | CLK, MOSI, MISO, CS, IRQ, RST, GPIO (7 pins) |
| **Protocol** | Direct register access (Semtech SX1262 commands) |
| **Mode Switching** | Software-controlled via SPI commands |
| **Latency** | Lower (direct register access) |
| **Throughput** | Higher (SPI is faster, less overhead) |

**Characteristics:**
- High-speed synchronous communication
- Direct access to chip registers
- No mode switching required
- Lower-level control with more flexibility
- Minimal protocol overhead

---

## 3. Configuration and Control

### 3.1 SX1262 LoRa HAT Configuration

**Configuration Method:**
```python
# Configuration via 12-byte register array
cfg_reg = [
    0xC2,  # Header (volatile)
    0x00,  # Length high
    0x09,  # Length low
    addr_h, addr_l,  # Node address
    net_id,  # Network ID
    uart_baud + air_speed,  # Combined register
    buffer_size + power + 0x20,  # Combined register
    freq_offset,  # Frequency offset
    mode + rssi_flag,  # Mode + RSSI enable
    crypt_h, crypt_l  # Encryption key
]
```

**Limitations:**
- Fixed parameter combinations (air speed limited to predefined values: 1200-62500 bps)
- Frequency specified as offset from base (410MHz or 850MHz)
- Power limited to 4 levels: 10, 13, 17, 22 dBm
- Buffer size limited to: 32, 64, 128, 240 bytes
- Requires mode switching (M0/M1) for configuration
- Configuration retry logic needed (up to 3 attempts)

**Configuration Parameters:**
- Frequency: 410-493 MHz or 850-930 MHz (as offset)
- Power: 10, 13, 17, 22 dBm (4 levels)
- Air Speed: 1200, 2400, 4800, 9600, 19200, 38400, 62500 bps
- Buffer Size: 32, 64, 128, 240 bytes
- Address: 0-65535
- Network ID: 0-255
- Encryption: 0-65535 (simple key)

### 3.2 Core1262-868M Configuration

**Configuration Method:**
```python
# Direct register access via SPI commands
lora.begin(
    freq=434.0,      # Direct frequency in MHz
    bw=125.0,        # Bandwidth in kHz
    sf=9,            # Spreading factor (5-12)
    cr=7,            # Coding rate (5-8)
    power=14,        # Power in dBm (-9 to 22)
    syncWord=0x12,   # Sync word
    currentLimit=60.0,
    preambleLength=8,
    implicit=False,
    crcOn=True
)
```

**Advantages:**
- Direct frequency specification (150-960 MHz)
- Fine-grained power control (-9 to 22 dBm)
- Full LoRa parameter control (SF, BW, CR)
- Configurable preamble length
- Explicit/implicit header mode
- CRC control
- IQ inversion support
- TCXO voltage configuration
- Regulator mode selection (LDO/DCDC)

**Configuration Parameters:**
- Frequency: 150-960 MHz (continuous range)
- Power: -9 to 22 dBm (fine-grained)
- Spreading Factor: 5-12 (full range)
- Bandwidth: 7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500 kHz
- Coding Rate: 4/5, 4/6, 4/7, 4/8
- Preamble Length: Configurable
- Sync Word: Customizable
- Current Limit: Configurable

---

## 4. Feature Comparison

### 4.1 Modulation Support

| Feature | SX1262 LoRa HAT | Core1262-868M |
|---------|----------------|---------------|
| **LoRa Modulation** | ✅ Yes (fixed parameters) | ✅ Yes (full control) |
| **GFSK Modulation** | ❌ No | ✅ Yes |
| **Modulation Switching** | ❌ No | ✅ Yes (runtime) |

### 4.2 Addressing and Routing

| Feature | SX1262 LoRa HAT | Core1262-868M |
|---------|----------------|---------------|
| **Node Addressing** | ✅ Built-in (0-65535) | ⚠️ Manual (GFSK only) |
| **Network ID** | ✅ Yes (0-255) | ❌ No |
| **Broadcast Support** | ✅ Yes (0xFFFF) | ⚠️ Manual implementation |
| **Relay Mode** | ✅ Built-in | ❌ No |
| **Address Filtering** | ✅ Hardware-based | ⚠️ Software-based (GFSK) |

### 4.3 Advanced Features

| Feature | SX1262 LoRa HAT | Core1262-868M |
|---------|----------------|---------------|
| **RSSI Reporting** | ✅ Packet RSSI + Noise RSSI | ✅ Packet RSSI + SNR |
| **Encryption** | ✅ Simple key (0-65535) | ❌ No (application layer) |
| **Listen Before Talk (LBT)** | ⚠️ Declared but not implemented | ✅ CAD (Channel Activity Detection) |
| **Wake On Radio (WOR)** | ⚠️ Declared but not implemented | ✅ Duty cycle RX |
| **Low Power Modes** | ⚠️ Limited | ✅ Sleep, Standby modes |
| **Interrupt Support** | ❌ Polling only | ✅ IRQ pin support |
| **Blocking/Non-blocking** | ❌ Blocking only | ✅ Both modes |
| **Callback Functions** | ❌ No | ✅ Yes (non-blocking mode) |

### 4.4 Performance Characteristics

| Aspect | SX1262 LoRa HAT | Core1262-868M |
|--------|----------------|---------------|
| **Configuration Time** | ~500-1000ms (mode switching + retries) | ~50-100ms (direct SPI) |
| **Message Overhead** | 7 bytes (address + freq headers) | 0-4 bytes (LoRa header) |
| **Max Packet Size** | 240 bytes (configurable: 32/64/128/240) | 255 bytes (LoRa standard) |
| **Air Data Rate** | Fixed: 1200-62500 bps | Configurable: Depends on SF/BW |
| **Communication Latency** | Higher (UART + protocol) | Lower (SPI direct) |
| **Throughput** | Limited by UART speed | Higher (SPI speed) |

---

## 5. Pros and Cons

### 5.1 SX1262 868M LoRa HAT (UART-based)

#### ✅ **Pros**

1. **Simplicity**
   - Easy to use - just send/receive data
   - Built-in addressing and routing
   - No need to understand LoRa parameters (SF, BW, CR)
   - Simple configuration interface

2. **Built-in Features**
   - Hardware-based addressing (0-65535)
   - Network ID support for network isolation
   - Built-in relay mode for mesh networking
   - Simple encryption support
   - Automatic message routing

3. **Ease of Integration**
   - Fewer pins required (UART + 2 GPIO)
   - Standard UART interface (widely supported)
   - Less code complexity
   - Good for rapid prototyping

4. **Protocol Abstraction**
   - Module handles LoRa protocol internally
   - Application doesn't need to manage LoRa parameters
   - Message format is straightforward

#### ❌ **Cons**

1. **Limited Flexibility**
   - Fixed air data rates (7 options: 1200-62500 bps)
   - Limited power levels (4 options: 10, 13, 17, 22 dBm)
   - Frequency specified as offset (not direct)
   - Cannot fine-tune LoRa parameters (SF, BW, CR)

2. **Performance Limitations**
   - UART speed limits throughput (115200 bps)
   - Higher latency due to protocol overhead
   - 7-byte message overhead per packet
   - Mode switching required for configuration

3. **Configuration Complexity**
   - Requires M0/M1 pin control for mode switching
   - Configuration retry logic needed
   - Baud rate switching during initialization
   - Potential timing issues

4. **Limited Control**
   - Cannot access advanced LoRa features
   - No GFSK modulation support
   - No direct register access
   - Limited debugging capabilities

5. **Dependency on Module Firmware**
   - Proprietary protocol (not standard LoRaWAN)
   - Cannot communicate with standard LoRa modules
   - Module-specific implementation
   - Less portable across different hardware

### 5.2 Core1262-868M (SPI-based)

#### ✅ **Pros**

1. **Full Control**
   - Direct access to SX1262 chip registers
   - Complete control over all LoRa parameters
   - Fine-grained frequency control (150-960 MHz)
   - Precise power control (-9 to 22 dBm)

2. **Advanced Features**
   - Both LoRa and GFSK modulation support
   - Configurable spreading factor (5-12)
   - Configurable bandwidth (7.8-500 kHz)
   - Configurable coding rate (4/5 to 4/8)
   - Explicit/implicit header modes
   - IQ inversion support

3. **Performance**
   - Higher throughput (SPI: 2 Mbps vs UART: 115.2 kbps)
   - Lower latency (direct register access)
   - Minimal protocol overhead
   - Faster configuration (~50ms vs ~500ms)

4. **Flexibility**
   - Blocking and non-blocking modes
   - Interrupt-driven operation (IRQ pin)
   - Callback function support
   - Duty cycle RX for power saving
   - CAD (Channel Activity Detection)
   - Sleep and standby modes

5. **Standard Compliance**
   - Standard LoRa modulation
   - Compatible with other LoRa devices
   - Can implement LoRaWAN if needed
   - Better for interoperability

6. **Debugging and Development**
   - Direct register access for debugging
   - More visibility into chip state
   - Better error reporting
   - Can read chip status and errors

#### ❌ **Cons**

1. **Complexity**
   - More complex API (many parameters)
   - Need to understand LoRa parameters (SF, BW, CR)
   - More code to write and maintain
   - Steeper learning curve

2. **More Pins Required**
   - SPI interface: CLK, MOSI, MISO, CS (4 pins)
   - Control pins: IRQ, RST, GPIO (3 pins)
   - Total: 7 pins vs 4 pins for UART version

3. **Manual Implementation**
   - Addressing must be implemented in application
   - No built-in routing or relay
   - No built-in encryption (application layer)
   - More application code required

4. **Configuration Overhead**
   - More parameters to configure
   - Need to understand LoRa parameter relationships
   - Parameter validation required
   - More potential for misconfiguration

5. **Hardware Requirements**
   - Requires SPI interface (not all boards have it)
   - More complex pin routing
   - IRQ pin needed for efficient operation

---

## 6. Use Case Recommendations

### 6.1 Choose SX1262 LoRa HAT When:

✅ **Simple Point-to-Point Communication**
- Basic data transmission between two nodes
- Don't need fine-grained control
- Want simple addressing

✅ **Rapid Prototyping**
- Quick development cycles
- Minimal code complexity
- Standard UART interface available

✅ **Mesh Networking**
- Need built-in relay functionality
- Want hardware-based addressing
- Network ID for network isolation

✅ **Limited Pin Availability**
- Only have UART + 2 GPIO pins available
- Cannot spare SPI pins

✅ **Application-Level Simplicity**
- Don't want to manage LoRa parameters
- Prefer higher-level API
- Simple send/receive operations

### 6.2 Choose Core1262-868M When:

✅ **Full LoRa Control Required**
- Need to optimize for specific use case
- Want to fine-tune SF, BW, CR parameters
- Need maximum range or throughput

✅ **Standard LoRa Compatibility**
- Want to communicate with standard LoRa devices
- Planning to implement LoRaWAN
- Need interoperability

✅ **Advanced Features**
- Need GFSK modulation
- Want interrupt-driven operation
- Need low-power modes (sleep, duty cycle)
- Require CAD (Channel Activity Detection)

✅ **Performance Critical**
- Need maximum throughput
- Low latency requirements
- High data rate applications

✅ **Flexible Modulation**
- Need to switch between LoRa and GFSK
- Want to experiment with different modulations
- Research and development applications

✅ **Power Optimization**
- Battery-powered applications
- Need sleep modes
- Duty cycle RX for power saving

---

## 7. Code Complexity Comparison

### 7.1 SX1262 LoRa HAT

**Initialization:**
```python
lora = sx126x(
    uart_num=1,
    freq=868,
    addr=0x0001,
    power=22,
    rssi=True,
    air_speed=2400
)
```

**Send Message:**
```python
lora.send(target_addr=0x0002, message=b"Hello World")
```

**Receive Message:**
```python
msg, rssi = lora.receive()
if msg:
    print(f"Received: {msg}, RSSI: {rssi}")
```

**Lines of Code:** ~1100 lines (single file)

### 7.2 Core1262-868M

**Initialization:**
```python
lora = SX1262(spi_bus=1, clk="P10", mosi="P11", miso="P12", 
               cs="P13", irq="P14", rst="P15", gpio="P16")
lora.begin(freq=868.0, bw=125.0, sf=9, cr=7, 
           power=14, syncWord=0x12)
```

**Send Message:**
```python
data = b"Hello World"
length, state = lora.send(data)
```

**Receive Message:**
```python
data, state = lora.recv(len=0, timeout_en=True, timeout_ms=5000)
if state == ERR_NONE:
    print(f"Received: {data}")
```

**Lines of Code:** ~2800 lines (3 files: `_sx126x.py`, `sx126x.py`, `sx1262.py`)

---

## 8. Performance Benchmarks

### 8.1 Configuration Time

| Module | Configuration Time | Notes |
|--------|------------------|-------|
| SX1262 LoRa HAT | ~500-1000ms | Includes mode switching, baud rate change, retries |
| Core1262-868M | ~50-100ms | Direct SPI register writes |

### 8.2 Message Overhead

| Module | Overhead per Message | Details |
|--------|---------------------|---------|
| SX1262 LoRa HAT | 7 bytes | Target addr (2) + freq (1) + Source addr (2) + freq (1) + newline (1) |
| Core1262-868M | 0-4 bytes | LoRa header (implicit: 0, explicit: 1-4 bytes) |

### 8.3 Maximum Throughput

| Module | Theoretical Max | Practical Max | Limiting Factor |
|--------|----------------|---------------|----------------|
| SX1262 LoRa HAT | ~14 KB/s | ~10 KB/s | UART speed (115200 bps) |
| Core1262-868M | Depends on SF/BW | Higher | SPI speed (2 Mbps) + LoRa air rate |

### 8.4 Power Consumption

| Module | TX Current | RX Current | Sleep Current |
|--------|-----------|-----------|---------------|
| SX1262 LoRa HAT | ~100mA | ~11mA | ~2µA (deep sleep) |
| Core1262-868M | Similar | Similar | Similar (with sleep mode) |

---

## 9. Integration with OpenMV RT1062

### 9.1 SX1262 LoRa HAT

**Pin Requirements:**
- UART1: TX, RX
- GPIO: P6 (M0), P7 (M1)

**Advantages:**
- Uses standard UART (widely available)
- Simple pin configuration
- No SPI bus conflicts

**Disadvantages:**
- Uses UART (may conflict with other UART devices)
- Requires 2 GPIO pins for mode control

### 9.2 Core1262-868M

**Pin Requirements:**
- SPI1: CLK, MOSI, MISO
- GPIO: P13 (CS), P14 (IRQ), P15 (RST), P16 (GPIO/Busy)

**Advantages:**
- SPI is faster and more efficient
- IRQ pin enables interrupt-driven operation
- Better for real-time applications

**Disadvantages:**
- Requires SPI interface (may conflict with other SPI devices)
- More pins required
- More complex pin routing

---

## 10. Summary and Recommendations

### 10.1 Quick Decision Matrix

| Requirement | SX1262 LoRa HAT | Core1262-868M |
|------------|----------------|---------------|
| **Simple point-to-point** | ✅ Better | ⚠️ More complex |
| **Full LoRa control** | ❌ Limited | ✅ Better |
| **Standard LoRa compatibility** | ❌ Proprietary | ✅ Standard |
| **Mesh networking** | ✅ Built-in | ❌ Manual |
| **Maximum performance** | ❌ Limited | ✅ Better |
| **Low power operation** | ⚠️ Limited | ✅ Better |
| **Rapid prototyping** | ✅ Better | ⚠️ More setup |
| **Minimal pins** | ✅ Better (4 pins) | ❌ More (7 pins) |
| **GFSK modulation** | ❌ No | ✅ Yes |
| **Interrupt-driven** | ❌ No | ✅ Yes |

### 10.2 Final Recommendations

**For Most Users (Simple Applications):**
- **Choose SX1262 LoRa HAT** if you need:
  - Simple point-to-point communication
  - Built-in addressing and routing
  - Rapid prototyping
  - Minimal code complexity

**For Advanced Users (Full Control):**
- **Choose Core1262-868M** if you need:
  - Full control over LoRa parameters
  - Standard LoRa compatibility
  - Maximum performance
  - Advanced features (GFSK, interrupts, low power)
  - Research and development

**For Production Systems:**
- **Core1262-868M** is recommended for:
  - Standard compliance
  - Interoperability
  - Performance optimization
  - Future-proofing

---

## 11. Migration Considerations

### 11.1 Migrating from SX1262 LoRa HAT to Core1262-868M

**Code Changes Required:**
1. Replace UART initialization with SPI initialization
2. Change configuration method (from 12-byte register to parameter-based)
3. Implement addressing in application layer
4. Update send/receive methods
5. Add error handling for SPI operations

**Hardware Changes:**
1. Replace UART connection with SPI
2. Add IRQ, RST, GPIO pins
3. Remove M0, M1 pins (no longer needed)

**Benefits After Migration:**
- Better performance
- More control
- Standard compliance
- Advanced features

### 11.2 Migrating from Core1262-868M to SX1262 LoRa HAT

**Code Changes Required:**
1. Replace SPI with UART
2. Simplify configuration
3. Use built-in addressing
4. Update message format (add addressing headers)

**Hardware Changes:**
1. Replace SPI with UART
2. Add M0, M1 pins
3. Remove IRQ, RST, GPIO pins

**Trade-offs:**
- Simpler code
- Less control
- Lower performance
- Proprietary protocol

---

## 12. Conclusion

Both drivers serve different purposes:

- **SX1262 LoRa HAT** excels in simplicity, ease of use, and rapid prototyping with built-in features like addressing and routing.

- **Core1262-868M** excels in performance, flexibility, standard compliance, and advanced features with full control over LoRa parameters.

The choice depends on your specific requirements:
- **Choose SX1262 LoRa HAT** for simple applications and rapid development.
- **Choose Core1262-868M** for advanced applications requiring full control, standard compliance, and maximum performance.

For production systems and long-term projects, **Core1262-868M** is generally recommended due to its standard compliance, better performance, and future-proofing capabilities.

---

## References

- [SX1262 868M LoRa HAT Wiki](https://www.waveshare.com/wiki/SX1262_868M_LoRa_HAT)
- [Core1262-868M Wiki](https://www.waveshare.com/wiki/Core1262-868M)
- Semtech SX1262 Datasheet
- LoRaWAN Specification

---

*Document generated for OpenMV RT1062 LoRa integration comparison*

