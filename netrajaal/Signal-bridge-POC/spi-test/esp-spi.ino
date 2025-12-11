// main.c  -- build with ESP-IDF (v4.x or v5.x)
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
#include "esp_log.h"

static const char *TAG = "spi_slave_demo";

#define PIN_SCLK   18
#define PIN_MOSI   23
#define PIN_MISO   19
#define PIN_CS     5

// Max transfer size in bytes
#define TRANSFER_SIZE  64

void app_main(void)
{
    esp_err_t ret;

    // Configure SPI slave bus pins
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_MOSI,
        .miso_io_num = PIN_MISO,
        .sclk_io_num = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = TRANSFER_SIZE
    };

    // Configure CS pin (per-device)
    spi_slave_interface_config_t slvcfg = {
        .mode = 0,                 // SPI mode 0
        .spics_io_num = PIN_CS,    // CS pin
        .queue_size = 3,           // transaction queue depth
        .flags = 0,
        .post_setup_cb = NULL,
        .post_trans_cb = NULL
    };

    // Initialize SPI slave interface (VSPI_HOST)
    ret = spi_slave_initialize(VSPI_HOST, &buscfg, &slvcfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "spi_slave_initialize failed: %d", ret);
        return;
    }
    ESP_LOGI(TAG, "SPI slave initialized (CS=%d MOSI=%d MISO=%d SCLK=%d)", PIN_CS, PIN_MOSI, PIN_MISO, PIN_SCLK);

    // Buffers for transaction
    static uint8_t recvbuf[TRANSFER_SIZE];
    static uint8_t sendbuf[TRANSFER_SIZE];

    memset(sendbuf, 0xEE, sizeof(sendbuf)); // default reply pattern

    while (1) {
        // prepare a transaction descriptor
        spi_slave_transaction_t t;
        memset(&t, 0, sizeof(t));
        t.length = TRANSFER_SIZE * 8; // length in bits
        t.tx_buffer = sendbuf;
        t.rx_buffer = recvbuf;

        // Queue transaction and wait for master to start the transaction
        ret = spi_slave_queue_trans(VSPI_HOST, &t, portMAX_DELAY);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "spi_slave_queue_trans failed: %d", ret);
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Wait for transaction to be completed
        spi_slave_transaction_t *rt;
        ret = spi_slave_get_trans_result(VSPI_HOST, &rt, portMAX_DELAY);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "spi_slave_get_trans_result failed: %d", ret);
            continue;
        }

        // rt->rx_buffer now contains the bytes master sent
        ESP_LOGI(TAG, "Received %d bytes from master:", TRANSFER_SIZE);
        ESP_LOG_BUFFER_HEXDUMP(TAG, recvbuf, TRANSFER_SIZE, ESP_LOG_INFO);

        // Prepare reply based on received data (simple example)
        // We'll put echo of first 8 bytes + a counter
        static uint32_t counter = 0;
        counter++;
        for (int i = 0; i < TRANSFER_SIZE; ++i) {
            // simple demo reply: invert received byte, or send pattern if rx is 0
            if (recvbuf[i] != 0) sendbuf[i] = ~recvbuf[i];
            else sendbuf[i] = (counter + i) & 0xFF;
        }

        // loop to queue next transaction (sendbuf already updated)
        // short delay to avoid busy loop; can be removed if master drives transactions
        vTaskDelay(pdMS_TO_TICKS(10));
    }

    // never reached
    // spi_slave_free(VSPI_HOST);
}
