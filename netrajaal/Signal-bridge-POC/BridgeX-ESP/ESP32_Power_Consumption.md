# ESP32 Power Consumption Specifications

This document provides detailed power consumption specifications for the ESP32 microcontroller across different operating modes. Understanding these parameters is essential for power management and battery life optimization in your projects.

## Table of Contents

- [Voltage Specifications](#voltage-specifications)
- [Operating Modes](#operating-modes)
- [Power Consumption by Mode](#power-consumption-by-mode)
- [Peripheral Power Consumption](#peripheral-power-consumption)
- [Power Optimization Tips](#power-optimization-tips)
- [Battery Life Calculations](#battery-life-calculations)

---

## Voltage Specifications

### Operating Voltage Range
- **Recommended Operating Voltage**: 3.3V ± 0.1V
- **Absolute Maximum Voltage**: 3.6V
- **Absolute Minimum Voltage**: 2.3V (with reduced performance)
- **Typical Operating Voltage**: 3.3V

### Power Supply Requirements
- **Input Voltage Range**: 2.2V to 3.6V (when using internal LDO)
- **Input Voltage Range**: 2.7V to 3.6V (when using external 3.3V regulator)
- **Peak Current**: Up to 500 mA during Wi-Fi transmission
- **Average Current**: Varies by operating mode (see below)

---

## Operating Modes

The ESP32 supports multiple power modes to optimize energy consumption:

1. **Active Mode** - Full operation, all peripherals active
2. **Modem-Sleep Mode** - CPU active, Wi-Fi/Bluetooth disabled
3. **Light-Sleep Mode** - CPU paused, RTC active, peripherals can wake system
4. **Deep-Sleep Mode** - Most components powered down, RTC active
5. **Hibernation Mode** - Minimal power, only RTC timer active

---

## Power Consumption by Mode

### 1. Active Mode

**Description**: Full operation with CPU and all peripherals active.

| Component | Current Consumption | Voltage | Power |
|-----------|-------------------|---------|-------|
| **CPU @ 240 MHz** | 80-160 mA | 3.3V | 264-528 mW |
| **CPU @ 160 MHz** | 50-100 mA | 3.3V | 165-330 mW |
| **CPU @ 80 MHz** | 30-60 mA | 3.3V | 99-198 mW |
| **CPU @ 2.4 MHz** | 10-20 mA | 3.3V | 33-66 mW |

**Wi-Fi Transmission**:
| Mode | Data Rate | TX Power | Current | Power @ 3.3V |
|------|-----------|----------|---------|--------------|
| 802.11b | 1 Mbps | +19.5 dBm | ~240 mA | ~792 mW |
| 802.11g | 54 Mbps | +16 dBm | ~190 mA | ~627 mW |
| 802.11n | MCS7 | +14 dBm | ~180 mA | ~594 mW |
| 802.11n | MCS7 | +10 dBm | ~150 mA | ~495 mW |
| 802.11n | MCS7 | +5 dBm | ~120 mA | ~396 mW |

**Wi-Fi Reception**:
- **Current**: ~95-100 mA
- **Power @ 3.3V**: ~313-330 mW

**Bluetooth**:
| Mode | TX Power | Current | Power @ 3.3V |
|------|----------|---------|--------------|
| TX @ 0 dBm | - | ~130 mA | ~429 mW |
| RX | - | ~95-100 mA | ~313-330 mW |

**Typical Active Mode (No Wi-Fi/Bluetooth)**:
- **Current**: 50-100 mA (depending on CPU frequency)
- **Power @ 3.3V**: 165-330 mW

---

### 2. Modem-Sleep Mode

**Description**: CPU remains active, but Wi-Fi and Bluetooth modules are disabled.

| CPU Frequency | Current Consumption | Voltage | Power |
|---------------|-------------------|---------|-------|
| 240 MHz | ~20-30 mA | 3.3V | 66-99 mW |
| 160 MHz | ~20 mA | 3.3V | ~66 mW |
| 80 MHz | ~15 mA | 3.3V | ~49.5 mW |
| 2.4 MHz | ~5-10 mA | 3.3V | 16.5-33 mW |

**Typical Modem-Sleep**:
- **Current**: 15-30 mA
- **Power @ 3.3V**: 49.5-99 mW

---

### 3. Light-Sleep Mode

**Description**: CPU and most peripherals are paused, but RTC remains active. System can be woken by:
- GPIO interrupts
- Timer interrupts
- UART data
- Touch sensor
- External wake-up sources

**Power Consumption**:
- **Current**: ~130 μA (0.13 mA)
- **Voltage**: 3.3V
- **Power**: ~0.429 mW

**Wake-up Time**: ~1-2 ms

---

### 4. Deep-Sleep Mode

**Description**: Most components powered down except:
- RTC (Real-Time Clock)
- RTC memory
- RTC peripherals (ULP coprocessor, touch sensor, etc.)

**Power Consumption**:
- **Current**: ~5-10 μA (0.005-0.01 mA)
- **Voltage**: 3.3V
- **Power**: ~0.0165-0.033 mW

**Wake-up Sources**:
- Timer (RTC)
- External GPIO
- Touch sensor
- ULP coprocessor

**Wake-up Time**: ~100-200 ms

**Note**: All data in RAM is lost except RTC slow memory.

---

### 5. Hibernation Mode

**Description**: Minimal power consumption. Only RTC timer and RTC GPIOs remain active.

**Power Consumption**:
- **Current**: ~1-5 μA (0.001-0.005 mA)
- **Voltage**: 3.3V
- **Power**: ~0.0033-0.0165 mW

**Wake-up Sources**:
- RTC timer only
- External GPIO (RTC GPIOs only)

**Wake-up Time**: ~100-200 ms

**Note**: All data in RAM is lost. Only RTC slow memory is preserved.

---

## Peripheral Power Consumption

Additional power consumption when peripherals are active:

| Peripheral | Current Consumption | Notes |
|------------|-------------------|-------|
| **UART** | ~1-5 mA | Depends on baud rate |
| **SPI** | ~2-10 mA | Depends on clock speed |
| **I2C** | ~0.5-2 mA | Low power interface |
| **ADC** | ~1-3 mA | When sampling |
| **DAC** | ~2-5 mA | When outputting |
| **GPIO** | ~0.1-1 mA per pin | Depends on load |
| **LED (onboard)** | ~5-10 mA | If enabled |
| **Flash Memory** | ~5-15 mA | During read/write operations |

---

## Power Consumption with SX1262 LoRa Module

When using ESP32 with SX1262 LoRa module (as in this project):

### Active Transmission Mode
- **ESP32 (Active @ 80 MHz)**: ~50 mA
- **SX1262 (TX @ 22 dBm)**: ~120-150 mA
- **Total Current**: ~170-200 mA
- **Total Power @ 3.3V**: ~561-660 mW

### Active Reception Mode
- **ESP32 (Active @ 80 MHz)**: ~50 mA
- **SX1262 (RX)**: ~15-20 mA
- **Total Current**: ~65-70 mA
- **Total Power @ 3.3V**: ~214.5-231 mW

### Sleep Mode (ESP32 Deep-Sleep + LoRa Sleep)
- **ESP32 (Deep-Sleep)**: ~5-10 μA
- **SX1262 (Sleep)**: ~1-2 μA
- **Total Current**: ~6-12 μA
- **Total Power @ 3.3V**: ~0.02-0.04 mW

---

## Power Optimization Tips

### 1. Use Appropriate Sleep Modes
- Use **Light-Sleep** for short idle periods (< 1 second)
- Use **Deep-Sleep** for longer idle periods (> 1 second)
- Use **Hibernation** for very long idle periods (hours/days)

### 2. Reduce CPU Frequency
- Lower CPU frequency reduces power consumption significantly
- Use 80 MHz or 160 MHz instead of 240 MHz when possible
- Use 2.4 MHz for simple tasks

### 3. Disable Unused Peripherals
- Disable Wi-Fi and Bluetooth when not needed
- Turn off unused UART, SPI, I2C interfaces
- Disable ADC/DAC when not in use

### 4. Optimize Wi-Fi/Bluetooth Usage
- Reduce transmission power when possible
- Use lower data rates for Wi-Fi
- Minimize transmission time

### 5. GPIO Management
- Set unused GPIOs to input mode with pull-up/pull-down
- Avoid floating pins
- Disable internal pull-ups when using external resistors

### 6. Flash Memory Optimization
- Minimize flash read/write operations
- Use RAM for frequently accessed data
- Cache data when possible

---

## Battery Life Calculations

### Example 1: Battery-Powered LoRa Node

**Scenario**: ESP32 + SX1262 LoRa module powered by 18650 Li-ion battery (2600 mAh @ 3.7V)

**Usage Pattern**:
- Transmit every 5 minutes: 200 mA for 100 ms
- Receive for 1 second: 70 mA
- Deep-sleep for rest: 10 μA

**Calculations**:
- Active time per cycle: 1.1 seconds
- Sleep time per cycle: 298.9 seconds
- Average current per cycle:
  - Active: (200 mA × 0.1s + 70 mA × 1.0s) / 300s = 0.3 mA
  - Sleep: 10 μA = 0.01 mA
  - **Total average**: ~0.31 mA

- **Battery life**: 2600 mAh / 0.31 mA ≈ **8,387 hours ≈ 349 days**

### Example 2: Always-On Wi-Fi Device

**Scenario**: ESP32 with Wi-Fi always on, CPU @ 80 MHz

**Usage Pattern**:
- Wi-Fi RX: 100 mA
- CPU @ 80 MHz: 50 mA
- **Total**: ~150 mA

**Battery Life** (18650, 2600 mAh):
- **Battery life**: 2600 mAh / 150 mA ≈ **17.3 hours**

### Example 3: Periodic Sensor Node

**Scenario**: ESP32 reads sensor every 10 seconds, transmits via LoRa

**Usage Pattern**:
- Active (read + transmit): 200 mA for 200 ms every 10 seconds
- Deep-sleep: 10 μA for rest

**Calculations**:
- Average current: (200 mA × 0.2s) / 10s + 0.01 mA ≈ 4.01 mA

**Battery Life** (18650, 2600 mAh):
- **Battery life**: 2600 mAh / 4.01 mA ≈ **648 hours ≈ 27 days**

---

## Power Supply Recommendations

### For Battery-Powered Applications

1. **Li-ion/Li-Po Battery** (3.7V nominal)
   - Use LDO or switching regulator to 3.3V
   - Consider battery protection circuit
   - Monitor battery voltage

2. **AA/AAA Batteries** (1.5V each)
   - Use 2-3 batteries in series (3V-4.5V)
   - Use voltage regulator to 3.3V
   - Consider low-dropout (LDO) regulator

3. **USB Power** (5V)
   - Use AMS1117 or similar 3.3V regulator
   - Add decoupling capacitors
   - Consider USB-C for higher current capacity

### For Mains-Powered Applications

1. **AC-DC Adapter** (5V or 12V)
   - Use switching regulator for efficiency
   - Add filtering capacitors
   - Consider over-voltage protection

2. **Power Bank** (5V USB)
   - Use 3.3V LDO regulator
   - Monitor power bank capacity
   - Consider low-power design for portability

---

## References

- ESP32 Technical Reference Manual
- ESP32 Datasheet
- Espressif ESP32 Power Management Documentation
- Last Minute Engineers - ESP32 Sleep Modes Guide

---

## Notes

- Power consumption values are typical and may vary based on:
  - Manufacturing variations
  - Operating temperature
  - PCB design and layout
  - External components and loads
  - Code efficiency

- Always measure actual power consumption in your specific application for accurate battery life calculations.

- For critical applications, add a 20-30% safety margin to battery life calculations.

---

**Last Updated**: 2024
**Document Version**: 1.0

