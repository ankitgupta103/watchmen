# SX1262 LoRa Driver for ESP32

A simple, easy-to-understand driver for SX126x-based LoRa modules (E22/E32 series) on ESP32.

## Features

- ✅ Simple API - Easy to use and understand
- ✅ Configuration management - Set frequency, power, address, etc.
- ✅ Send/Receive data - Full duplex communication
- ✅ RSSI support - Signal strength measurement
- ✅ Address-based routing - Mesh network support
- ✅ Well documented - Clear code comments

## Hardware Setup

### Required Connections

```
ESP32          SX1262 Module
------         -------------
GPIO17  -----> TX (UART TX)
GPIO16  <----- RX (UART RX)
GPIO4   -----> M0 (Mode control)
GPIO5   -----> M1 (Mode control)
GND     -----> GND
3.3V    -----> VCC
```

**Note:** Adjust GPIO pins in your code based on your board configuration.

## Quick Start

### 1. Include the Driver

```c
#include "sx1262.h"
```

### 2. Configure the Module

```c
sx1262_config_t config = {
    .uart_num = UART_NUM_1,        // UART port
    .m0_pin = GPIO_NUM_4,          // M0 GPIO pin
    .m1_pin = GPIO_NUM_5,          // M1 GPIO pin
    .addr = 0x0001,                // Node address (0-65535)
    .freq = 868,                   // Frequency: 410-493 or 850-930 MHz
    .power = 22,                   // TX power: 10, 13, 17, or 22 dBm
    .air_speed = 2400,             // Air data rate: 1200-62500 bps
    .net_id = 0,                   // Network ID (0-255)
    .buffer_size = 240,            // Buffer: 32, 64, 128, or 240 bytes
    .crypt_key = 0,                // Encryption key (0 = disabled)
    .rssi_enabled = true,          // Enable RSSI in received packets
    .persistent_config = false     // false = RAM only, true = EEPROM
};
```

### 3. Initialize

```c
sx1262_handle_t lora_handle;
esp_err_t ret = sx1262_init(&config, &lora_handle);
if (ret != ESP_OK) {
    ESP_LOGE(TAG, "Initialization failed!");
    return;
}
```

### 4. Send Data

```c
const char *message = "Hello, LoRa!";
esp_err_t ret = sx1262_send(&lora_handle, 0xFFFF, (uint8_t *)message, strlen(message));
// 0xFFFF = broadcast address (all nodes receive)
```

### 5. Receive Data

```c
uint8_t rx_buffer[256];
size_t received_len;
int8_t rssi;

esp_err_t ret = sx1262_receive(&lora_handle, rx_buffer, sizeof(rx_buffer), 
                                &received_len, &rssi);
if (ret == ESP_OK) {
    rx_buffer[received_len] = '\0';  // Null terminate
    ESP_LOGI(TAG, "Received: %s (RSSI: %d dBm)", rx_buffer, rssi);
}
```

### 6. Read Channel RSSI

```c
int8_t rssi;
if (sx1262_get_channel_rssi(&lora_handle, &rssi) == ESP_OK) {
    ESP_LOGI(TAG, "Channel RSSI: %d dBm", rssi);
}
```

## Complete Example

See `main/sx1262_example.c` for a complete working example.

## API Reference

### `sx1262_init()`

Initialize and configure the SX1262 module.

```c
esp_err_t sx1262_init(const sx1262_config_t *config, sx1262_handle_t *handle);
```

**Parameters:**
- `config`: Configuration parameters
- `handle`: Pointer to store driver handle

**Returns:**
- `ESP_OK`: Success
- `ESP_ERR_INVALID_ARG`: Invalid configuration
- `ESP_FAIL`: Configuration failed

---

### `sx1262_send()`

Send data to a target address.

```c
esp_err_t sx1262_send(sx1262_handle_t *handle, uint16_t target_addr, 
                      const uint8_t *data, size_t len);
```

**Parameters:**
- `handle`: Driver handle
- `target_addr`: Destination address (0-65535, 65535 = broadcast)
- `data`: Data to send
- `len`: Data length (max 240 bytes)

**Returns:**
- `ESP_OK`: Success
- `ESP_ERR_INVALID_ARG`: Invalid parameters
- `ESP_FAIL`: Send failed

---

### `sx1262_receive()`

Receive data from the module.

```c
esp_err_t sx1262_receive(sx1262_handle_t *handle, uint8_t *buffer, 
                        size_t buffer_size, size_t *received_len, int8_t *rssi);
```

**Parameters:**
- `handle`: Driver handle
- `buffer`: Buffer to store received data
- `buffer_size`: Size of buffer
- `received_len`: Pointer to store actual received length
- `rssi`: Pointer to store RSSI value (dBm), NULL if not needed

**Returns:**
- `ESP_OK`: Data received
- `ESP_ERR_NOT_FOUND`: No data available
- `ESP_ERR_INVALID_SIZE`: Buffer too small

---

### `sx1262_get_channel_rssi()`

Read channel RSSI (background noise level).

```c
esp_err_t sx1262_get_channel_rssi(sx1262_handle_t *handle, int8_t *rssi);
```

**Parameters:**
- `handle`: Driver handle
- `rssi`: Pointer to store RSSI value (dBm)

**Returns:**
- `ESP_OK`: Success
- `ESP_FAIL`: Failed to read RSSI

---

### `sx1262_deinit()`

Deinitialize the driver.

```c
esp_err_t sx1262_deinit(sx1262_handle_t *handle);
```

## Configuration Parameters

### Frequency

- **400 MHz range:** 410-493 MHz (E22-400T22S)
- **900 MHz range:** 850-930 MHz (E22-900T22S)

### TX Power

- `10` dBm - Lowest power
- `13` dBm
- `17` dBm
- `22` dBm - Highest power (default)

### Air Data Rate

- `1200` bps - Longest range, slowest
- `2400` bps - Default
- `4800` bps
- `9600` bps
- `19200` bps
- `38400` bps
- `62500` bps - Shortest range, fastest

### Buffer Size

- `32` bytes - Smallest
- `64` bytes
- `128` bytes
- `240` bytes - Largest (default)

## Message Format

### Sent Message

```
[target_addr_h][target_addr_l][target_freq][own_addr_h][own_addr_l][own_freq][payload][\n]
```

### Received Message

**Without RSSI:**
```
[addr_h][addr_l][freq][payload][\n]
```

**With RSSI:**
```
[addr_h][addr_l][freq][payload][rssi_byte][\n]
```

## Troubleshooting

### Module Not Responding

1. **Check connections:**
   - Verify UART TX/RX are not swapped
   - Check M0/M1 pins are connected correctly
   - Ensure power supply is 3.3V and stable

2. **Check baud rate:**
   - Initial configuration uses 9600 baud
   - Normal operation uses 115200 baud

3. **Verify GPIO pins:**
   - Make sure M0 and M1 pins are correct
   - Check UART TX/RX pins match your board

### Configuration Fails

- Try increasing `SX1262_CFG_RETRY_DELAY_MS` in `sx1262.c`
- Check if module is in configuration mode (M0=HIGH, M1=HIGH)
- Verify UART communication at 9600 baud first

### No Data Received

- Check if sender and receiver are on same frequency
- Verify network ID matches (if using network filtering)
- Check if RSSI is enabled and module is in range
- Ensure module is in normal mode (M0=LOW, M1=LOW)

## Code Structure

```
main/
├── sx1262.h          # Driver header (public API)
├── sx1262.c          # Driver implementation
└── sx1262_example.c  # Usage example
```

## License

This driver is provided as-is for the Watchmen Project.

