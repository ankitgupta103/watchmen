#include <stdio.h>
#include <string.h>
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "UART_BRIDGE";

// Pin definitions
#define PIN_D21           GPIO_NUM_21
#define PIN_D22           GPIO_NUM_22
#define UART2_RX_PIN      GPIO_NUM_16  // External device TX -> ESP32 RX (GPIO16)
#define UART2_TX_PIN      GPIO_NUM_17  // External device RX <- ESP32 TX (GPIO17)
#define LED_PIN           GPIO_NUM_2   // On-board LED on most ESP32 dev boards

#define UART_PORT         UART_NUM_1
#define UART_BAUD_RATE    115200
#define UART_TIMEOUT_MS   2000
#define LED_BLINK_TIME_MS 200

static TickType_t led_off_time = 0;

static void blink_led(void)
{
    gpio_set_level(LED_PIN, 1);
    led_off_time = xTaskGetTickCount() + pdMS_TO_TICKS(LED_BLINK_TIME_MS);
    ESP_LOGI(TAG, "LED blinked - will turn off in %d ms", LED_BLINK_TIME_MS);
}

static void gpio_init(void)
{
    // Configure GPIO D21, D22, and LED as outputs
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << PIN_D21) | (1ULL << PIN_D22) | (1ULL << LED_PIN),
        .pull_down_en = 0,
        .pull_up_en = 0,
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));
    
    // Set D21 and D22 to LOW
    gpio_set_level(PIN_D21, 0);
    gpio_set_level(PIN_D22, 0);
    gpio_set_level(LED_PIN, 0);
    
    ESP_LOGI(TAG, "GPIO D21 and D22 set to LOW (GND)");
}

static void uart_init(void)
{
    // Configure UART parameters
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };

    // Install UART driver
    ESP_ERROR_CHECK(uart_driver_install(UART_PORT, 1024, 1024, 0, NULL, 0));
    
    // Configure UART parameters
    ESP_ERROR_CHECK(uart_param_config(UART_PORT, &uart_config));
    
    // Set UART pins (TX=17, RX=16)
    ESP_ERROR_CHECK(uart_set_pin(UART_PORT, UART2_TX_PIN, UART2_RX_PIN, 
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    ESP_LOGI(TAG, "Serial2 started @%d, timeout=%d ms", UART_BAUD_RATE, UART_TIMEOUT_MS);
}

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32 UART (Serial2) example with LED blink activity");
    
    // Initialize GPIO
    gpio_init();
    
    // Initialize UART
    uart_init();
    
    ESP_LOGI(TAG, "Setup complete! Bridging UART <-> USB Serial");

    uint8_t uart_rx_buf[256];
    char usb_rx_buf[256];
    
    while (1) {
        // Turn LED OFF when timeout expires
        if (xTaskGetTickCount() > led_off_time) {
            gpio_set_level(LED_PIN, 0);
        }

        // UART -> USB (Serial Monitor)
        // Check if data is available first
        size_t buffered_len = 0;
        uart_get_buffered_data_len(UART_PORT, &buffered_len);
        
        if (buffered_len > 0) {
            int len = uart_read_bytes(UART_PORT, uart_rx_buf, sizeof(uart_rx_buf) - 1, 
                                      pdMS_TO_TICKS(100));
            if (len > 0) {
                uart_rx_buf[len] = '\0';  // Null terminate
                ESP_LOGI(TAG, "[UART -> USB] Received %d bytes: %s", len, uart_rx_buf);
                blink_led();  // Blink LED on RX activity
            }
        } else {
            // Also try direct read with short timeout
            int len = uart_read_bytes(UART_PORT, uart_rx_buf, sizeof(uart_rx_buf) - 1, 
                                      pdMS_TO_TICKS(10));
            if (len > 0) {
                uart_rx_buf[len] = '\0';  // Null terminate
                ESP_LOGI(TAG, "[UART -> USB] Received %d bytes: %s", len, uart_rx_buf);
                blink_led();  // Blink LED on RX activity
            }
        }

        // USB -> UART (from Serial Monitor)
        // Read from stdin (USB serial)
        if (fgets(usb_rx_buf, sizeof(usb_rx_buf), stdin) != NULL) {
            // Remove newline if present
            size_t usb_len = strlen(usb_rx_buf);
            if (usb_len > 0 && usb_rx_buf[usb_len - 1] == '\n') {
                usb_rx_buf[usb_len - 1] = '\0';
                usb_len--;
            }
            
            if (usb_len > 0) {
                // Send to UART
                uart_write_bytes(UART_PORT, usb_rx_buf, usb_len);
                uart_write_bytes(UART_PORT, "\n", 1);
                ESP_LOGI(TAG, "[USB -> UART] %s", usb_rx_buf);
                blink_led();  // Blink LED on TX activity
            }
        }

        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
