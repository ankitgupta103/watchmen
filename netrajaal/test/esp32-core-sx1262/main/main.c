/**
 * @file main.c
 * @brief Main application for ESP32 SX1262 LoRa point-to-point communication
 * 
 * This is a minimal example demonstrating point-to-point LoRa communication
 * between two Core1262-868M modules using ESP32.
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "lora_sx1262.h"

static const char *TAG = "MAIN";

// Pin configuration (from reference implementation)
static const lora_sx1262_pins_t pins = LORA_SX1262_PINS_DEFAULT;

// LoRa configuration (from reference implementation)
static const lora_sx1262_config_t config = LORA_SX1262_CONFIG_DEFAULT;

/**
 * @brief Example: Transmit a packet
 */
static void example_transmit(void)
{
    const char *message = "Hello LoRa!";
    size_t len = strlen(message);
    
    ESP_LOGI(TAG, "Transmitting: %s", message);
    lora_sx1262_err_t err = lora_sx1262_transmit((const uint8_t *)message, len, 0);
    
    if (err == LORA_SX1262_OK) {
        ESP_LOGI(TAG, "Transmission successful");
    } else {
        ESP_LOGE(TAG, "Transmission failed: %d", err);
    }
}

/**
 * @brief Example: Receive a packet
 */
static void example_receive(void)
{
    uint8_t buffer[256];
    size_t received_len = 0;
    
    ESP_LOGI(TAG, "Waiting for packet...");
    lora_sx1262_err_t err = lora_sx1262_receive(buffer, sizeof(buffer), &received_len, 5000);
    
    if (err == LORA_SX1262_OK) {
        buffer[received_len] = '\0';  // Null terminate
        ESP_LOGI(TAG, "Received (%d bytes): %s", received_len, buffer);
        ESP_LOGI(TAG, "RSSI: %.2f dBm, SNR: %.2f dB", 
                 lora_sx1262_get_rssi(), lora_sx1262_get_snr());
    } else if (err == LORA_SX1262_ERR_RX_TIMEOUT) {
        ESP_LOGW(TAG, "Receive timeout");
    } else {
        ESP_LOGE(TAG, "Receive failed: %d", err);
    }
}

/**
 * @brief Example: Continuous receive mode
 */
static void example_continuous_receive(void)
{
    uint8_t buffer[256];
    size_t received_len = 0;
    
    ESP_LOGI(TAG, "Starting continuous receive mode...");
    lora_sx1262_err_t err = lora_sx1262_start_receive();
    if (err != LORA_SX1262_OK) {
        ESP_LOGE(TAG, "Failed to start receive: %d", err);
        return;
    }
    
    while (1) {
        err = lora_sx1262_wait_packet(buffer, sizeof(buffer), &received_len, 5000);
        if (err == LORA_SX1262_OK) {
            buffer[received_len] = '\0';
            ESP_LOGI(TAG, "Received (%d bytes): %s", received_len, buffer);
            ESP_LOGI(TAG, "RSSI: %.2f dBm, SNR: %.2f dB", 
                     lora_sx1262_get_rssi(), lora_sx1262_get_snr());
        } else if (err == LORA_SX1262_ERR_CRC) {
            ESP_LOGW(TAG, "CRC error, ignoring packet");
        } else if (err == LORA_SX1262_ERR_RX_TIMEOUT) {
            ESP_LOGD(TAG, "Receive timeout, continuing...");
        } else {
            ESP_LOGE(TAG, "Receive error: %d", err);
            break;
        }
    }
}

/**
 * @brief Main application entry point
 */
void app_main(void)
{   
    ESP_LOGI(TAG, "ESP32 SX1262 LoRa P2P Communication");
    ESP_LOGI(TAG, "Initializing SX1262...");
    
    // Initialize the SX1262 module
    lora_sx1262_err_t err = lora_sx1262_init(&pins, &config);
    if (err != LORA_SX1262_OK) {
        ESP_LOGE(TAG, "SX1262 initialization failed: %d", err);
        return;
    }
    
    ESP_LOGI(TAG, "SX1262 initialized successfully");
    ESP_LOGI(TAG, "Frequency: %lu Hz", config.frequency);
    ESP_LOGI(TAG, "Bandwidth: %d, SF: %d, CR: %d", 
             config.bandwidth, config.spreading_factor + 5, config.coding_rate + 5);
    ESP_LOGI(TAG, "TX Power: %d dBm", config.tx_power);
    
    // Example usage: Choose one of the following
    
    // Option 1: Simple TX/RX test
    // Uncomment to test transmission
    // example_transmit();
    // vTaskDelay(pdMS_TO_TICKS(1000));
    
    // Uncomment to test reception
    // example_receive();
    
    // Option 2: Continuous receive mode (for RX module)
    // Uncomment for continuous listening
    example_continuous_receive();
    
    // Option 3: Periodic TX (for TX module)
    // Uncomment to transmit periodically
    /*
    while (1) {
        example_transmit();
        vTaskDelay(pdMS_TO_TICKS(5000));  // Transmit every 5 seconds
    }
    */
}
