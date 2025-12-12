/*
 * ESP32 SPI Slave Code
 * Bidirectional SPI communication with OpenMV RT1062
 * 
 * Uses ESP32's standard SPI Slave driver API
 */

#include <driver/spi_slave.h>
#include <string.h>
#include <ctype.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "spi_slave";

// SPI Pin Configuration for ESP32
#define SPI_MOSI 23  // Master Out, Slave In
#define SPI_MISO 19  // Master In, Slave Out
#define SPI_SCK 18   // Serial Clock
#define SPI_SS 5     // Slave Select (Chip Select)

// SPI Configuration
#define SPI_HOST_ID SPI2_HOST  // Use HSPI (SPI2)
#define DMA_CHAN 2
#define BUFFER_SIZE 64

// Global response counter
static uint8_t response_counter = 0;

/**
 * Check if received data is text (printable ASCII)
 * Handles zero-padding at the end
 */
static bool is_text_data(const uint8_t *data, size_t len)
{
    if (len == 0) return false;
    
    // Find the actual text length (up to first null or end)
    size_t text_len = 0;
    for (size_t i = 0; i < len; i++) {
        if (data[i] == 0) {
            text_len = i;
            break;
        }
        text_len = i + 1;
    }
    
    // Need at least a few printable characters to consider it text
    if (text_len < 3) return false;
    
    // Check if the non-zero portion is printable
    for (size_t i = 0; i < text_len; i++) {
        if (!isprint(data[i]) && data[i] != '\n' && data[i] != '\r' && data[i] != '\t') {
            return false;
        }
    }
    
    return true;
}

/**
 * Extract text from received buffer (up to null terminator or buffer end)
 */
static void extract_text(const uint8_t *buffer, size_t len, char *text, size_t text_size)
{
    size_t i = 0;
    // Extract up to first null or end of buffer
    while (i < len && i < text_size - 1) {
        if (buffer[i] == 0) {
            break;
        }
        if (isprint(buffer[i]) || buffer[i] == '\n' || buffer[i] == '\r' || buffer[i] == '\t') {
            text[i] = (char)buffer[i];
            i++;
        } else {
            break;  // Stop at first non-printable
        }
    }
    text[i] = '\0';
}

/**
 * Prepare response message based on received data
 * Always fills the entire buffer to ensure proper SPI communication
 */
static void prepare_response(const uint8_t *rx_data, size_t rx_len, uint8_t *tx_buffer, size_t tx_size)
{
    // Always prepare a full response buffer - zero it first
    memset(tx_buffer, 0, tx_size);
    
    // Check if received data is text
    if (is_text_data(rx_data, rx_len) && rx_len > 0) {
        // Received text - respond with text acknowledgment
        char rx_text[BUFFER_SIZE];
        extract_text(rx_data, rx_len, rx_text, sizeof(rx_text));
        
        // Create response text (limit rx_text length to avoid truncation)
        char response_msg[BUFFER_SIZE];
        if (strlen(rx_text) > 0) {
            // Limit rx_text to 35 chars to ensure response fits in buffer
            char limited_text[36];
            strncpy(limited_text, rx_text, 35);
            limited_text[35] = '\0';
            snprintf(response_msg, sizeof(response_msg), "ESP32 ACK #%d: Got '%s'", response_counter, limited_text);
        } else {
            snprintf(response_msg, sizeof(response_msg), "ESP32 ACK #%d", response_counter);
        }
        response_counter++;
        
        // Copy to transmit buffer - fill entire buffer
        size_t msg_len = strlen(response_msg);
        if (msg_len > tx_size - 1) {
            msg_len = tx_size - 1;
        }
        memcpy(tx_buffer, response_msg, msg_len);
        // Rest of buffer is already zeroed by memset above
    } else {
        // Received binary data - respond with text acknowledgment mentioning binary
        char response_msg[BUFFER_SIZE];
        if (rx_len <= 4 && rx_len > 0) {
            // Short binary - show hex
            snprintf(response_msg, sizeof(response_msg), "ESP32: Binary %02x%02x%02x%02x #%d", 
                    rx_data[0],
                    rx_len > 1 ? rx_data[1] : 0,
                    rx_len > 2 ? rx_data[2] : 0,
                    rx_len > 3 ? rx_data[3] : 0,
                    response_counter);
        } else {
            snprintf(response_msg, sizeof(response_msg), "ESP32: Received %zu bytes binary #%d", rx_len, response_counter);
        }
        response_counter++;
        
        // Copy to transmit buffer - fill entire buffer
        size_t msg_len = strlen(response_msg);
        if (msg_len > tx_size - 1) {
            msg_len = tx_size - 1;
        }
        memcpy(tx_buffer, response_msg, msg_len);
        // Rest of buffer is already zeroed by memset above
    }
}

/**
 * Send text message via SPI (helper function)
 * Note: In slave mode, we can't initiate transfers, but we prepare responses
 */
void spi_slave_send_text(const char *text, uint8_t *tx_buffer, size_t buffer_size)
{
    memset(tx_buffer, 0, buffer_size);
    size_t text_len = strlen(text);
    if (text_len >= buffer_size) {
        text_len = buffer_size - 1;
    }
    memcpy(tx_buffer, text, text_len);
}

void spi_slave_task(void *pvParameters)
{
  // Transaction buffers
  uint8_t rx_buffer[BUFFER_SIZE] = {0};
  uint8_t tx_buffer[BUFFER_SIZE] = {0};
  uint8_t sent_buffer[BUFFER_SIZE] = {0};  // Keep track of what we actually sent
  
  // Prepare initial response - fill entire buffer
  memset(tx_buffer, 0, BUFFER_SIZE);
  const char *init_msg = "ESP32 Ready";
  memcpy(tx_buffer, init_msg, strlen(init_msg));
  
  while (1) {
    // Save what we're about to send (for logging)
    memcpy(sent_buffer, tx_buffer, BUFFER_SIZE);
    
    // Initialize SPI transaction
    spi_slave_transaction_t trans = {};
    trans.length = BUFFER_SIZE * 8;  // Maximum length in bits (master controls actual length)
    trans.tx_buffer = tx_buffer;  // Send what we prepared (always full buffer)
    trans.rx_buffer = rx_buffer;  // Receive into this buffer
    
    // Clear receive buffer before transaction
    memset(rx_buffer, 0, BUFFER_SIZE);
    
    // Wait for transaction from master (blocking)
    esp_err_t ret = spi_slave_transmit(SPI_HOST_ID, &trans, portMAX_DELAY);
    
    if (ret == ESP_OK) {
      // Get actual transaction length
      size_t actual_len = trans.trans_len / 8;  // Convert bits to bytes
      
      // Check if we received all zeros (this is a "read response" request from master)
      // In this case, don't prepare a new response, keep the current one
      bool all_zeros = false;
      if (actual_len > 0) {
        all_zeros = true;
        for (size_t i = 0; i < actual_len && i < BUFFER_SIZE; i++) {
          if (rx_buffer[i] != 0) {
            all_zeros = false;
            break;
          }
        }
      }
      
      // Only prepare new response if we received actual data (not a read request)
      if (!all_zeros && actual_len > 0) {
        // Prepare response for NEXT transaction based on what we received in THIS transaction
        // This will be sent in the next SPI transaction
        prepare_response(rx_buffer, actual_len, tx_buffer, BUFFER_SIZE);
      }
      // If all zeros or zero length, keep the current tx_buffer (don't overwrite the prepared response)
      
      // Build log message
      char log_msg[512];
      int pos = 0;
      
      pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "RX: %zu bytes | ", actual_len);
      
      // Print received data (hex)
      for (size_t i = 0; i < actual_len && i < BUFFER_SIZE && pos < sizeof(log_msg) - 20; i++) {
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "%02x ", rx_buffer[i]);
      }
      
      pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "| ");
      
      // Print received data (text)
      if (all_zeros && actual_len > 0) {
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "[read request]");
      } else if (is_text_data(rx_buffer, actual_len)) {
        char rx_text[BUFFER_SIZE];
        extract_text(rx_buffer, actual_len, rx_text, sizeof(rx_text));
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "'%s'", rx_text);
      } else {
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "[binary]");
      }
      
      pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, " | TX: ");
      
      // Print sent data (hex) - show what we ACTUALLY sent in THIS transaction
      size_t tx_show_len = (actual_len < BUFFER_SIZE) ? actual_len : BUFFER_SIZE;
      for (size_t i = 0; i < tx_show_len && pos < sizeof(log_msg) - 20; i++) {
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "%02x ", sent_buffer[i]);
      }
      
      pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "| ");
      
      // Print sent data (text) - show what we ACTUALLY sent in THIS transaction
      if (is_text_data(sent_buffer, tx_show_len)) {
        char tx_text[BUFFER_SIZE];
        extract_text(sent_buffer, tx_show_len, tx_text, sizeof(tx_text));
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "'%s'", tx_text);
      } else {
        pos += snprintf(log_msg + pos, sizeof(log_msg) - pos, "[binary]");
      }
      
      ESP_LOGI(TAG, "%s", log_msg);
    } else {
      ESP_LOGE(TAG, "SPI error: %s", esp_err_to_name(ret));
      // Prepare default response for next transaction
      spi_slave_send_text("ESP32 Error", tx_buffer, BUFFER_SIZE);
    }
    
    // Small delay to prevent CPU spinning
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

void app_main(void)
{
  ESP_LOGI(TAG, "ESP32 SPI Slave Starting...");
  
  // Configure SPI Bus
  spi_bus_config_t buscfg = {
    .mosi_io_num = SPI_MOSI,
    .miso_io_num = SPI_MISO,
    .sclk_io_num = SPI_SCK,
    .quadwp_io_num = -1,
    .quadhd_io_num = -1,
    .max_transfer_sz = BUFFER_SIZE,
  };
  
  // Configure SPI Slave Interface
  spi_slave_interface_config_t slvcfg = {};
  slvcfg.mode = 0;                    // SPI Mode 0: CPOL=0, CPHA=0
  slvcfg.spics_io_num = SPI_SS;
  slvcfg.queue_size = 3;
  slvcfg.flags = 0;
  slvcfg.post_setup_cb = NULL;
  slvcfg.post_trans_cb = NULL;
  
  // Initialize SPI Slave
  esp_err_t ret = spi_slave_initialize(SPI_HOST_ID, &buscfg, &slvcfg, DMA_CHAN);
  
  if (ret != ESP_OK) {
    ESP_LOGE(TAG, "SPI Slave init failed: %s", esp_err_to_name(ret));
    return;
  }
  
  ESP_LOGI(TAG, "ESP32 SPI Slave ready");
  ESP_LOGI(TAG, "Mode: 0 (CPOL=0, CPHA=0)");
  ESP_LOGI(TAG, "Ready for bidirectional text communication");
  
  // Create task for SPI slave loop
  xTaskCreate(spi_slave_task, "spi_slave_task", 4096, NULL, 5, NULL);
}
