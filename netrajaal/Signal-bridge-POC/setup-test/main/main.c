#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "driver/spi_slave.h"

// GPIOs to be pulled LOW
#define PIN_D21            21
#define PIN_D22            22

// LED GPIO
#define LED_PIN             2

// SPI slave configuration (ESP32 is SPI slave to OpenMV)
#define BRIDGE_SPI_HOST     HSPI_HOST
#define PIN_MOSI            23
#define PIN_MISO            19
#define PIN_SCLK            18
#define PIN_CS              5

// External UART using pins 16 (RX) and 17 (TX)
#define UART_EXT            UART_NUM_1
#define UART_EXT_RX_PIN     16
#define UART_EXT_TX_PIN     17

// Console UART (USB-JTAG/serial)
#define UART_USB            UART_NUM_0

// UART config
#define UART_BAUD_RATE          115200
#define UART_EXT_RX_BUF_SIZE    4096    // large buffer for fast incoming data
#define UART_USB_RX_BUF_SIZE    512

// SPI frame size to send towards OpenMV
#define SPI_FRAME_SIZE      250

// SPI TX/RX buffers (one frame)
static uint8_t spi_tx_buf[SPI_FRAME_SIZE];
static uint8_t spi_rx_buf[SPI_FRAME_SIZE];

static void led_blink_short(void)
{
    // Turn LED ON briefly
    gpio_set_level(LED_PIN, 1);
    // 10 ms ON time
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(LED_PIN, 0);
}

// Task: data coming from external UART (UART_EXT) -> update SPI TX buffer
static void uart_ext_to_spi_task(void *arg)
{
    uint8_t buf[256];

    while (1) {
        int len = uart_read_bytes(UART_EXT, buf, sizeof(buf), pdMS_TO_TICKS(10));
        if (len > 0) {
            // Prepare SPI frame from received UART data (truncate or pad to SPI_FRAME_SIZE)
            int to_send = len;
            if (to_send > SPI_FRAME_SIZE) {
                to_send = SPI_FRAME_SIZE;
            }
            memset(spi_tx_buf, 0, SPI_FRAME_SIZE);
            memcpy(spi_tx_buf, buf, to_send);

            led_blink_short();
        }
    }
}

// Task: data coming from USB console (UART_USB) -> external UART (UART_EXT)
static void usb_to_uart_ext_task(void *arg)
{
    uint8_t buf[256];

    while (1) {
        int len = uart_read_bytes(UART_USB, buf, sizeof(buf), pdMS_TO_TICKS(10));
        if (len > 0) {
            uart_write_bytes(UART_EXT, (const char *)buf, len);
            // Also mirror USB data into SPI TX buffer so OpenMV can see it
            int to_send = len;
            if (to_send > SPI_FRAME_SIZE) {
                to_send = SPI_FRAME_SIZE;
            }
            memset(spi_tx_buf, 0, SPI_FRAME_SIZE);
            memcpy(spi_tx_buf, buf, to_send);

            led_blink_short();
        }
    }
}

// Task: SPI slave loop. Always ready to send the latest contents of spi_tx_buf.
static void spi_slave_task(void *arg)
{
    while (1) {
        memset(spi_rx_buf, 0, SPI_FRAME_SIZE);

        spi_slave_transaction_t t = {0};
        t.length = SPI_FRAME_SIZE * 8;   // bits
        t.tx_buffer = spi_tx_buf;
        t.rx_buffer = spi_rx_buf;

        (void)spi_slave_transmit(BRIDGE_SPI_HOST, &t, portMAX_DELAY);
    }
}

void app_main(void)
{
    // Configure GPIOs 21 and 22 as outputs and drive LOW
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_D21) | (1ULL << PIN_D22),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf);
    gpio_set_level(PIN_D21, 0);
    gpio_set_level(PIN_D22, 0);

    // Configure LED GPIO
    gpio_config_t led_conf = {
        .pin_bit_mask = (1ULL << LED_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&led_conf);
    gpio_set_level(LED_PIN, 0);

    // Configure external UART on pins 16 (RX) and 17 (TX)
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };

    // External UART on pins 16 (RX) and 17 (TX)
    ESP_ERROR_CHECK(uart_driver_install(UART_EXT, UART_EXT_RX_BUF_SIZE, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_EXT, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_EXT, UART_EXT_TX_PIN, UART_EXT_RX_PIN,
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    // USB/console UART
    ESP_ERROR_CHECK(uart_driver_install(UART_USB, UART_USB_RX_BUF_SIZE, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_USB, &uart_config));

    // Configure SPI slave (ESP32 as slave)
    spi_bus_config_t buscfg = {
        .mosi_io_num = PIN_MOSI,
        .miso_io_num = PIN_MISO,
        .sclk_io_num = PIN_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = SPI_FRAME_SIZE,
    };

    spi_slave_interface_config_t slvcfg = {
        .mode = 0,
        .spics_io_num = PIN_CS,
        .queue_size = 1,
        .flags = 0,
        .post_setup_cb = NULL,
        .post_trans_cb = NULL,
    };

    ESP_ERROR_CHECK(spi_slave_initialize(BRIDGE_SPI_HOST, &buscfg, &slvcfg, SPI_DMA_CH_AUTO));

    // Initialize SPI TX buffer with a known test pattern until UART data arrives
    memset(spi_tx_buf, 0, SPI_FRAME_SIZE);
    const char *test_msg = "NO UART DATA YET - SPI TEST PATTERN";
    size_t msg_len = strlen(test_msg);
    if (msg_len > SPI_FRAME_SIZE) {
        msg_len = SPI_FRAME_SIZE;
    }
    memcpy(spi_tx_buf, test_msg, msg_len);

    // Start bridge tasks (run in parallel)
    xTaskCreate(uart_ext_to_spi_task, "uart_ext_to_spi_task", 4096, NULL, 10, NULL);
    xTaskCreate(usb_to_uart_ext_task, "usb_to_uart_ext_task", 4096, NULL, 10, NULL);
    xTaskCreate(spi_slave_task, "spi_slave_task", 4096, NULL, 10, NULL);
}
