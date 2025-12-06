/**
 * @file main.c
 * @brief Two-Node SX1262 LoRa Communication Example
 * 
 * This example demonstrates bidirectional communication between two ESP32 boards
 * each equipped with an SX1262 LoRa module.
 * 
 * Configuration:
 *   - Change NODE_ID to 1 or 2 to configure each board
 *   - Node 1 sends to Node 2 (address 0x0002)
 *   - Node 2 sends to Node 1 (address 0x0001)
 *   - Both nodes can receive from each other
 * 
 * Hardware Connections:
 *   - UART1: TX=GPIO17, RX=GPIO16
 *   - M0 pin: GPIO_NUM_4
 *   - M1 pin: GPIO_NUM_5
 *   - Adjust pins in config below if needed
 */

#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "sx1262.h"

static const char *TAG = "LORA_COMM";

// ============================================================================
// CONFIGURATION - Change this for each ESP32 board
// ============================================================================

// Set NODE_ID to 1 for first ESP32, 2 for second ESP32
#define NODE_ID 1

// GPIO pin configuration (adjust based on your board)
#define M0_PIN GPIO_NUM_4
#define M1_PIN GPIO_NUM_5

// LoRa module configuration
#define FREQUENCY 868        // MHz (868 for EU, 915 for US, 433 for Asia)
#define TX_POWER 22          // dBm (10, 13, 17, or 22)
#define AIR_SPEED 2400       // bps (1200-62500)
#define NETWORK_ID 0         // Network ID (0-255, must match on both nodes)

// ============================================================================
// Node Configuration
// ============================================================================

#if NODE_ID == 1
    #define MY_ADDRESS 0x0001
    #define TARGET_ADDRESS 0x0002
    #define NODE_NAME "Node-1"
#elif NODE_ID == 2
    #define MY_ADDRESS 0x0002
    #define TARGET_ADDRESS 0x0001
    #define NODE_NAME "Node-2"
#else
    #error "NODE_ID must be 1 or 2"
#endif

// ============================================================================
// Communication Task
// ============================================================================

void lora_communication_task(void *pvParameters)
{
    sx1262_handle_t lora_handle;
    
    // Configure SX1262 module
    sx1262_config_t config = {
        .uart_num = UART_NUM_1,
        .m0_pin = M0_PIN,
        .m1_pin = M1_PIN,
        .addr = MY_ADDRESS,
        .freq = FREQUENCY,
        .power = TX_POWER,
        .air_speed = AIR_SPEED,
        .net_id = NETWORK_ID,
        .buffer_size = 240,
        .crypt_key = 0,              // No encryption
        .rssi_enabled = true,        // Enable RSSI reporting
        .persistent_config = false   // RAM only (resets on power cycle)
    };
    
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  %s - LoRa Communication", NODE_NAME);
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "My Address: 0x%04X", MY_ADDRESS);
    ESP_LOGI(TAG, "Target Address: 0x%04X", TARGET_ADDRESS);
    ESP_LOGI(TAG, "Frequency: %d MHz", FREQUENCY);
    ESP_LOGI(TAG, "TX Power: %d dBm", TX_POWER);
    ESP_LOGI(TAG, "Air Speed: %d bps", AIR_SPEED);
    ESP_LOGI(TAG, "Network ID: %d", NETWORK_ID);
    ESP_LOGI(TAG, "========================================");
    
    // Initialize SX1262 module
    ESP_LOGI(TAG, "Initializing SX1262 module...");
    esp_err_t ret = sx1262_init(&config, &lora_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SX1262: %s", esp_err_to_name(ret));
        ESP_LOGE(TAG, "Please check:");
        ESP_LOGE(TAG, "  - UART connections (TX/RX)");
        ESP_LOGE(TAG, "  - M0/M1 pin connections");
        ESP_LOGE(TAG, "  - Power supply (3.3V)");
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(TAG, "SX1262 initialized successfully!");
    
    // Read channel RSSI
    int8_t channel_rssi;
    if (sx1262_get_channel_rssi(&lora_handle, &channel_rssi) == ESP_OK) {
        ESP_LOGI(TAG, "Channel RSSI (background noise): %d dBm", channel_rssi);
    }
    
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "Starting communication...");
    ESP_LOGI(TAG, "  - Sending messages every 3 seconds");
    ESP_LOGI(TAG, "  - Listening for incoming messages");
    ESP_LOGI(TAG, "");
    
    uint32_t message_counter = 0;
    uint32_t send_counter = 0;
    uint32_t receive_counter = 0;
    
    // Initialize to current time to avoid sending immediately
    TickType_t last_send_time = xTaskGetTickCount();
    const TickType_t send_interval = pdMS_TO_TICKS(3000);  // Send every 3 seconds
    
    while (1) {
        TickType_t current_time = xTaskGetTickCount();
        
        // Send message periodically
        if ((current_time - last_send_time) >= send_interval) {
            message_counter++;
            send_counter++;
            
            // Build message
            char message[128];
            int len = snprintf(message, sizeof(message), 
                             "Hello from %s! Message #%lu", 
                             NODE_NAME, message_counter);
            
            ESP_LOGI(TAG, ">>> [SEND] To 0x%04X: %s", TARGET_ADDRESS, message);
            
            ret = sx1262_send(&lora_handle, TARGET_ADDRESS, (uint8_t *)message, len);
            if (ret == ESP_OK) {
                ESP_LOGI(TAG, "    ✓ Message sent successfully");
            } else {
                ESP_LOGE(TAG, "    ✗ Send failed: %s", esp_err_to_name(ret));
            }
            
            last_send_time = current_time;
        }
        
        // Try to receive messages
        uint8_t rx_buffer[256];
        size_t received_len;
        int8_t rx_rssi;
        
        ret = sx1262_receive(&lora_handle, rx_buffer, sizeof(rx_buffer), 
                            &received_len, &rx_rssi);
        
        if (ret == ESP_OK) {
            receive_counter++;
            rx_buffer[received_len] = '\0';  // Null terminate
            
            ESP_LOGI(TAG, "<<< [RECEIVE] %d bytes:", received_len);
            ESP_LOGI(TAG, "    Message: %s", rx_buffer);
            if (rx_rssi != 0) {
                ESP_LOGI(TAG, "    RSSI: %d dBm", rx_rssi);
            }
            ESP_LOGI(TAG, "    Total received: %lu messages", receive_counter);
        } else if (ret != ESP_ERR_NOT_FOUND) {
            ESP_LOGW(TAG, "Receive error: %s", esp_err_to_name(ret));
        }
        
        // Small delay to prevent CPU spinning
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    // Cleanup (never reached in this example)
    sx1262_deinit(&lora_handle);
    vTaskDelete(NULL);
}

// ============================================================================
// Main Application Entry Point
// ============================================================================

void app_main(void)
{
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  ESP32 LoRa Two-Node Communication");
    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Node ID: %d", NODE_ID);
    ESP_LOGI(TAG, "Node Name: %s", NODE_NAME);
    ESP_LOGI(TAG, "My Address: 0x%04X", MY_ADDRESS);
    ESP_LOGI(TAG, "Target Address: 0x%04X", TARGET_ADDRESS);
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "To configure the other node:");
    ESP_LOGI(TAG, "  1. Change NODE_ID to %d", (NODE_ID == 1) ? 2 : 1);
    ESP_LOGI(TAG, "  2. Rebuild and flash");
    ESP_LOGI(TAG, "");
    
    // Create communication task
    xTaskCreate(
        lora_communication_task,    // Task function
        "lora_comm",                 // Task name
        8192,                        // Stack size
        NULL,                        // Parameters
        5,                           // Priority
        NULL                         // Task handle
    );
    
    ESP_LOGI(TAG, "Communication task started");
    ESP_LOGI(TAG, "System ready!");
}
