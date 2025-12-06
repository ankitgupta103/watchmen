/**
 * @file sx1262.c
 * @brief SX126x LoRa Module Driver Implementation for ESP32
 */

#include "sx1262.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

static const char *TAG = "SX1262";

// ============================================================================
// Internal Helper Functions
// ============================================================================

/**
 * @brief Set module mode via M0/M1 pins
 * 
 * Modes:
 *   - Normal: M0=LOW, M1=LOW
 *   - Wake-up: M0=HIGH, M1=LOW
 *   - Power Save: M0=LOW, M1=HIGH
 *   - Configuration: M0=HIGH, M1=HIGH
 */
static void sx1262_set_mode(gpio_num_t m0_pin, gpio_num_t m1_pin, bool m0, bool m1)
{
    gpio_set_level(m0_pin, m0 ? 1 : 0);
    gpio_set_level(m1_pin, m1 ? 1 : 0);
    vTaskDelay(pdMS_TO_TICKS(SX1262_MODE_SWITCH_DELAY_MS));
}

/**
 * @brief Enter configuration mode
 */
static void sx1262_enter_config_mode(gpio_num_t m0_pin, gpio_num_t m1_pin)
{
    sx1262_set_mode(m0_pin, m1_pin, true, true);  // M0=HIGH, M1=HIGH
}

/**
 * @brief Exit to normal operation mode
 */
static void sx1262_exit_config_mode(gpio_num_t m0_pin, gpio_num_t m1_pin)
{
    sx1262_set_mode(m0_pin, m1_pin, false, false);  // M0=LOW, M1=LOW
}

/**
 * @brief Get UART baud rate register value
 */
static uint8_t sx1262_get_uart_baud_reg(uint32_t baud)
{
    switch (baud) {
        case 1200:  return 0x00;
        case 2400:  return 0x20;
        case 4800:  return 0x40;
        case 9600:  return 0x60;
        case 19200: return 0x80;
        case 38400: return 0xA0;
        case 57600: return 0xC0;
        case 115200: return 0xE0;
        default: return 0x60;  // Default to 9600
    }
}

/**
 * @brief Get air data rate register value
 */
static uint8_t sx1262_get_air_speed_reg(uint16_t air_speed)
{
    switch (air_speed) {
        case 1200:  return 0x01;
        case 2400:  return 0x02;
        case 4800:  return 0x03;
        case 9600:  return 0x04;
        case 19200: return 0x05;
        case 38400: return 0x06;
        case 62500: return 0x07;
        default: return 0x02;  // Default to 2400
    }
}

/**
 * @brief Get buffer size register value
 */
static uint8_t sx1262_get_buffer_size_reg(uint8_t buffer_size)
{
    switch (buffer_size) {
        case 240: return 0x00;
        case 128: return 0x40;
        case 64:  return 0x80;
        case 32:  return 0xC0;
        default: return 0x00;  // Default to 240
    }
}

/**
 * @brief Get TX power register value
 */
static uint8_t sx1262_get_power_reg(uint8_t power)
{
    switch (power) {
        case 22: return 0x00;
        case 17: return 0x01;
        case 13: return 0x02;
        case 10: return 0x03;
        default: return 0x00;  // Default to 22 dBm
    }
}

/**
 * @brief Build configuration register array (12 bytes)
 */
static void sx1262_build_config_reg(const sx1262_config_t *config, uint8_t *cfg_reg)
{
    // Calculate frequency offset
    uint16_t freq_offset;
    
    if (config->freq >= SX1262_FREQ_900MHZ_START) {
        freq_offset = config->freq - SX1262_FREQ_900MHZ_START;
    } else if (config->freq >= SX1262_FREQ_400MHZ_START) {
        freq_offset = config->freq - SX1262_FREQ_400MHZ_START;
    } else {
        freq_offset = 0;
    }
    
    // Build configuration register
    cfg_reg[0] = config->persistent_config ? SX1262_CFG_HEADER_PERSISTENT : SX1262_CFG_HEADER_VOLATILE;
    cfg_reg[1] = 0x00;  // Length high byte
    cfg_reg[2] = 0x09;  // Length low byte (9 parameters)
    cfg_reg[3] = (config->addr >> 8) & 0xFF;  // Address high byte
    cfg_reg[4] = config->addr & 0xFF;         // Address low byte
    cfg_reg[5] = config->net_id & 0xFF;       // Network ID
    cfg_reg[6] = sx1262_get_uart_baud_reg(SX1262_UART_NORMAL_BAUD) | sx1262_get_air_speed_reg(config->air_speed);
    cfg_reg[7] = sx1262_get_buffer_size_reg(config->buffer_size) | sx1262_get_power_reg(config->power) | 0x20;  // 0x20 enables noise RSSI
    cfg_reg[8] = freq_offset & 0xFF;          // Frequency offset
    cfg_reg[9] = 0x43 | (config->rssi_enabled ? 0x80 : 0x00);  // Fixed point mode (0x43) + RSSI enable (0x80)
    cfg_reg[10] = (config->crypt_key >> 8) & 0xFF;  // Encryption key high byte
    cfg_reg[11] = config->crypt_key & 0xFF;         // Encryption key low byte
}

/**
 * @brief Send configuration to module and verify
 */
static esp_err_t sx1262_send_config(uart_port_t uart_num, gpio_num_t m0_pin, gpio_num_t m1_pin, const uint8_t *cfg_reg)
{
    uint8_t response[12];
    int len;
    
    // Clear UART buffer
    uart_flush(uart_num);
    
    // Send configuration (12 bytes)
    int written = uart_write_bytes(uart_num, cfg_reg, 12);
    if (written != 12) {
        ESP_LOGE(TAG, "Failed to write configuration");
        return ESP_FAIL;
    }
    
    vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_WRITE_DELAY_MS));
    
    // Wait for response
    vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_RESPONSE_WAIT_MS));
    
    len = uart_read_bytes(uart_num, response, sizeof(response), pdMS_TO_TICKS(SX1262_CFG_RESPONSE_WAIT_MS));
    
    if (len > 0 && response[0] == SX1262_RESPONSE_SUCCESS) {
        ESP_LOGI(TAG, "Configuration successful");
        return ESP_OK;
    } else {
        ESP_LOGW(TAG, "Configuration failed or no response");
        return ESP_FAIL;
    }
}

// ============================================================================
// Public API Implementation
// ============================================================================

esp_err_t sx1262_init(const sx1262_config_t *config, sx1262_handle_t *handle)
{
    if (config == NULL || handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    // Validate frequency range
    if ((config->freq < SX1262_FREQ_400MHZ_START || config->freq > SX1262_FREQ_400MHZ_END) &&
        (config->freq < SX1262_FREQ_900MHZ_START || config->freq > SX1262_FREQ_900MHZ_END)) {
        ESP_LOGE(TAG, "Invalid frequency: %d MHz", config->freq);
        return ESP_ERR_INVALID_ARG;
    }
    
    // Initialize GPIO pins
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << config->m0_pin) | (1ULL << config->m1_pin),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    
    ESP_LOGI(TAG, "Initializing SX1262 module...");
    ESP_LOGI(TAG, "  UART: %d, M0: GPIO%d, M1: GPIO%d", config->uart_num, config->m0_pin, config->m1_pin);
    ESP_LOGI(TAG, "  Address: %d, Frequency: %d MHz, Power: %d dBm", 
             config->addr, config->freq, config->power);
    
    // Enter configuration mode
    sx1262_enter_config_mode(config->m0_pin, config->m1_pin);
    
    // Configure UART at 9600 baud for initial configuration
    uart_config_t uart_config = {
        .baud_rate = SX1262_UART_CONFIG_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    
    ESP_ERROR_CHECK(uart_driver_install(config->uart_num, SX1262_UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(config->uart_num, &uart_config));
    
    // Set UART pins (adjust these based on your ESP32 board)
    // Default: TX=GPIO17, RX=GPIO16 for UART_NUM_1
    ESP_ERROR_CHECK(uart_set_pin(config->uart_num, GPIO_NUM_17, GPIO_NUM_16, 
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    vTaskDelay(pdMS_TO_TICKS(SX1262_UART_INIT_DELAY_MS));
    
    // Build and send configuration
    uint8_t cfg_reg[12];
    sx1262_build_config_reg(config, cfg_reg);
    
    // Retry configuration up to 3 times
    esp_err_t ret = ESP_FAIL;
    for (int i = 0; i < SX1262_CFG_RETRY_ATTEMPTS; i++) {
        ESP_LOGI(TAG, "Configuration attempt %d/%d", i + 1, SX1262_CFG_RETRY_ATTEMPTS);
        ret = sx1262_send_config(config->uart_num, config->m0_pin, config->m1_pin, cfg_reg);
        if (ret == ESP_OK) {
            break;
        }
        vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_RETRY_DELAY_MS));
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure module after %d attempts", SX1262_CFG_RETRY_ATTEMPTS);
        uart_driver_delete(config->uart_num);
        return ESP_FAIL;
    }
    
    // Reconfigure UART at target baud rate (115200)
    uart_driver_delete(config->uart_num);
    vTaskDelay(pdMS_TO_TICKS(300));
    
    // Re-enter config mode for baud rate change
    sx1262_enter_config_mode(config->m0_pin, config->m1_pin);
    vTaskDelay(pdMS_TO_TICKS(SX1262_UART_INIT_DELAY_MS));
    
    uart_config.baud_rate = SX1262_UART_NORMAL_BAUD;
    ESP_ERROR_CHECK(uart_driver_install(config->uart_num, SX1262_UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(config->uart_num, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(config->uart_num, GPIO_NUM_17, GPIO_NUM_16, 
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    uart_flush(config->uart_num);
    vTaskDelay(pdMS_TO_TICKS(30));
    
    // Exit to normal operation mode
    sx1262_exit_config_mode(config->m0_pin, config->m1_pin);
    
    // Calculate frequency offset for handle
    uint16_t start_freq;
    if (config->freq >= SX1262_FREQ_900MHZ_START) {
        start_freq = SX1262_FREQ_900MHZ_START;
    } else {
        start_freq = SX1262_FREQ_400MHZ_START;
    }
    
    // Store handle
    handle->uart_num = config->uart_num;
    handle->m0_pin = config->m0_pin;
    handle->m1_pin = config->m1_pin;
    handle->addr = config->addr;
    handle->freq = config->freq;
    handle->offset_freq = config->freq - start_freq;
    handle->start_freq = start_freq;
    handle->is_configured = true;
    handle->rssi_enabled = config->rssi_enabled;
    
    ESP_LOGI(TAG, "SX1262 module initialized successfully");
    return ESP_OK;
}

esp_err_t sx1262_send(sx1262_handle_t *handle, uint16_t target_addr, const uint8_t *data, size_t len)
{
    if (handle == NULL || data == NULL || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (!handle->is_configured) {
        ESP_LOGE(TAG, "Module not configured");
        return ESP_ERR_INVALID_STATE;
    }
    
    // Ensure normal mode
    sx1262_exit_config_mode(handle->m0_pin, handle->m1_pin);
    
    // Build message packet
    // Format: [target_high][target_low][target_freq][own_high][own_low][own_freq][payload][\n]
    uint8_t packet[256];  // Max packet size
    size_t packet_len = 0;
    
    if (len > 240) {  // Max payload size
        len = 240;
    }
    
    packet[packet_len++] = (target_addr >> 8) & 0xFF;  // Target address high
    packet[packet_len++] = target_addr & 0xFF;        // Target address low
    packet[packet_len++] = handle->offset_freq;        // Target frequency offset
    packet[packet_len++] = (handle->addr >> 8) & 0xFF; // Own address high
    packet[packet_len++] = handle->addr & 0xFF;        // Own address low
    packet[packet_len++] = handle->offset_freq;       // Own frequency offset
    
    // Copy payload
    memcpy(&packet[packet_len], data, len);
    packet_len += len;
    
    // Add newline
    packet[packet_len++] = '\n';
    
    // Send packet
    int written = uart_write_bytes(handle->uart_num, packet, packet_len);
    if (written != packet_len) {
        ESP_LOGE(TAG, "Failed to send data");
        return ESP_FAIL;
    }
    
    vTaskDelay(pdMS_TO_TICKS(SX1262_TX_DELAY_MS));
    
    ESP_LOGD(TAG, "Sent %d bytes to address %d", len, target_addr);
    return ESP_OK;
}

esp_err_t sx1262_receive(sx1262_handle_t *handle, uint8_t *buffer, size_t buffer_size, 
                         size_t *received_len, int8_t *rssi)
{
    if (handle == NULL || buffer == NULL || received_len == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (!handle->is_configured) {
        return ESP_ERR_INVALID_STATE;
    }
    
    // Ensure normal mode
    sx1262_exit_config_mode(handle->m0_pin, handle->m1_pin);
    
    // Check if data is available
    size_t available = 0;
    uart_get_buffered_data_len(handle->uart_num, &available);
    
    if (available == 0) {
        return ESP_ERR_NOT_FOUND;
    }
    
    // Wait a bit for complete message to arrive
    vTaskDelay(pdMS_TO_TICKS(SX1262_RX_DELAY_MS));
    
    // Recheck available data after delay
    uart_get_buffered_data_len(handle->uart_num, &available);
    if (available == 0) {
        return ESP_ERR_NOT_FOUND;
    }
    
    // Read data (try to read a line ending with \n)
    uint8_t temp_buffer[256];
    int len = uart_read_bytes(handle->uart_num, temp_buffer, sizeof(temp_buffer) - 1, 
                              pdMS_TO_TICKS(200));  // Increased timeout for longer messages
    
    if (len <= 0) {
        return ESP_ERR_NOT_FOUND;
    }
    
    // Find newline
    int newline_pos = -1;
    for (int i = 0; i < len; i++) {
        if (temp_buffer[i] == '\n') {
            newline_pos = i;
            break;
        }
    }
    
    if (newline_pos < 0) {
        // No newline found, might be incomplete message
        return ESP_ERR_NOT_FOUND;
    }
    
    // Minimum message: 3 bytes header (addr_h, addr_l, freq) + 1 byte payload
    if (newline_pos < 4) {
        return ESP_ERR_INVALID_SIZE;
    }
    
    // Extract RSSI if enabled
    int payload_start = 3;  // Skip addr_h, addr_l, freq
    int payload_end = newline_pos;
    
    if (handle->rssi_enabled && newline_pos >= 5) {
        // Last byte before newline is RSSI
        if (rssi != NULL) {
            *rssi = -(256 - temp_buffer[newline_pos - 1]);
        }
        payload_end = newline_pos - 1;  // Exclude RSSI byte
    } else if (rssi != NULL) {
        *rssi = 0;
    }
    
    // Extract payload (skip header: addr_h, addr_l, freq)
    size_t payload_len = payload_end - payload_start;
    
    if (payload_len > buffer_size) {
        ESP_LOGW(TAG, "Buffer too small: need %d, have %d", payload_len, buffer_size);
        return ESP_ERR_INVALID_SIZE;
    }
    
    memcpy(buffer, &temp_buffer[payload_start], payload_len);
    *received_len = payload_len;
    
    ESP_LOGD(TAG, "Received %d bytes", payload_len);
    return ESP_OK;
}

esp_err_t sx1262_get_channel_rssi(sx1262_handle_t *handle, int8_t *rssi)
{
    if (handle == NULL || rssi == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (!handle->is_configured) {
        return ESP_ERR_INVALID_STATE;
    }
    
    // Ensure normal mode
    sx1262_exit_config_mode(handle->m0_pin, handle->m1_pin);
    
    // Clear buffer
    uart_flush(handle->uart_num);
    
    // Send RSSI command: 0xC0 0xC1 0xC2 0xC3 0x00 0x02
    uint8_t rssi_cmd[] = {0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02};
    uart_write_bytes(handle->uart_num, rssi_cmd, sizeof(rssi_cmd));
    
    vTaskDelay(pdMS_TO_TICKS(SX1262_RSSI_WAIT_MS));
    
    // Read response: 0xC1 0x00 0x02 [RSSI_value]
    uint8_t response[4];
    int len = uart_read_bytes(handle->uart_num, response, sizeof(response), 
                               pdMS_TO_TICKS(SX1262_CFG_RESPONSE_WAIT_MS));
    
    if (len >= 4 && response[0] == 0xC1 && response[1] == 0x00 && response[2] == 0x02) {
        *rssi = -(256 - response[3]);
        ESP_LOGI(TAG, "Channel RSSI: %d dBm", *rssi);
        return ESP_OK;
    }
    
    ESP_LOGW(TAG, "Failed to read RSSI");
    return ESP_FAIL;
}

esp_err_t sx1262_deinit(sx1262_handle_t *handle)
{
    if (handle == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    uart_driver_delete(handle->uart_num);
    handle->is_configured = false;
    
    ESP_LOGI(TAG, "SX1262 driver deinitialized");
    return ESP_OK;
}

