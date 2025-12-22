# BridgeX-ESP - Sensor Wake Application

ESP32 application that monitors a sensor on GPIO12 (D12) and wakes from light sleep mode when the sensor sends a HIGH signal.

## Features

- **Light Sleep Mode**: ESP32 enters light sleep to minimize power consumption
- **GPIO Wakeup**: Wakes automatically when GPIO12 goes HIGH
- **LED Indication**: Built-in LED (GPIO2) provides visual feedback
- **5-Second Active Period**: Stays awake for 5 seconds after wakeup
- **Smart Sleep Logic**: Waits for signal to go LOW before sleeping to prevent immediate re-wake

## Hardware Requirements

- ESP32 development board
- Sensor connected to GPIO12 (D12) - sends HIGH (1) or LOW (0) signal
- Common ground connection between ESP32 and sensor

## Pin Configuration

- **GPIO12 (D12)**: Sensor input (with internal pull-down resistor)
- **GPIO2**: LED output (built-in LED on most ESP32 boards)

## Power Consumption

### Light Sleep Mode

The ESP32 consumes approximately **0.8 mA** (800 µA) in light sleep mode.

**Note about Power LED**: The power LED on the ESP32 development board remains ON during light sleep mode. This is expected behavior because:

- The power LED is a board-level indicator powered directly from the 3.3V supply
- It is not controlled by the ESP32 GPIO and cannot be turned off by software
- The LED indicates that the board is receiving power, not the ESP32's operational state
- The actual ESP32 chip itself is in low-power light sleep mode, consuming minimal current

### Power States

| State | Current Consumption | Description |
|-------|---------------------|-------------|
| Light Sleep | ~0.8 mA | CPU paused, RAM retained, RTC active |
| Active (Awake) | ~80-240 mA | Full operation, depends on CPU frequency and peripherals |
| Deep Sleep | ~10-150 µA | Lowest power, RAM not retained |

### Power Optimization Notes

- Light sleep mode pauses the CPU and suspends most system clocks
- RAM contents are retained, allowing quick wakeup
- RTC timer remains active for wakeup timing
- GPIO wakeup capability is maintained
- Actual power consumption may vary based on:
  - Board design and components
  - External peripherals connected
  - Environmental conditions

## Application Flow

1. **Initialization**
   - Configure GPIO12 as input with pull-down
   - Configure GPIO2 (LED) as output
   - Wait for GPIO12 to be LOW before first sleep

2. **Light Sleep Mode**
   - Configure GPIO12 as wakeup source (triggers on HIGH)
   - Enter light sleep mode
   - LED is OFF during sleep
   - Power consumption: ~0.8 mA

3. **Wake Up** (when GPIO12 goes HIGH)
   - ESP32 wakes from light sleep
   - LED blinks 3 times fast (wake indication)
   - Stay awake for 5 seconds
   - Power consumption: ~80-240 mA (active mode)

4. **Prepare for Sleep**
   - After 5 seconds, LED blinks 3 times fast (sleep indication)
   - Wait for GPIO12 to go LOW
   - Return to light sleep mode

## LED Behavior

- **3 Fast Blinks**: When waking up from sleep (wake indication)
- **3 Fast Blinks**: Before entering sleep mode (sleep indication)
- **OFF**: During light sleep mode
- **ON**: During active period (5 seconds after wake)

## Building and Flashing

### Prerequisites

- ESP-IDF v5.1 or later
- Python 3.10+
- ESP32 development board

### Build

```bash
idf.py build
```

### Flash

```bash
idf.py -p <PORT> flash monitor
```

Replace `<PORT>` with your ESP32's serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows).

## Configuration

You can modify these constants in `main/main.c`:

```c
#define SENSOR_GPIO       GPIO_NUM_12  // Sensor input pin
#define LED_GPIO          GPIO_NUM_2   // LED output pin
#define WAKE_TIME_SEC     5            // Active time after wake (seconds)
#define BLINK_ON_MS       100          // LED ON time for blink (ms)
#define BLINK_OFF_MS      100          // LED OFF time for blink (ms)
#define BLINK_COUNT       3            // Number of blinks
```

## Code Structure

The code is organized with clear separation of concerns:

- **Configuration**: All defines at the top
- **GPIO Structures**: GPIO configuration structs defined outside functions
- **Helper Functions**: Modular functions for each operation
- **Main Flow**: `app_main()` contains only the high-level application flow

## Troubleshooting

### ESP32 Wakes Immediately

- Ensure GPIO12 is LOW before entering sleep
- Check for floating pins or external pull-up resistors
- Verify sensor connection and signal levels

### Power LED Always On

- This is normal - the power LED is board-level and cannot be controlled by software
- The ESP32 itself is in low-power mode despite the LED being on

### Sensor Not Detected

- Verify GPIO12 connection
- Check sensor signal levels (HIGH = 3.3V, LOW = 0V)
- Ensure common ground connection

## License

This project is provided as-is for demonstration purposes.
