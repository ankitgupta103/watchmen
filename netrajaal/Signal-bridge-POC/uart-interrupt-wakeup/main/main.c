#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_sleep.h"
#include "esp_log.h"

#define UART_EXT            UART_NUM_1
#define UART_EXT_RX_PIN     16
#define UART_EXT_TX_PIN     17
#define UART_BAUD_RATE      115200
#define UART_RX_BUF_SIZE    1024
#define WAKEUP_THRESHOLD    1    // Wake up on 1 RX edge
#define ACTIVE_TIME_SEC     10   // Stay awake for 10 seconds
#define LED_PIN             2    // LED GPIO pin
#define M0_PIN              21
#define M1_PIN              22

static const char *TAG = "UART_SLEEP";

void app_main(void)
{
    // Configure UART
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };

    ESP_ERROR_CHECK(uart_driver_install(UART_EXT, UART_RX_BUF_SIZE, 0, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_EXT, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_EXT, UART_EXT_TX_PIN, UART_EXT_RX_PIN,
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    // Configure LED GPIO
    gpio_config_t led_conf = {
        .pin_bit_mask = (1ULL << LED_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&led_conf);
    gpio_set_level(LED_PIN, 0);  // LED OFF initially

    // Configure M0 and M1 pins as outputs and set LOW (for module read/write mode)
    gpio_config_t m0_m1_conf = {
        .pin_bit_mask = (1ULL << M0_PIN) | (1ULL << M1_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&m0_m1_conf);
    gpio_set_level(M0_PIN, 0);  // Set M0 LOW
    gpio_set_level(M1_PIN, 0);  // Set M1 LOW

    // Configure UART wakeup source
    ESP_ERROR_CHECK(esp_sleep_enable_uart_wakeup(UART_EXT));
    uart_set_wakeup_threshold(UART_EXT, WAKEUP_THRESHOLD);

    ESP_LOGI(TAG, "UART configured. Entering light sleep mode...");

    while (1) {
        // Turn LED OFF before entering sleep
        gpio_set_level(LED_PIN, 0);
        
        // Enter light sleep (will wake on UART RX)
        esp_light_sleep_start();

        // Check wakeup reason
        esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
        if (cause == ESP_SLEEP_WAKEUP_UART) {
            ESP_LOGI(TAG, "Woke up from UART interrupt");
            
            // Turn LED ON when active
            gpio_set_level(LED_PIN, 1);

            // Read any available data
            uint8_t buf[256];
            int len = uart_read_bytes(UART_EXT, buf, sizeof(buf), 0);
            if (len > 0) {
                ESP_LOGI(TAG, "Received %d bytes", len);
                // Process your data here
            }

            // Stay awake for 10 seconds, reading data periodically
            TickType_t wake_time = xTaskGetTickCount();
            while ((xTaskGetTickCount() - wake_time) < pdMS_TO_TICKS(ACTIVE_TIME_SEC * 1000)) {
                len = uart_read_bytes(UART_EXT, buf, sizeof(buf), pdMS_TO_TICKS(100));
                if (len > 0) {
                    ESP_LOGI(TAG, "Received %d bytes", len);
                    // Process your data here
                }
                vTaskDelay(pdMS_TO_TICKS(100));
            }

            ESP_LOGI(TAG, "10 seconds elapsed. Going back to sleep...");
        }
    }
}
