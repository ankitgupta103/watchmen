/*
 * ESP32 SPI Slave Code
 * Bidirectional SPI communication with OpenMV RT1062
 */

#include <driver/spi_slave.h>
#include <string.h>
#include <ctype.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "spi_slave";

// SPI Pin Configuration
#define SPI_MOSI 23
#define SPI_MISO 19
#define SPI_SCK 18
#define SPI_SS 5

// SPI Configuration
#define SPI_HOST_ID SPI2_HOST
#define DMA_CHAN 2
#define BUFFER_SIZE 64

static uint8_t response_counter = 0;

// Check if data is text (printable ASCII)
static bool is_text_data(const uint8_t *data, size_t len)
{
    if (len == 0) return false;
    
    size_t text_len = 0;
    for (size_t i = 0; i < len; i++) {
        if (data[i] == 0) {
            text_len = i;
            break;
        }
        text_len = i + 1;
    }
    
    if (text_len < 3) return false;
    
    for (size_t i = 0; i < text_len; i++) {
        if (!isprint(data[i]) && data[i] != '\n' && data[i] != '\r' && data[i] != '\t') {
            return false;
        }
    }
    
    return true;
}

// Extract text from buffer
static void extract_text(const uint8_t *buffer, size_t len, char *text, size_t text_size)
{
    size_t i = 0;
    while (i < len && i < text_size - 1) {
        if (buffer[i] == 0) break;
        if (isprint(buffer[i]) || buffer[i] == '\n' || buffer[i] == '\r' || buffer[i] == '\t') {
            text[i] = (char)buffer[i];
            i++;
        } else {
            break;
        }
    }
    text[i] = '\0';
}

// Prepare response based on received data
static void prepare_response(const uint8_t *rx_data, size_t rx_len, uint8_t *tx_buffer, size_t tx_size)
{
    memset(tx_buffer, 0, tx_size);
    
    if (is_text_data(rx_data, rx_len) && rx_len > 0) {
        // Received text - respond with acknowledgment
        char rx_text[BUFFER_SIZE];
        extract_text(rx_data, rx_len, rx_text, sizeof(rx_text));
        
        char response_msg[BUFFER_SIZE];
        if (strlen(rx_text) > 0) {
            char limited_text[36];
            strncpy(limited_text, rx_text, 35);
            limited_text[35] = '\0';
            snprintf(response_msg, sizeof(response_msg), "ESP32 ACK #%d: Got '%s'", response_counter, limited_text);
        } else {
            snprintf(response_msg, sizeof(response_msg), "ESP32 ACK #%d", response_counter);
        }
        response_counter++;
        
        size_t msg_len = strlen(response_msg);
        if (msg_len > tx_size - 1) msg_len = tx_size - 1;
        memcpy(tx_buffer, response_msg, msg_len);
    } else {
        // Received binary - respond with binary acknowledgment
        char response_msg[BUFFER_SIZE];
        if (rx_len <= 4 && rx_len > 0) {
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
        
        size_t msg_len = strlen(response_msg);
        if (msg_len > tx_size - 1) msg_len = tx_size - 1;
        memcpy(tx_buffer, response_msg, msg_len);
    }
}

void spi_slave_task(void *pvParameters)
{
    uint8_t rx_buffer[BUFFER_SIZE] = {0};
    uint8_t tx_buffer[BUFFER_SIZE] = {0};
    uint8_t sent_buffer[BUFFER_SIZE] = {0};
    
    // Initial response
    memset(tx_buffer, 0, BUFFER_SIZE);
    const char *init_msg = "ESP32 Ready";
    memcpy(tx_buffer, init_msg, strlen(init_msg));
    
    while (1) {
        memcpy(sent_buffer, tx_buffer, BUFFER_SIZE);
        
        spi_slave_transaction_t trans = {};
        trans.length = BUFFER_SIZE * 8;
        trans.tx_buffer = tx_buffer;
        trans.rx_buffer = rx_buffer;
        
        memset(rx_buffer, 0, BUFFER_SIZE);
        
        esp_err_t ret = spi_slave_transmit(SPI_HOST_ID, &trans, portMAX_DELAY);
        
        if (ret == ESP_OK) {
            size_t actual_len = trans.trans_len / 8;
            
            // Check if all zeros (read request)
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
            
            // Prepare new response only if we received actual data
            if (!all_zeros && actual_len > 0) {
                prepare_response(rx_buffer, actual_len, tx_buffer, BUFFER_SIZE);
            }
            
            // Simple logging - just RX and TX text
            if (all_zeros && actual_len > 0) {
                // Read request - show what we sent
                char tx_text[BUFFER_SIZE];
                extract_text(sent_buffer, BUFFER_SIZE, tx_text, sizeof(tx_text));
                ESP_LOGI(TAG, "RX: [read request] | TX: '%s'", tx_text);
            } else if (is_text_data(rx_buffer, actual_len)) {
                char rx_text[BUFFER_SIZE];
                char tx_text[BUFFER_SIZE];
                extract_text(rx_buffer, actual_len, rx_text, sizeof(rx_text));
                extract_text(sent_buffer, actual_len, tx_text, sizeof(tx_text));
                ESP_LOGI(TAG, "RX: '%s' | TX: '%s'", rx_text, tx_text);
            } else {
                // Binary data
                char tx_text[BUFFER_SIZE];
                extract_text(sent_buffer, actual_len, tx_text, sizeof(tx_text));
                ESP_LOGI(TAG, "RX: [binary %zu bytes] | TX: '%s'", actual_len, tx_text);
            }
        } else {
            ESP_LOGE(TAG, "SPI error: %s", esp_err_to_name(ret));
            memset(tx_buffer, 0, BUFFER_SIZE);
            const char *error_msg = "ESP32 Error";
            memcpy(tx_buffer, error_msg, strlen(error_msg));
        }
        
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32 SPI Slave Starting...");
    
    spi_bus_config_t buscfg = {
        .mosi_io_num = SPI_MOSI,
        .miso_io_num = SPI_MISO,
        .sclk_io_num = SPI_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = BUFFER_SIZE,
    };
    
    spi_slave_interface_config_t slvcfg = {};
    slvcfg.mode = 0;
    slvcfg.spics_io_num = SPI_SS;
    slvcfg.queue_size = 3;
    slvcfg.flags = 0;
    slvcfg.post_setup_cb = NULL;
    slvcfg.post_trans_cb = NULL;
    
    esp_err_t ret = spi_slave_initialize(SPI_HOST_ID, &buscfg, &slvcfg, DMA_CHAN);
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI Slave init failed: %s", esp_err_to_name(ret));
        return;
    }
    
    ESP_LOGI(TAG, "ESP32 SPI Slave ready");
    ESP_LOGI(TAG, "Mode: 0 (CPOL=0, CPHA=0)");
    
    xTaskCreate(spi_slave_task, "spi_slave_task", 4096, NULL, 5, NULL);
}
