/**
 * @file sx1262_example.c
 * @brief Example usage of SX1262 LoRa driver
 * 
 * This example demonstrates how to:
 * 1. Initialize the SX1262 module
 * 2. Send data to another node
 * 3. Receive data from other nodes
 * 4. Read channel RSSI
 * 
 * Hardware Connections:
 *   - UART1: TX=GPIO17, RX=GPIO16 (adjust if needed)
 *   - M0 pin: GPIO_NUM_4 (adjust based on your board)
 *   - M1 pin: GPIO_NUM_5 (adjust based on your board)
 */

#include "sx1262.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "SX1262_EXAMPLE";

void sx1262_example_task(void *pvParameters)
{
    sx1262_handle_t lora_handle;
    sx1262_config_t config = {
        .uart_num = UART_NUM_1,
        .m0_pin = GPIO_NUM_4,      // Adjust based on your board
        .m1_pin = GPIO_NUM_5,       // Adjust based on your board
        .addr = 0x0001,            // Node address
        .freq = 868,               // Frequency in MHz (868 MHz for EU)
        .power = 22,               // TX power: 22 dBm (max)
        .air_speed = 2400,         // Air data rate: 2400 bps
        .net_id = 0,               // Network ID
        .buffer_size = 240,        // Buffer size: 240 bytes
        .crypt_key = 0,            // Encryption key (0 = disabled)
        .rssi_enabled = true,      // Enable RSSI reporting
        .persistent_config = false // RAM only (resets on power cycle)
    };
    
    // Initialize module
    ESP_LOGI(TAG, "Initializing SX1262 module...");
    esp_err_t ret = sx1262_init(&config, &lora_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SX1262: %s", esp_err_to_name(ret));
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(TAG, "SX1262 initialized successfully!");
    
    // Read channel RSSI
    int8_t rssi;
    if (sx1262_get_channel_rssi(&lora_handle, &rssi) == ESP_OK) {
        ESP_LOGI(TAG, "Channel RSSI: %d dBm", rssi);
    }
    
    int counter = 0;
    while (1) {
        // Send a message every 5 seconds
        char message[64];
        int len = snprintf(message, sizeof(message), "Hello from node %d, counter: %d", 
                          config.addr, counter++);
        
        ESP_LOGI(TAG, "Sending message to address 0xFFFF (broadcast)...");
        ret = sx1262_send(&lora_handle, 0xFFFF, (uint8_t *)message, len);
        if (ret == ESP_OK) {
            ESP_LOGI(TAG, "Message sent successfully");
        } else {
            ESP_LOGE(TAG, "Failed to send message: %s", esp_err_to_name(ret));
        }
        
        // Try to receive messages
        uint8_t rx_buffer[256];
        size_t received_len;
        int8_t rx_rssi;
        
        ret = sx1262_receive(&lora_handle, rx_buffer, sizeof(rx_buffer), 
                            &received_len, &rx_rssi);
        if (ret == ESP_OK) {
            rx_buffer[received_len] = '\0';  // Null terminate
            ESP_LOGI(TAG, "Received %d bytes: %s", received_len, rx_buffer);
            if (rx_rssi != 0) {
                ESP_LOGI(TAG, "RSSI: %d dBm", rx_rssi);
            }
        } else if (ret != ESP_ERR_NOT_FOUND) {
            ESP_LOGW(TAG, "Receive error: %s", esp_err_to_name(ret));
        }
        
        vTaskDelay(pdMS_TO_TICKS(5000));  // Wait 5 seconds
    }
    
    // Cleanup (never reached in this example)
    sx1262_deinit(&lora_handle);
    vTaskDelete(NULL);
}

