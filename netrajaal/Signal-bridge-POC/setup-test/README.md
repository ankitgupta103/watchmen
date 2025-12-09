# ESP-IDF SX1262 LoRa HAT Project

This project demonstrates how to use the Waveshare SX1262 868M LoRa HAT with ESP32 using ESP-IDF framework.

## Hardware Connections

- **UART TX**: GPIO 16
- **UART RX**: GPIO 17
- **M0 Pin**: GPIO 21
- **M1 Pin**: GPIO 22
- **Baud Rate**: 9600

## Project Structure

```
├── CMakeLists.txt              Main CMake configuration
├── main/
│   ├── CMakeLists.txt          Component CMake configuration
│   ├── main.c                  Main application code
│   ├── sx126x_lora_hat.h       SX1262 driver header
│   └── sx126x_lora_hat.c       SX1262 driver implementation
└── README.md                   This file
```

## Features

The driver supports three operation modes:

1. **Transparent Mode** (Default): Broadcast mode for point-to-point or broadcast communication
2. **Relay Mode**: Multi-hop relay communication
3. **WOR Mode**: Wake-on-Radio mode for low power applications

## Usage

1. Build the project:
   ```bash
   idf.py build
   ```

2. Flash to ESP32:
   ```bash
   idf.py flash
   ```

3. Monitor output:
   ```bash
   idf.py monitor
   ```

## Configuration

To change the operation mode, edit `main/main.c` and uncomment the desired mode:

```c
#define TRANSPARENT_MODE_ENABLED
// #define RELAY_MODE_ENABLED
// #define WOR_MODE_ENABLED
```

## How It Works

1. **Initialization**: The module initializes UART and GPIO pins
2. **Configuration**: Sets M0/M1 pins to enter configuration mode and writes register values
3. **Normal Operation**: Switches to normal mode and starts sending/receiving data
4. **Main Loop**: 
   - Continuously checks for received messages
   - Sends a test message every 5 seconds

## Code Overview

- `sx126x_init()`: Initializes UART and GPIO
- `cfg_sx126x_io()`: Sets M0/M1 pins for different modes
- `cfg_sx126x_mode()`: Configures the module for a specific mode
- `sx126x_write_register()`: Writes configuration to the module
- `sx126x_send()`: Sends data via LoRa
- `sx126x_receive()`: Receives data from LoRa

## Reference

Based on the STM32 implementation in the `stm32/` directory and adapted for ESP-IDF.
