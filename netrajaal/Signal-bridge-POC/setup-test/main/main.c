/*
 * ESP32 SPI Slave - Simple Echo Communication with OpenMV RT1062
 */

#include <driver/spi_slave.h>
#include <string.h>
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
#define BUFFER_SIZE 32

static uint8_t counter = 0;

void spi_slave_task(void *pvParameters)
{
    uint8_t rx_buffer[BUFFER_SIZE] = {0};
    uint8_t tx_buffer[BUFFER_SIZE] = {0};
    
    // Initial message
    const char *init_msg = "ESP32 Ready";
    memset(tx_buffer, 0, BUFFER_SIZE);
    memcpy(tx_buffer, init_msg, strlen(init_msg) < BUFFER_SIZE ? strlen(init_msg) : BUFFER_SIZE - 1);
    
    while (1) {
        spi_slave_transaction_t trans = {
            .length = BUFFER_SIZE * 8,
            .tx_buffer = tx_buffer,
            .rx_buffer = rx_buffer,
        };
        
        esp_err_t ret = spi_slave_transmit(SPI_HOST_ID, &trans, portMAX_DELAY);
        
        if (ret == ESP_OK) {
            size_t actual_len = trans.trans_len / 8;
            
            // Simple echo: clear TX buffer and copy received data for next transaction
            memset(tx_buffer, 0, BUFFER_SIZE);
            size_t copy_len = (actual_len < BUFFER_SIZE) ? actual_len : BUFFER_SIZE;
            memcpy(tx_buffer, rx_buffer, copy_len);
            
            // Simple logging with counter
            ESP_LOGI(TAG, "[%d] RX: %.*s", counter++, (int)copy_len, (char*)rx_buffer);
        } else {
            ESP_LOGE(TAG, "SPI error: %s", esp_err_to_name(ret));
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
    
    spi_slave_interface_config_t slvcfg = {
        .mode = 0,
        .spics_io_num = SPI_SS,
        .queue_size = 3,
        .flags = 0,
    };
    
    esp_err_t ret = spi_slave_initialize(SPI_HOST_ID, &buscfg, &slvcfg, DMA_CHAN);
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SPI Slave init failed: %s", esp_err_to_name(ret));
        return;
    }
    
    ESP_LOGI(TAG, "ESP32 SPI Slave ready (Mode 0)");
    
    xTaskCreate(spi_slave_task, "spi_slave_task", 4096, NULL, 5, NULL);
}
