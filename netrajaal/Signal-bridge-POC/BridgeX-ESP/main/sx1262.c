/**
 * @file sx1262.c
 * @brief SX126x LoRa Module Driver Implementation for ESP32
 */

#include "sx1262.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <inttypes.h>

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
 *   - Configuration: M0=LOW, M1=HIGH
 */
static void sx1262_set_mode(gpio_num_t m0_pin, gpio_num_t m1_pin, bool m0, bool m1)
{
    // Simple mode setting - match STM32 driver
    // STM32: M0_RESET()/M0_SET(), M1_RESET()/M1_SET(), HAL_Delay(5)
    gpio_set_level(m0_pin, m0 ? 1 : 0);
    gpio_set_level(m1_pin, m1 ? 1 : 0);
    
    // Wait for module to recognize mode change (match STM32: HAL_Delay(5))
    vTaskDelay(pdMS_TO_TICKS(SX1262_MODE_SWITCH_DELAY_MS));
    
    // Verify pins are actually at the expected levels
    int m0_level = gpio_get_level(m0_pin);
    int m1_level = gpio_get_level(m1_pin);
    int expected_m0 = m0 ? 1 : 0;
    int expected_m1 = m1 ? 1 : 0;
    
    ESP_LOGI(TAG, "GPIO pin verification:");
    ESP_LOGI(TAG, "  M0 (GPIO%d): Set to %d, Read back: %d %s", 
             m0_pin, expected_m0, m0_level, (m0_level == expected_m0) ? "✓" : "✗ MISMATCH!");
    ESP_LOGI(TAG, "  M1 (GPIO%d): Set to %d, Read back: %d %s", 
             m1_pin, expected_m1, m1_level, (m1_level == expected_m1) ? "✓" : "✗ MISMATCH!");
    
    if (m0_level != expected_m0 || m1_level != expected_m1) {
        ESP_LOGE(TAG, "⚠ WARNING: GPIO pins not at expected levels!");
        ESP_LOGE(TAG, "  This may indicate:");
        ESP_LOGE(TAG, "    - Pins not connected to module");
        ESP_LOGE(TAG, "    - Module pulling pins to different level");
        ESP_LOGE(TAG, "    - GPIO pin conflict with another peripheral");
    }
}

/**
 * @brief Enter configuration mode
 */
static void sx1262_enter_config_mode(gpio_num_t m0_pin, gpio_num_t m1_pin)
{
    sx1262_set_mode(m0_pin, m1_pin, false, true);  // M0=LOW, M1=HIGH
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
 * 
 * Matches Waveshare SX1262 868M LoRa HAT timing:
 * - Sends config twice (for i in range(2))
 * - Waits 200ms after write
 * - Waits 100ms if data available before reading
 */
static esp_err_t sx1262_send_config(uart_port_t uart_num, gpio_num_t m0_pin, gpio_num_t m1_pin, const uint8_t *cfg_reg)
{
    uint8_t response[12];
    int len = 0;
    size_t available = 0;
    
    // Clear input buffer (match Python: self.ser.flushInput())
    do {
        uart_get_buffered_data_len(uart_num, &available);
        if (available > 0) {
            uint8_t dummy[256];
            int read_len = uart_read_bytes(uart_num, dummy, 
                                          available > sizeof(dummy) ? sizeof(dummy) : available, 0);
            ESP_LOGI(TAG, "Cleared %d bytes from buffer", read_len);
        }
    } while (available > 0);
    
    // Debug: Print configuration bytes being sent
    ESP_LOGI(TAG, "Sending configuration (12 bytes):");
    char hex_str[50] = {0};
    for (int i = 0; i < 12; i++) {
        char temp[5];
        snprintf(temp, sizeof(temp), "%02X ", cfg_reg[i]);
        strncat(hex_str, temp, sizeof(hex_str) - strlen(hex_str) - 1);
    }
    ESP_LOGI(TAG, "  Bytes: %s", hex_str);
    ESP_LOGI(TAG, "  Header: 0x%02X (0xC2=volatile, 0xC0=persistent)", cfg_reg[0]);
    
    // Send configuration with retry logic (match Python: for attempt in range(CFG_RETRY_ATTEMPTS))
    for (int attempt = 0; attempt < SX1262_CFG_RETRY_ATTEMPTS; attempt++) {
        if (attempt > 0) {
            ESP_LOGI(TAG, "Configuration attempt %d/%d...", attempt + 1, SX1262_CFG_RETRY_ATTEMPTS);
        }
        
        // Send 12-byte configuration register (match Python: self.ser.write(bytes(self.cfg_reg)))
        ESP_LOGI(TAG, "Writing configuration bytes to UART...");
        int written = uart_write_bytes(uart_num, cfg_reg, 12);
        if (written != 12) {
            ESP_LOGE(TAG, "Failed to write all configuration bytes! Written: %d", written);
            continue;  // Try again
        }
        ESP_LOGI(TAG, "  ✓ Written %d bytes to UART", written);
        
        // Wait for module to process (match STM32: HAL_Delay(500))
        vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_WRITE_DELAY_MS));
        
        // Check for response (match STM32: check buffer[0] == CFG_RETURN after delay)
        uart_get_buffered_data_len(uart_num, &available);
        ESP_LOGI(TAG, "Checking for response... Available bytes: %d", available);
        
        if (available > 0) {
            // Read response (match STM32: HAL_UART_Receive_IT, then check buffer[0])
            len = uart_read_bytes(uart_num, response, sizeof(response), pdMS_TO_TICKS(100));
            ESP_LOGI(TAG, "Read %d bytes from module", len);
            
            if (len > 0 && response[0] == SX1262_RESPONSE_SUCCESS) {
                // Success! (match Waveshare: if r_buff[0] == 0xC1)
                ESP_LOGI(TAG, "Response received (%d bytes):", len);
                char resp_hex[50] = {0};
                for (int i = 0; i < len && i < 12; i++) {
                    char temp[5];
                    snprintf(temp, sizeof(temp), "%02X ", response[i]);
                    strncat(resp_hex, temp, sizeof(resp_hex) - strlen(resp_hex) - 1);
                }
                ESP_LOGI(TAG, "  Bytes: %s", resp_hex);
                ESP_LOGI(TAG, "✓ Configuration successful! Module confirmed with 0x%02X", response[0]);
                return ESP_OK;
            } else if (len > 0) {
                ESP_LOGW(TAG, "Unexpected response: 0x%02X (expected 0xC1)", len > 0 ? response[0] : 0);
            }
        } else {
            ESP_LOGW(TAG, "No data available in buffer");
        }
        
        // Clear input buffer before retry (match Python: while self.ser.any(): self.ser.read())
        do {
            uart_get_buffered_data_len(uart_num, &available);
            if (available > 0) {
                uint8_t dummy[256];
                uart_read_bytes(uart_num, dummy, 
                              available > sizeof(dummy) ? sizeof(dummy) : available, 0);
            }
        } while (available > 0);
        
        // Wait before retry (match Python: time.sleep_ms(CFG_RETRY_DELAY_MS))
        if (attempt < SX1262_CFG_RETRY_ATTEMPTS - 1) {
            vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_RETRY_DELAY_MS));
        }
    }
    
    // All attempts failed (match Python error message)
    ESP_LOGE(TAG, "✗ Configuration failed after %d attempts", SX1262_CFG_RETRY_ATTEMPTS);
    ESP_LOGE(TAG, "  Check:");
    ESP_LOGE(TAG, "    - M0/M1 pins are set correctly (M0=LOW, M1=HIGH for config mode)");
    ESP_LOGE(TAG, "    - UART TX/RX connections (GPIO17/GPIO16)");
    ESP_LOGE(TAG, "    - Module power supply (3.3V, stable)");
    ESP_LOGE(TAG, "    - Module is responding (may need power cycle)");
    return ESP_FAIL;
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
    
    ESP_LOGI(TAG, "Initializing SX1262 module...");
    ESP_LOGI(TAG, "  UART: %d, M0: GPIO%d, M1: GPIO%d", config->uart_num, config->m0_pin, config->m1_pin);
    ESP_LOGI(TAG, "  Address: %d, Frequency: %d MHz, Power: %d dBm", 
             config->addr, config->freq, config->power);
    
    // Initialize GPIO pins for mode control (M0, M1) - PUSH-PULL mode
    // Push-pull: ESP32 actively drives HIGH (1) or LOW (0)
    // IMPORTANT: External 4.7kΩ-10kΩ pull-up resistors are REQUIRED on M0/M1 to 3.3V
    // The LoRa module has internal pull-down resistors that prevent ESP32 from
    // driving pins HIGH reliably without external pull-ups.
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << config->m0_pin) | (1ULL << config->m1_pin),
        .mode = GPIO_MODE_OUTPUT,  // Push-pull mode - ESP32 drives both HIGH and LOW
        .pull_up_en = GPIO_PULLUP_DISABLE,  // Use external pull-ups (required)
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));
    
    // Set maximum drive strength (40mA) to help overcome module's pull-down
    // Note: Even with max drive, external pull-ups are still required
    // ESP32 drive capability: 0=weakest, 3=strongest (40mA)
    ESP_ERROR_CHECK(gpio_set_drive_capability(config->m0_pin, GPIO_DRIVE_CAP_3));
    ESP_ERROR_CHECK(gpio_set_drive_capability(config->m1_pin, GPIO_DRIVE_CAP_3));
    ESP_LOGI(TAG, "GPIO pins configured in PUSH-PULL mode with maximum drive strength (40mA)");
    ESP_LOGI(TAG, "  M0: GPIO%d, M1: GPIO%d", config->m0_pin, config->m1_pin);
    ESP_LOGI(TAG, "  ESP32 will actively drive pins HIGH or LOW");
    ESP_LOGI(TAG, "  ⚠ HARDWARE: External 4.7kΩ-10kΩ pull-ups required on M0/M1 to 3.3V");
    
    // Set pins HIGH initially - ESP32 actively drives HIGH
    gpio_set_level(config->m0_pin, 1);  // ESP32 actively drives HIGH
    gpio_set_level(config->m1_pin, 1);  // ESP32 actively drives HIGH
    
    // Verify pins can be set HIGH before proceeding
    vTaskDelay(pdMS_TO_TICKS(10));  // Small delay for pin to settle
    int m0_init = gpio_get_level(config->m0_pin);
    int m1_init = gpio_get_level(config->m1_pin);
    ESP_LOGI(TAG, "GPIO pins initialized: M0=GPIO%d (%s), M1=GPIO%d (%s)", 
             config->m0_pin, m0_init ? "HIGH✓" : "LOW✗", 
             config->m1_pin, m1_init ? "HIGH✓" : "LOW✗");
    
    if (!m0_init || !m1_init) {
        ESP_LOGE(TAG, "⚠ ERROR: ESP32 cannot drive pins HIGH!");
        ESP_LOGE(TAG, "  SOLUTION: Add external pull-up resistors:");
        ESP_LOGE(TAG, "    M0 (GPIO%d) → [4.7kΩ or 10kΩ] → 3.3V", config->m0_pin);
        ESP_LOGE(TAG, "    M1 (GPIO%d) → [4.7kΩ or 10kΩ] → 3.3V", config->m1_pin);
        ESP_LOGE(TAG, "  This is REQUIRED because the module has internal pull-downs");
        ESP_LOGE(TAG, "  Without external pull-ups, ESP32 cannot drive pins HIGH");
    }
    
    // Configure UART at 9600 baud for configuration (match STM32: 9600 baud)
    uart_config_t uart_config = {
        .baud_rate = SX1262_UART_CONFIG_BAUD,  // 9600 baud for config
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    
    ESP_ERROR_CHECK(uart_driver_install(config->uart_num, SX1262_UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(config->uart_num, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(config->uart_num, GPIO_NUM_17, GPIO_NUM_16, 
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    ESP_LOGI(TAG, "UART initialized at %d baud for configuration", SX1262_UART_CONFIG_BAUD);
    
    // STM32: HAL_Delay(1000); //dont delete wait for lora reset
    ESP_LOGI(TAG, "Waiting 1000ms for module to reset and stabilize (match STM32)...");
    vTaskDelay(pdMS_TO_TICKS(SX1262_UART_INIT_DELAY_MS));
    
    // Enter configuration mode: M0=LOW, M1=HIGH (match STM32: cfg_sx126x_io(CFG_REGISTER))
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "Entering configuration mode (M0=LOW, M1=HIGH)...");
    sx1262_enter_config_mode(config->m0_pin, config->m1_pin);
    ESP_LOGI(TAG, "");
    
    // Build configuration register (match Python driver)
    uint8_t cfg_reg[12];
    sx1262_build_config_reg(config, cfg_reg);
    
    // Retry configuration up to 3 times
    esp_err_t ret = ESP_FAIL;
    for (int i = 0; i < SX1262_CFG_RETRY_ATTEMPTS; i++) {
        ESP_LOGI(TAG, "");
        ESP_LOGI(TAG, "========================================");
        ESP_LOGI(TAG, "Configuration attempt %d/%d", i + 1, SX1262_CFG_RETRY_ATTEMPTS);
        ESP_LOGI(TAG, "========================================");
        
        // Re-enter config mode before each attempt (match Python: ensure config mode)
        if (i > 0) {
            ESP_LOGI(TAG, "Re-entering config mode before retry...");
            sx1262_enter_config_mode(config->m0_pin, config->m1_pin);
            vTaskDelay(pdMS_TO_TICKS(SX1262_MODE_SWITCH_DELAY_MS));
        }
        
        ret = sx1262_send_config(config->uart_num, config->m0_pin, config->m1_pin, cfg_reg);
        if (ret == ESP_OK) {
            ESP_LOGI(TAG, "✓ Configuration successful on attempt %d!", i + 1);
            break;
        } else {
            ESP_LOGW(TAG, "✗ Configuration attempt %d failed", i + 1);
            if (i < SX1262_CFG_RETRY_ATTEMPTS - 1) {
                ESP_LOGI(TAG, "Waiting %d ms before retry...", SX1262_CFG_RETRY_DELAY_MS);
                vTaskDelay(pdMS_TO_TICKS(SX1262_CFG_RETRY_DELAY_MS));
            }
        }
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure module after %d attempts", SX1262_CFG_RETRY_ATTEMPTS);
        uart_driver_delete(config->uart_num);
        return ESP_FAIL;
    }
    
    // Reopen UART at target baud rate (115200) - match Python driver exactly
    // Python: self.ser.deinit(), time.sleep_ms(300), then reopen at target_baud
    uart_driver_delete(config->uart_num);
    vTaskDelay(pdMS_TO_TICKS(300));  // Match Python: time.sleep_ms(300)
    
    // Critical: Module must be back in configuration mode for baud rate change
    // Python: self.M0.value(0), self.M1.value(1), time.sleep_ms(UART_INIT_DELAY_MS)
    sx1262_enter_config_mode(config->m0_pin, config->m1_pin);
    vTaskDelay(pdMS_TO_TICKS(SX1262_UART_INIT_DELAY_MS));
    
    // Reinitialize UART at target baud rate
    // Note: Keep the same pin configuration that worked during config
    uart_config.baud_rate = SX1262_UART_NORMAL_BAUD;
    ESP_ERROR_CHECK(uart_driver_install(config->uart_num, SX1262_UART_BUF_SIZE * 2, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(config->uart_num, &uart_config));
    // Use the same pin config that was tested (might be swapped)
    ESP_ERROR_CHECK(uart_set_pin(config->uart_num, GPIO_NUM_17, GPIO_NUM_16, 
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    // Clear any stale data from input buffer (match STM32: simple flush)
    size_t available = 0;
    uart_flush(config->uart_num);
    
    vTaskDelay(pdMS_TO_TICKS(30));  // Match Python: UART_STABILIZE_DELAY_MS = 30ms
    
    // Exit configuration mode: M0=LOW, M1=LOW (normal operation mode)
    // Python: self.M0.value(0), self.M1.value(0), time.sleep_ms(MODE_SWITCH_DELAY_MS)
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

