/**
 * @file sx1262.h
 * @brief SX126x LoRa Module Driver for ESP32
 * 
 * This driver provides a simple interface to configure and communicate with
 * SX126x-based LoRa modules (E22/E32 series) using ESP-IDF.
 * 
 * Hardware Requirements:
 *   - ESP32 board
 *   - SX1262 LoRa module (E22/E32)
 *   - UART connection (default: UART_NUM_1)
 *   - GPIO pins for M0 and M1 mode control
 * 
 * Features:
 *   - Simple configuration API
 *   - Send and receive data
 *   - RSSI measurement
 *   - Address-based routing
 * 
 * @author Watchmen Project
 */

#ifndef SX1262_H
#define SX1262_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================================
// Configuration Constants
// ============================================================================

// Configuration headers
#define SX1262_CFG_HEADER_PERSISTENT  0xC0  // Settings persist after power-off
#define SX1262_CFG_HEADER_VOLATILE   0xC2  // Settings lost after power-off (default)

// Response headers
#define SX1262_RESPONSE_SUCCESS      0xC1
#define SX1262_RESPONSE_FAILURE      0xC0

// Frequency ranges (MHz)
#define SX1262_FREQ_400MHZ_START    410
#define SX1262_FREQ_400MHZ_END      493
#define SX1262_FREQ_900MHZ_START    850
#define SX1262_FREQ_900MHZ_END      930

// Timing constants (milliseconds) - Matched to working STM32 driver
#define SX1262_MODE_SWITCH_DELAY_MS     5    // Delay when switching M0/M1 modes (STM32: HAL_Delay(5))
#define SX1262_UART_INIT_DELAY_MS       1000 // Delay after UART init before config (STM32: HAL_Delay(1000))
#define SX1262_CFG_WRITE_DELAY_MS       500  // Delay after config write (STM32: HAL_Delay(500))
#define SX1262_CFG_RESPONSE_WAIT_MS     200   // Delay if data available (Python: CFG_RESPONSE_WAIT_MS)
#define SX1262_CFG_RETRY_DELAY_MS       500   // Delay between retries (Python: CFG_RETRY_DELAY_MS)
#define SX1262_TX_DELAY_MS              150
#define SX1262_RX_DELAY_MS              250
#define SX1262_RSSI_WAIT_MS             500

// Configuration retry attempts
#define SX1262_CFG_RETRY_ATTEMPTS       3

// UART settings
#define SX1262_UART_CONFIG_BAUD         9600   // Initial baud for configuration
#define SX1262_UART_NORMAL_BAUD        115200  // Target baud for operation
#define SX1262_UART_BUF_SIZE           1024
#define SX1262_UART_TIMEOUT_MS          2000

// ============================================================================
// Configuration Structure
// ============================================================================

/**
 * @brief SX1262 module configuration parameters
 */
typedef struct {
    uart_port_t uart_num;      // UART port number (e.g., UART_NUM_1)
    gpio_num_t m0_pin;         // GPIO pin for M0 mode control
    gpio_num_t m1_pin;         // GPIO pin for M1 mode control
    uint16_t addr;             // Node address (0-65535)
    uint16_t freq;             // Operating frequency in MHz (410-493 or 850-930)
    uint8_t power;             // TX power: 10, 13, 17, or 22 dBm
    uint16_t air_speed;        // Air data rate: 1200, 2400, 4800, 9600, 19200, 38400, 62500 bps
    uint8_t net_id;            // Network ID (0-255)
    uint8_t buffer_size;       // Buffer size: 32, 64, 128, or 240 bytes
    uint16_t crypt_key;        // Encryption key (0-65535, 0 = disabled)
    bool rssi_enabled;         // Enable RSSI reporting in received packets
    bool persistent_config;    // Save config to EEPROM (true) or RAM only (false)
} sx1262_config_t;

/**
 * @brief SX1262 driver handle
 */
typedef struct {
    uart_port_t uart_num;
    gpio_num_t m0_pin;
    gpio_num_t m1_pin;
    uint16_t addr;
    uint16_t freq;
    uint16_t offset_freq;
    uint16_t start_freq;
    bool is_configured;
    bool rssi_enabled;
} sx1262_handle_t;

// ============================================================================
// Public API Functions
// ============================================================================

/**
 * @brief Initialize SX1262 LoRa module
 * 
 * This function:
 * 1. Initializes GPIO pins (M0, M1)
 * 2. Enters configuration mode
 * 3. Configures UART at 9600 baud
 * 4. Sends configuration to module
 * 5. Switches to target baud rate (115200)
 * 6. Returns to normal operation mode
 * 
 * @param config Configuration parameters
 * @param handle Pointer to store driver handle
 * @return 
 *   - ESP_OK: Success
 *   - ESP_ERR_INVALID_ARG: Invalid configuration
 *   - ESP_FAIL: Configuration failed
 */
esp_err_t sx1262_init(const sx1262_config_t *config, sx1262_handle_t *handle);

/**
 * @brief Send data to a target address
 * 
 * Message format: [target_addr_h][target_addr_l][target_freq][own_addr_h][own_addr_l][own_freq][payload][\n]
 * 
 * @param handle Driver handle
 * @param target_addr Destination address (0-65535, 65535 = broadcast)
 * @param data Data to send
 * @param len Data length
 * @return 
 *   - ESP_OK: Success
 *   - ESP_ERR_INVALID_ARG: Invalid parameters
 *   - ESP_FAIL: Send failed
 */
esp_err_t sx1262_send(sx1262_handle_t *handle, uint16_t target_addr, const uint8_t *data, size_t len);

/**
 * @brief Receive data from the module
 * 
 * @param handle Driver handle
 * @param buffer Buffer to store received data
 * @param buffer_size Size of buffer
 * @param received_len Pointer to store actual received length
 * @param rssi Pointer to store RSSI value (dBm), NULL if not needed
 * @return 
 *   - ESP_OK: Data received
 *   - ESP_ERR_NOT_FOUND: No data available
 *   - ESP_ERR_INVALID_SIZE: Buffer too small
 */
esp_err_t sx1262_receive(sx1262_handle_t *handle, uint8_t *buffer, size_t buffer_size, 
                         size_t *received_len, int8_t *rssi);

/**
 * @brief Read channel RSSI (background noise level)
 * 
 * @param handle Driver handle
 * @param rssi Pointer to store RSSI value (dBm)
 * @return 
 *   - ESP_OK: Success
 *   - ESP_FAIL: Failed to read RSSI
 */
esp_err_t sx1262_get_channel_rssi(sx1262_handle_t *handle, int8_t *rssi);

/**
 * @brief Deinitialize SX1262 driver
 * 
 * @param handle Driver handle
 * @return ESP_OK
 */
esp_err_t sx1262_deinit(sx1262_handle_t *handle);

#ifdef __cplusplus
}
#endif

#endif // SX1262_H

