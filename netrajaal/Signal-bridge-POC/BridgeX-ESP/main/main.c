/**
 * @file main.c
 * @brief SX1262 Simple Mode and Configuration Test
 * 
 * Simple test that:
 * 1. Tests different M0/M1 mode combinations
 * 2. Verifies each mode
 * 3. Sends configuration in each mode
 * 4. Gets and displays response
 * 
 * FIXED: Uses open-drain mode to prevent back-voltage from module
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sx1262.h"
#include "driver/gpio.h"
#include "driver/uart.h"

static const char *TAG = "LORA_TEST";

// GPIO pin configuration for M0/M1 mode control
// RECOMMENDED: GPIO21/GPIO22 (avoid SPI conflicts with GPIO18/GPIO19)
// HARDWARE REQUIRED: Add external 4.7kΩ or 10kΩ pull-up resistors:
//   M0 (GPIO21) → [4.7kΩ] → 3.3V
//   M1 (GPIO22) → [4.7kΩ] → 3.3V
// This is required because the LoRa module has internal pull-down resistors
// that prevent ESP32 from driving pins HIGH without external pull-ups.
#define M0_PIN GPIO_NUM_21
#define M1_PIN GPIO_NUM_22

// Alternative pins (if GPIO21/22 are not available):
// #define M0_PIN GPIO_NUM_18
// #define M1_PIN GPIO_NUM_19

// Test GPIO pins without module (diagnostic)
void test_pins_without_module(gpio_num_t m0, gpio_num_t m1)
{
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  GPIO Pin Test (WITHOUT Module)");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  Disconnect M0/M1 from module for this test");
    ESP_LOGI(TAG, "  This verifies ESP32 can drive pins correctly");
    ESP_LOGI(TAG, "");
    
    // Configure as output
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << m0) | (1ULL << m1),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    gpio_set_drive_capability(m0, GPIO_DRIVE_CAP_3);
    gpio_set_drive_capability(m1, GPIO_DRIVE_CAP_3);
    
    // Test HIGH
    ESP_LOGI(TAG, "Testing HIGH state...");
    gpio_set_level(m0, 1);
    gpio_set_level(m1, 1);
    vTaskDelay(pdMS_TO_TICKS(100));
    int m0_high = gpio_get_level(m0);
    int m1_high = gpio_get_level(m1);
    ESP_LOGI(TAG, "  M0: %d (expected 1) %s", m0_high, (m0_high == 1) ? "✓" : "✗");
    ESP_LOGI(TAG, "  M1: %d (expected 1) %s", m1_high, (m1_high == 1) ? "✓" : "✗");
    
    // Test LOW
    ESP_LOGI(TAG, "Testing LOW state...");
    gpio_set_level(m0, 0);
    gpio_set_level(m1, 0);
    vTaskDelay(pdMS_TO_TICKS(100));
    int m0_low = gpio_get_level(m0);
    int m1_low = gpio_get_level(m1);
    ESP_LOGI(TAG, "  M0: %d (expected 0) %s", m0_low, (m0_low == 0) ? "✓" : "✗");
    ESP_LOGI(TAG, "  M1: %d (expected 0) %s", m1_low, (m1_low == 0) ? "✓" : "✗");
    
    if (m0_high == 1 && m1_high == 1 && m0_low == 0 && m1_low == 0) {
        ESP_LOGI(TAG, "");
        ESP_LOGI(TAG, "✓ ESP32 can drive pins correctly!");
        ESP_LOGI(TAG, "  Problem is module pulling pins LOW");
        ESP_LOGI(TAG, "  Solution: Use open-drain mode or add series resistors");
    } else {
        ESP_LOGE(TAG, "");
        ESP_LOGE(TAG, "✗ ESP32 cannot drive pins correctly!");
        ESP_LOGE(TAG, "  Check GPIO configuration or try different pins");
    }
    ESP_LOGI(TAG, "");
    vTaskDelay(pdMS_TO_TICKS(2000));
}

// Simple function to set mode and verify - ESP32 actively drives HIGH/LOW
void set_and_verify_mode(gpio_num_t m0, gpio_num_t m1, int m0_val, int m1_val, const char *mode_name)
{
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "=== Testing %s Mode (M0=%d, M1=%d) ===", mode_name, m0_val, m1_val);
    
    // Push-pull mode: ESP32 actively drives HIGH (1) or LOW (0)
    ESP_LOGI(TAG, "  Setting pins: M0=%d, M1=%d", m0_val, m1_val);
    gpio_set_level(m0, m0_val);  // ESP32 actively drives HIGH or LOW
    gpio_set_level(m1, m1_val);  // ESP32 actively drives HIGH or LOW
    vTaskDelay(pdMS_TO_TICKS(100));  // Wait for pin to settle
    
    // Read back to verify
    int m0_read = gpio_get_level(m0);
    int m1_read = gpio_get_level(m1);
    
    ESP_LOGI(TAG, "  M0: Set=%d, Read=%d %s", m0_val, m0_read, (m0_read == m0_val) ? "✓" : "✗");
    ESP_LOGI(TAG, "  M1: Set=%d, Read=%d %s", m1_val, m1_read, (m1_read == m1_val) ? "✓" : "✗");
    
    if (m0_read == m0_val && m1_read == m1_val) {
        ESP_LOGI(TAG, "  ✓ Mode verified successfully! ESP32 is controlling pins.");
    } else {
        ESP_LOGW(TAG, "  ✗ Mode mismatch - ESP32 cannot drive pins to desired state");
        if (m0_val == 1 && m0_read == 0) {
            ESP_LOGE(TAG, "    M0: Cannot drive HIGH - module may have strong pull-down");
            ESP_LOGE(TAG, "      Check: Pin connection, module power, or try different GPIO");
        }
        if (m1_val == 1 && m1_read == 0) {
            ESP_LOGE(TAG, "    M1: Cannot drive HIGH - module may have strong pull-down");
            ESP_LOGE(TAG, "      Check: Pin connection, module power, or try different GPIO");
        }
    }
}

// Simple function to send config and get response
esp_err_t send_config_and_get_response(uart_port_t uart_num, uint8_t *config_bytes, int len)
{
    ESP_LOGI(TAG, "  Sending config (%d bytes):", len);
    for (int i = 0; i < len; i++) {
        ESP_LOGI(TAG, "    [%d] = 0x%02X", i, config_bytes[i]);
    }
    
    // Clear buffer
    uart_flush(uart_num);
    vTaskDelay(pdMS_TO_TICKS(50));
    
    // Send configuration
    int written = uart_write_bytes(uart_num, config_bytes, len);
    ESP_LOGI(TAG, "  Written: %d bytes", written);
    
    // Wait for response
    vTaskDelay(pdMS_TO_TICKS(500));
    
    // Check for response
    size_t available = 0;
    uart_get_buffered_data_len(uart_num, &available);
    ESP_LOGI(TAG, "  Available bytes: %d", available);
    
    if (available > 0) {
        uint8_t response[12];
        int read = uart_read_bytes(uart_num, response, (available > 12) ? 12 : available, pdMS_TO_TICKS(100));
        ESP_LOGI(TAG, "  ✓ Response received (%d bytes):", read);
        for (int i = 0; i < read; i++) {
            ESP_LOGI(TAG, "    [%d] = 0x%02X", i, response[i]);
        }
        
        if (read > 0 && response[0] == 0xC1) {
            ESP_LOGI(TAG, "  ✓ SUCCESS! Module confirmed (0xC1)");
            return ESP_OK;
        } else if (read > 0) {
            ESP_LOGW(TAG, "  ⚠ Unexpected response: 0x%02X (expected 0xC1)", response[0]);
            return ESP_FAIL;
        }
    } else {
        ESP_LOGW(TAG, "  ✗ No response from module");
        return ESP_FAIL;
    }
    
    return ESP_FAIL;
}

void test_task(void *pvParameters)
{
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  SX1262 Simple Mode & Config Test");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "");
    
    // Initialize GPIO pins in PUSH-PULL mode - ESP32 actively drives HIGH and LOW
    // Push-pull: 0 = drive LOW, 1 = drive HIGH (ESP32 controls both states)
    // IMPORTANT: External 4.7kΩ-10kΩ pull-up resistors are REQUIRED on M0/M1 to 3.3V
    // The LoRa module has internal pull-down resistors that prevent ESP32 from
    // driving pins HIGH reliably without external pull-ups.
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "Initializing GPIO pins in PUSH-PULL mode...");
    ESP_LOGI(TAG, "  M0: GPIO%d", M0_PIN);
    ESP_LOGI(TAG, "  M1: GPIO%d", M1_PIN);
    ESP_LOGI(TAG, "  ESP32 will actively drive pins HIGH or LOW");
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "⚠ HARDWARE REQUIREMENT:");
    ESP_LOGI(TAG, "  Add external pull-up resistors (4.7kΩ or 10kΩ):");
    ESP_LOGI(TAG, "    M0 (GPIO%d) → [4.7kΩ] → 3.3V", M0_PIN);
    ESP_LOGI(TAG, "    M1 (GPIO%d) → [4.7kΩ] → 3.3V", M1_PIN);
    ESP_LOGI(TAG, "  Without these, ESP32 cannot drive pins HIGH!");
    ESP_LOGI(TAG, "");
    
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << M0_PIN) | (1ULL << M1_PIN),
        .mode = GPIO_MODE_OUTPUT,  // Push-pull mode - ESP32 drives both HIGH and LOW
        .pull_up_en = GPIO_PULLUP_DISABLE,  // Use external pull-ups (required)
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    
    // Set maximum drive strength to help overcome module's pull-down (40mA)
    // Note: Even with max drive, external pull-ups are still required
    gpio_set_drive_capability(M0_PIN, GPIO_DRIVE_CAP_3);  // Maximum: 40mA
    gpio_set_drive_capability(M1_PIN, GPIO_DRIVE_CAP_3);
    ESP_LOGI(TAG, "  Drive strength: Maximum (40mA)");
    ESP_LOGI(TAG, "");
    
    // Test if ESP32 can drive pins HIGH (without module connected)
    // Uncomment next line to test pins without module:
    // test_pins_without_module(M0_PIN, M1_PIN);
    
    // Initialize UART at 9600 baud
    uart_config_t uart_config = {
        .baud_rate = 9600,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM_1, 2048, 0, 0, NULL, 0);
    uart_param_config(UART_NUM_1, &uart_config);
    uart_set_pin(UART_NUM_1, GPIO_NUM_17, GPIO_NUM_16, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    
    ESP_LOGI(TAG, "UART initialized at 9600 baud");
    ESP_LOGI(TAG, "Waiting 1000ms for module reset...");
    vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Test different modes
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  Testing Different Modes");
    ESP_LOGI(TAG, "========================================");
    
    // Mode 1: Normal mode (M0=LOW, M1=LOW)
    set_and_verify_mode(M0_PIN, M1_PIN, 0, 0, "Normal");
    vTaskDelay(pdMS_TO_TICKS(200));
    
    // Mode 2: Wake-up mode (M0=HIGH, M1=LOW)
    set_and_verify_mode(M0_PIN, M1_PIN, 1, 0, "Wake-up");
    vTaskDelay(pdMS_TO_TICKS(200));
    
    // Mode 3: Power Save mode (M0=LOW, M1=HIGH) - This is CONFIG mode
    set_and_verify_mode(M0_PIN, M1_PIN, 0, 1, "Power Save/Config");
    vTaskDelay(pdMS_TO_TICKS(200));
    
    // Mode 4: Sleep mode (M0=HIGH, M1=HIGH)
    set_and_verify_mode(M0_PIN, M1_PIN, 1, 1, "Sleep");
    vTaskDelay(pdMS_TO_TICKS(200));
    
    // Now test configuration in CONFIG mode (M0=LOW, M1=HIGH)
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  Testing Configuration");
    ESP_LOGI(TAG, "========================================");
    
    // Set to config mode
    ESP_LOGI(TAG, "Setting to CONFIG mode (M0=LOW, M1=HIGH)...");
    set_and_verify_mode(M0_PIN, M1_PIN, 0, 1, "Config");
    vTaskDelay(pdMS_TO_TICKS(500));
    
    // Test configuration 1: Basic config
    uint8_t config1[12] = {0xC2, 0x00, 0x09, 0x00, 0x01, 0x00, 0xE2, 0x20, 0x12, 0xC3, 0x00, 0x00};
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "--- Config Test 1: Basic ---");
    esp_err_t ret1 = send_config_and_get_response(UART_NUM_1, config1, 12);
    
    vTaskDelay(pdMS_TO_TICKS(500));
    
    // Test configuration 2: Different address
    uint8_t config2[12] = {0xC2, 0x00, 0x09, 0x00, 0x02, 0x00, 0xE2, 0x20, 0x12, 0xC3, 0x00, 0x00};
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "--- Config Test 2: Different Address ---");
    esp_err_t ret2 = send_config_and_get_response(UART_NUM_1, config2, 12);
    
    vTaskDelay(pdMS_TO_TICKS(500));
    
    // Summary
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  Test Summary");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  Config Test 1: %s", (ret1 == ESP_OK) ? "✓ SUCCESS" : "✗ FAILED");
    ESP_LOGI(TAG, "  Config Test 2: %s", (ret2 == ESP_OK) ? "✓ SUCCESS" : "✗ FAILED");
    ESP_LOGI(TAG, "");
    
    // Keep running
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Starting SX1262 Simple Test...");
    
    xTaskCreate(test_task, "test_task", 8192, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "Test task created");
}
