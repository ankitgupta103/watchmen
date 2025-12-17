#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_sleep.h"
#include "esp_log.h"

#define RX_PIN              16   // GPIO pin for RX data
#define ACTIVE_TIME_SEC     10   // Stay awake for 10 seconds
#define LED_PIN             2    // LED GPIO pin
#define M0_PIN              21
#define M1_PIN              22

static const char *TAG = "GPIO_SLEEP";

void app_main(void)
{
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

    // Configure M0 and M1 pins as outputs and set LOW
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

    // Configure RX pin as input with pull-up (idle HIGH, data LOW)
    gpio_config_t rx_conf = {
        .pin_bit_mask = (1ULL << RX_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,  // Pull up to HIGH when idle
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE  // We use wakeup, not interrupt
    };
    gpio_config(&rx_conf);

    // Enable GPIO wakeup - try both LOW and HIGH level to catch any change
    ESP_ERROR_CHECK(gpio_wakeup_enable(RX_PIN, GPIO_INTR_LOW_LEVEL));
    ESP_ERROR_CHECK(esp_sleep_enable_gpio_wakeup());
    
    ESP_LOGI(TAG, "GPIO wakeup configured on pin %d. Entering light sleep...", RX_PIN);
    vTaskDelay(pdMS_TO_TICKS(100));

    while (1) {
        // Turn LED OFF before entering sleep
        gpio_set_level(LED_PIN, 0);
        
        // Check and log pin state before sleep (should be HIGH when idle)
        int pin_state = gpio_get_level(RX_PIN);
        ESP_LOGI(TAG, "Entering light sleep... LED OFF. RX pin state: %d (1=HIGH/idle, 0=LOW/data)", pin_state);
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(100));  // Wait longer to ensure pin is stable
        
        // Ensure pin is HIGH (idle) before sleep - if it's LOW, wait for it to go HIGH
        if (pin_state == 0) {
            ESP_LOGW(TAG, "Pin is LOW, waiting for HIGH (idle) state...");
            while (gpio_get_level(RX_PIN) == 0) {
                vTaskDelay(pdMS_TO_TICKS(10));
            }
            ESP_LOGI(TAG, "Pin is now HIGH (idle), ready for sleep");
            vTaskDelay(pdMS_TO_TICKS(50));
        }
        
        // Re-enable GPIO wakeup before each sleep (critical!)
        esp_err_t ret = gpio_wakeup_enable(RX_PIN, GPIO_INTR_LOW_LEVEL);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Failed to enable GPIO wakeup: %d", ret);
        }
        
        // Enter light sleep (will wake on GPIO LOW on RX pin)
        esp_light_sleep_start();

        // Check wakeup cause
        esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
        ESP_LOGI(TAG, "Woke up! Cause: %d", cause);
        
        // Check if wakeup was from GPIO
        if (cause == ESP_SLEEP_WAKEUP_GPIO) {
            ESP_LOGI(TAG, "Wakeup from GPIO pin %d (data received)", RX_PIN);
            
            // Turn LED ON when active
            gpio_set_level(LED_PIN, 1);
            ESP_LOGI(TAG, "LED ON - Active mode");

            // Stay awake for 10 seconds
            TickType_t wake_time = xTaskGetTickCount();
            ESP_LOGI(TAG, "Staying awake for %d seconds...", ACTIVE_TIME_SEC);
            while ((xTaskGetTickCount() - wake_time) < pdMS_TO_TICKS(ACTIVE_TIME_SEC * 1000)) {
                // Check pin state periodically
                int pin_state = gpio_get_level(RX_PIN);
                vTaskDelay(pdMS_TO_TICKS(100));
            }

            ESP_LOGI(TAG, "10 seconds elapsed. Going back to sleep...");
        } else {
            ESP_LOGW(TAG, "Unexpected wakeup cause: %d", cause);
            gpio_set_level(LED_PIN, 1);
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
