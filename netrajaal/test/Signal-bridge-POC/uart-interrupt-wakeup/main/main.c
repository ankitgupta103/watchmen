#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_sleep.h"
#include "esp_log.h"

#define INTERRUPT_PIN       4    // D4 pin for interrupt (GPIO 4)
#define D21_PIN             21   // D21 pin (GPIO 21)
#define D22_PIN             22   // D22 pin (GPIO 22)
#define LED_PIN             2    // LED GPIO pin
#define ACTIVE_TIME_SEC     10   // Stay awake for 10 seconds

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

    // Configure D21 and D22 pins as outputs and set LOW
    gpio_config_t d21_d22_conf = {
        .pin_bit_mask = (1ULL << D21_PIN) | (1ULL << D22_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&d21_d22_conf);
    gpio_set_level(D21_PIN, 0);  // Set D21 LOW
    gpio_set_level(D22_PIN, 0);  // Set D22 LOW

    // Configure D4 pin as input with pull-up (HIGH by default, LOW triggers interrupt)
    gpio_config_t interrupt_conf = {
        .pin_bit_mask = (1ULL << INTERRUPT_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,  // Pull up to HIGH when idle
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE  // We use wakeup, not interrupt
    };
    gpio_config(&interrupt_conf);

    ESP_LOGI(TAG, "GPIO configuration complete:");
    ESP_LOGI(TAG, "  - D4 (GPIO %d): Input with pull-up (HIGH by default)", INTERRUPT_PIN);
    ESP_LOGI(TAG, "  - D21 (GPIO %d): Output LOW", D21_PIN);
    ESP_LOGI(TAG, "  - D22 (GPIO %d): Output LOW", D22_PIN);
    ESP_LOGI(TAG, "  - LED (GPIO %d): Output", LED_PIN);
    vTaskDelay(pdMS_TO_TICKS(100));

    while (1) {
        // Ensure D21 and D22 remain LOW
        gpio_set_level(D21_PIN, 0);
        gpio_set_level(D22_PIN, 0);
        
        // Turn LED OFF before entering sleep
        gpio_set_level(LED_PIN, 0);
        
        // Check pin state before sleep (should be HIGH when idle)
        int pin_state = gpio_get_level(INTERRUPT_PIN);
        ESP_LOGI(TAG, "Entering light sleep... LED OFF. D4 pin state: %d (1=HIGH, 0=LOW)", pin_state);
        
        // Ensure pin is HIGH before sleep - if it's LOW, wait for it to go HIGH
        if (pin_state == 0) {
            ESP_LOGW(TAG, "D4 pin is LOW, waiting for HIGH state...");
            while (gpio_get_level(INTERRUPT_PIN) == 0) {
                vTaskDelay(pdMS_TO_TICKS(10));
            }
            ESP_LOGI(TAG, "D4 pin is now HIGH, ready for sleep");
            vTaskDelay(pdMS_TO_TICKS(50));
        }
        
        // Enable GPIO wakeup on LOW level (when D4 goes from HIGH to LOW)
        esp_err_t ret = gpio_wakeup_enable(INTERRUPT_PIN, GPIO_INTR_LOW_LEVEL);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "Failed to enable GPIO wakeup: %d", ret);
        }
        ESP_ERROR_CHECK(esp_sleep_enable_gpio_wakeup());
        
        // Enter light sleep (will wake when D4 goes LOW)
        ESP_LOGI(TAG, "Entering light sleep mode...");
        esp_light_sleep_start();

        // Check wakeup cause
        esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
        ESP_LOGI(TAG, "Woke up! Cause: %d", cause);
        
        // Check if wakeup was from GPIO
        if (cause == ESP_SLEEP_WAKEUP_GPIO) {
            ESP_LOGI(TAG, "Wakeup from GPIO pin D4 (GPIO %d) - Interrupt received!", INTERRUPT_PIN);
            
            // Turn LED ON when entering active mode
            gpio_set_level(LED_PIN, 1);
            
            // Ensure D21 and D22 remain LOW during active mode
            gpio_set_level(D21_PIN, 0);
            gpio_set_level(D22_PIN, 0);
            
            ESP_LOGI(TAG, "Active mode - LED ON - staying awake for %d seconds...", ACTIVE_TIME_SEC);

            // Stay awake for 10 seconds
            TickType_t wake_time = xTaskGetTickCount();
            while ((xTaskGetTickCount() - wake_time) < pdMS_TO_TICKS(ACTIVE_TIME_SEC * 1000)) {
                // Keep LED ON and D21, D22 LOW during active period
                gpio_set_level(LED_PIN, 1);
                gpio_set_level(D21_PIN, 0);
                gpio_set_level(D22_PIN, 0);
                vTaskDelay(pdMS_TO_TICKS(100));
            }

            ESP_LOGI(TAG, "%d seconds elapsed. Going back to light sleep...", ACTIVE_TIME_SEC);
        } else {
            ESP_LOGW(TAG, "Unexpected wakeup cause: %d", cause);
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
