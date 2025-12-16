#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_sleep.h"
#include "esp_log.h"

// ============================================================================
// Configuration
// ============================================================================
#define SENSOR_GPIO       GPIO_NUM_12  // D12 pin
#define LED_GPIO          GPIO_NUM_2   // LED pin (GPIO2 is built-in LED on most ESP32)
#define WAKE_TIME_SEC     5            // Stay awake for 5 seconds
#define SIGNAL_CHECK_MS   100          // Check signal every 100ms
#define BLINK_ON_MS       100          // LED ON time for blink
#define BLINK_OFF_MS      100          // LED OFF time for blink
#define BLINK_COUNT       3            // Number of blinks

static const char *TAG = "SENSOR_WAKE";

// ============================================================================
// GPIO Configuration Structure
// ============================================================================
static gpio_config_t sensor_gpio_cfg = {
    .intr_type = GPIO_INTR_DISABLE,
    .mode = GPIO_MODE_INPUT,
    .pin_bit_mask = (1ULL << SENSOR_GPIO),
    .pull_down_en = GPIO_PULLDOWN_ENABLE,
    .pull_up_en = GPIO_PULLUP_DISABLE,
};

// ============================================================================
// Function: Initialize GPIO for sensor input
// ============================================================================
static void init_sensor_gpio(void)
{
    gpio_config(&sensor_gpio_cfg);
    ESP_LOGI(TAG, "GPIO%d configured as input with pull-down", SENSOR_GPIO);
}

// ============================================================================
// Function: Initialize LED GPIO as output
// ============================================================================
static void init_led_gpio(void)
{
    gpio_config_t led_conf = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << LED_GPIO),
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
    };
    gpio_config(&led_conf);
    gpio_set_level(LED_GPIO, 0); // Start with LED OFF
    ESP_LOGI(TAG, "GPIO%d configured as LED output", LED_GPIO);
}

// ============================================================================
// Function: Turn LED ON
// ============================================================================
static void led_on(void)
{
    gpio_set_level(LED_GPIO, 1);
}

// ============================================================================
// Function: Turn LED OFF
// ============================================================================
static void led_off(void)
{
    gpio_set_level(LED_GPIO, 0);
}

// ============================================================================
// Function: Blink LED 3 times fast
// ============================================================================
static void blink_led_fast(void)
{
    for (int i = 0; i < BLINK_COUNT; i++) {
        led_on();
        vTaskDelay(pdMS_TO_TICKS(BLINK_ON_MS));
        led_off();
        vTaskDelay(pdMS_TO_TICKS(BLINK_OFF_MS));
    }
}

// ============================================================================
// Function: Configure light sleep with GPIO wakeup
// ============================================================================
static void configure_light_sleep(void)
{
    // Disable previous wakeup sources
    esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_GPIO);
    
    // Enable GPIO wakeup
    esp_sleep_enable_gpio_wakeup();
    gpio_wakeup_enable(SENSOR_GPIO, GPIO_INTR_HIGH_LEVEL);
}

// ============================================================================
// Function: Wait for sensor signal to go LOW
// ============================================================================
static void wait_for_signal_low(void)
{
    ESP_LOGI(TAG, "Waiting for sensor to go LOW before sleeping...");
    while (gpio_get_level(SENSOR_GPIO) == 1) {
        vTaskDelay(pdMS_TO_TICKS(SIGNAL_CHECK_MS));
    }
    ESP_LOGI(TAG, "Sensor is LOW - Ready to sleep");
}

// ============================================================================
// Function: Check if wakeup was due to GPIO HIGH
// ============================================================================
static bool is_gpio_wakeup_high(void)
{
    // Small delay for GPIO to stabilize after wakeup
    vTaskDelay(pdMS_TO_TICKS(50));
    
    // Check wakeup cause
    esp_sleep_wakeup_cause_t wakeup_cause = esp_sleep_get_wakeup_cause();
    
    if (wakeup_cause == ESP_SLEEP_WAKEUP_GPIO) {
        // Verify GPIO is actually HIGH
        int gpio_level = gpio_get_level(SENSOR_GPIO);
        ESP_LOGI(TAG, "Wakeup cause: GPIO, GPIO level: %d", gpio_level);
        return (gpio_level == 1);
    } else {
        ESP_LOGW(TAG, "Wakeup cause: %d (not GPIO)", wakeup_cause);
        return false;
    }
}

// ============================================================================
// Main Application Entry Point
// ============================================================================
void app_main(void)
{
    // Initialize sensor GPIO
    init_sensor_gpio();
    
    // Initialize LED GPIO
    init_led_gpio();
    
    ESP_LOGI(TAG, "Starting sensor wake application");
    
    // Wait for sensor to be LOW before first sleep
    wait_for_signal_low();
    
    // Main loop: Sleep -> Wake -> Blink -> ON -> Blink -> OFF -> Sleep
    while (1) {
        // ========================================================================
        // SLEEP MODE: LED OFF
        // ========================================================================
        // Turn LED OFF before entering light sleep
        led_off();
        
        // Configure and enter light sleep
        configure_light_sleep();
        ESP_LOGI(TAG, "Entering light sleep mode... GPIO12 level: %d", gpio_get_level(SENSOR_GPIO));
        esp_light_sleep_start();
        
        // Check if wakeup was due to GPIO HIGH
        if (is_gpio_wakeup_high()) {
            ESP_LOGI(TAG, "Valid GPIO HIGH wakeup detected - Processing...");
            
            // Blink LED 3 times fast (wake indication)
            blink_led_fast();
            
            // ========================================================================
            // ACTIVE MODE: LED ON
            // ========================================================================
            // Turn LED ON and keep it ON during active mode (normal operation)
            led_on();
            
            // Stay awake for configured time with LED ON
            ESP_LOGI(TAG, "Staying awake for %d seconds (LED ON)", WAKE_TIME_SEC);
            vTaskDelay(pdMS_TO_TICKS(WAKE_TIME_SEC * 1000));
            
            // Blink LED 3 times fast (sleep indication)
            ESP_LOGI(TAG, "Preparing to sleep...");
            blink_led_fast();
            
            // Turn LED OFF before sleeping
            led_off();
            
            // Wait for signal to go LOW before sleeping again
            wait_for_signal_low();
        } else {
            // Invalid wakeup - go back to sleep immediately
            ESP_LOGW(TAG, "Invalid wakeup - GPIO not HIGH. Going back to sleep...");
            led_off();
            // Small delay before going back to sleep
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
