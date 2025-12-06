# BridgeX-ESP - ESP32 Light Sleep Mode Test

This project demonstrates and tests the light sleep mode functionality on ESP32 using ESP-IDF framework.

## Project Overview

The project includes a comprehensive test for ESP32 light sleep mode, which allows the CPU to be paused while keeping peripherals active. This is useful for power-sensitive applications where you need to reduce power consumption while maintaining the ability to wake up quickly.

## Features

- Light sleep mode implementation with timer wake-up
- LED indicator for visual feedback
- System information logging
- Sleep duration measurement
- Multiple sleep cycles for testing

## Building and Flashing

### Prerequisites

- ESP-IDF v4.4 or later
- Python 3.6 or later
- CMake 3.5 or later

### Build Steps

1. Set up ESP-IDF environment:
   ```bash
   . $HOME/esp/esp-idf/export.sh
   ```

2. Navigate to project directory:
   ```bash
   cd BridgeX-ESP
   ```

3. Configure the project (optional):
   ```bash
   idf.py menuconfig
   ```

4. Build the project:
   ```bash
   idf.py build
   ```

5. Flash to ESP32:
   ```bash
   idf.py -p /dev/ttyUSB0 flash
   ```

6. Monitor serial output:
   ```bash
   idf.py -p /dev/ttyUSB0 monitor
   ```

## Project Structure

```
├── CMakeLists.txt          # Main CMake configuration
├── main
│   ├── CMakeLists.txt     # Component CMake configuration
│   └── main.c             # Main application code with light sleep test
└── README.md              # This file
```

## How the Light Sleep Test Works

The test performs the following operations:

1. **Initialization**: Sets up GPIO for LED control and prints system information
2. **Active Period**: Blinks LED 3 times to indicate active state
3. **Light Sleep**: Enters light sleep mode for 5 seconds using timer wake-up
4. **Wake-up**: Automatically wakes up after the timer expires
5. **Cycle**: Repeats the process for 10 cycles

### Key Functions

- `enter_light_sleep()`: Configures timer wake-up and enters light sleep mode
- `print_system_info()`: Displays CPU frequency, heap memory, and other system stats
- `toggle_led()`: Controls LED for visual feedback

## ESP32 Power Consumption by Mode

The following power consumption values are typical for ESP32 modules. Actual values may vary based on:
- ESP32 variant (ESP32, ESP32-S2, ESP32-S3, ESP32-C3, etc.)
- CPU frequency
- Enabled peripherals
- External components
- Operating temperature

### ESP32 (Classic) Power Consumption

| Mode | CPU | WiFi | Bluetooth | Typical Current | Notes |
|------|-----|------|-----------|-----------------|-------|
| **Active (Normal)** | ON | ON | ON | 80-240 mA | Depends on CPU frequency and radio activity |
| **Active (WiFi TX)** | ON | TX | OFF | 170-240 mA | Transmitting at max power |
| **Active (WiFi RX)** | ON | RX | OFF | 80-100 mA | Receiving data |
| **Active (WiFi OFF)** | ON | OFF | OFF | 20-50 mA | CPU running, no radio |
| **Modem Sleep** | ON | OFF | OFF | 20-50 mA | WiFi/Bluetooth disabled, CPU active |
| **Light Sleep** | OFF | OFF | OFF | **0.8-1.2 mA** | CPU paused, RTC running, peripherals can wake |
| **Deep Sleep** | OFF | OFF | OFF | **10-150 μA** | Only RTC running, most peripherals off |
| **Hibernation** | OFF | OFF | OFF | **2.5-5 μA** | Ultra-low power, RTC slow clock only |

### ESP32-S2 Power Consumption

| Mode | CPU | WiFi | Typical Current | Notes |
|------|-----|------|-----------------|-------|
| **Active (Normal)** | ON | ON | 80-200 mA | Depends on CPU frequency |
| **Active (WiFi TX)** | ON | TX | 160-220 mA | Transmitting at max power |
| **Active (WiFi RX)** | ON | RX | 80-100 mA | Receiving data |
| **Active (WiFi OFF)** | ON | OFF | 15-40 mA | CPU running, no radio |
| **Light Sleep** | OFF | OFF | **0.8-1.0 mA** | CPU paused, RTC running |
| **Deep Sleep** | OFF | OFF | **10-150 μA** | Only RTC running |

### ESP32-S3 Power Consumption

| Mode | CPU | WiFi | Bluetooth | Typical Current | Notes |
|------|-----|------|-----------|-----------------|-------|
| **Active (Normal)** | ON | ON | ON | 80-240 mA | Dual-core, higher performance |
| **Active (WiFi OFF)** | ON | OFF | OFF | 20-50 mA | CPU running, no radio |
| **Light Sleep** | OFF | OFF | OFF | **0.8-1.2 mA** | CPU paused, RTC running |
| **Deep Sleep** | OFF | OFF | OFF | **10-150 μA** | Only RTC running |

### ESP32-C3 Power Consumption

| Mode | CPU | WiFi | Bluetooth | Typical Current | Notes |
|------|-----|------|-----------|-----------------|-------|
| **Active (Normal)** | ON | ON | ON | 50-160 mA | RISC-V architecture |
| **Active (WiFi OFF)** | ON | OFF | OFF | 15-35 mA | CPU running, no radio |
| **Light Sleep** | OFF | OFF | OFF | **0.7-1.0 mA** | CPU paused, RTC running |
| **Deep Sleep** | OFF | OFF | OFF | **5-100 μA** | Only RTC running |

## Light Sleep Mode Details

### Characteristics

- **Wake-up Time**: ~1-2 ms (very fast)
- **State Retention**: 
  - CPU state is lost (program continues from wake-up point)
  - RTC memory is retained
  - GPIO states are retained
  - Peripheral registers are retained
- **Wake-up Sources**:
  - Timer (RTC timer)
  - GPIO (external interrupt)
  - UART (data received)
  - Touch sensor
  - SDIO slave
  - WiFi/Bluetooth (if enabled)

### Advantages

- Very low power consumption (0.8-1.2 mA)
- Fast wake-up time (~1-2 ms)
- Peripherals can remain active
- GPIO states preserved
- Can wake on multiple sources

### Use Cases

- Battery-powered applications
- IoT sensors that need periodic wake-up
- Applications requiring fast response to external events
- Systems that need to reduce power while maintaining peripheral functionality

## Deep Sleep vs Light Sleep

| Feature | Light Sleep | Deep Sleep |
|---------|-------------|------------|
| **Current Consumption** | 0.8-1.2 mA | 10-150 μA |
| **Wake-up Time** | ~1-2 ms | ~100-200 ms |
| **CPU State** | Lost | Lost |
| **RTC Memory** | Retained | Retained |
| **GPIO States** | Retained | Lost (except RTC GPIO) |
| **Peripheral Registers** | Retained | Lost |
| **WiFi/Bluetooth** | Can wake | Cannot wake |
| **UART** | Can wake | Cannot wake |

## Monitoring Power Consumption

To accurately measure power consumption:

1. Use a precision current meter (e.g., Joulescope, Nordic Power Profiler)
2. Disconnect all unnecessary peripherals
3. Use a clean power supply
4. Measure over multiple sleep/wake cycles
5. Account for external components (LEDs, regulators, etc.)

## Configuration

### Adjusting Sleep Duration

Edit `SLEEP_DURATION_US` in `main/main.c`:
```c
#define SLEEP_DURATION_US (5 * 1000000ULL)  // 5 seconds
```

### Changing LED GPIO

Edit `LED_GPIO` in `main/main.c`:
```c
#define LED_GPIO GPIO_NUM_2  // Change to your board's LED pin
```

### Adjusting Number of Cycles

Edit `max_cycles` in `app_main()`:
```c
const int max_cycles = 10;  // Change to desired number
```

## Troubleshooting

### Issue: System doesn't wake up
- Check that wake-up source is properly configured
- Verify timer duration is not too long
- Check serial monitor for error messages

### Issue: High power consumption
- Disable unnecessary peripherals
- Check for external components drawing power
- Verify WiFi/Bluetooth are disabled during sleep
- Use `idf.py menuconfig` to optimize power settings

### Issue: LED not working
- Verify GPIO pin number matches your board
- Check if LED requires external pull-up/down resistor
- Some boards have built-in LEDs on specific pins

## References

- [ESP-IDF Power Management](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/sleep_modes.html)
- [ESP32 Light Sleep Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/sleep_modes.html#light-sleep)
- [ESP-IDF API Reference](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/index.html)

## License

This project is provided as-is for testing and educational purposes.
