#include <stdio.h>
#include <string.h>
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sleep.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "esp_pm.h"
#include "soc/rtc.h"

static const char *TAG = "LIGHT_SLEEP_TEST";

// GPIO pin for LED (adjust based on your board)
#define LED_GPIO GPIO_NUM_2

// Sleep duration in microseconds (5 seconds)
#define SLEEP_DURATION_US (5 * 1000000ULL)

/**
 * @brief Configure and enter light sleep mode
 */
void enter_light_sleep(void)
{
    ESP_LOGI(TAG, "Entering light sleep mode for %lld seconds...", SLEEP_DURATION_US / 1000000);
    
    // Configure timer wake-up source
    esp_sleep_enable_timer_wakeup(SLEEP_DURATION_US);
    
    // Get time before sleep
    int64_t time_before_sleep = esp_timer_get_time();
    
    // Enter light sleep
    esp_light_sleep_start();
    
    // Get time after wake-up
    int64_t time_after_sleep = esp_timer_get_time();
    int64_t sleep_duration = time_after_sleep - time_before_sleep;
    
    ESP_LOGI(TAG, "Woke up from light sleep");
    ESP_LOGI(TAG, "Sleep duration: %lld microseconds (%.2f seconds)", 
             sleep_duration, (float)sleep_duration / 1000000.0f);
}

/**
 * @brief Toggle LED to indicate system is active
 */
void toggle_led(void)
{
    static bool led_state = false;
    led_state = !led_state;
    gpio_set_level(LED_GPIO, led_state);
}

/**
 * @brief Initialize GPIO for LED
 */
void init_led(void)
{
    gpio_reset_pin(LED_GPIO);
    gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_level(LED_GPIO, 0);
}

/**
 * @brief Print system information
 */
void print_system_info(void)
{
    ESP_LOGI(TAG, "=== System Information ===");
    rtc_cpu_freq_config_t cpu_freq_config;
    rtc_clk_cpu_freq_get_config(&cpu_freq_config);
    ESP_LOGI(TAG, "CPU Frequency: %" PRIu32 " MHz", cpu_freq_config.freq_mhz);
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "Minimum free heap: %lu bytes", esp_get_minimum_free_heap_size());
    ESP_LOGI(TAG, "==========================");
}

/**
 * @brief Main application entry point
 */
void app_main(void)
{
    // Initialize LED
    init_led();
    
    // Print initial system information
    print_system_info();
    
    ESP_LOGI(TAG, "Starting Light Sleep Mode Test");
    ESP_LOGI(TAG, "This test will cycle between active and light sleep modes");
    ESP_LOGI(TAG, "LED will blink when active, off during sleep");
    
    int cycle_count = 0;
    const int max_cycles = 10; // Run for 10 cycles
    
    while (cycle_count < max_cycles) {
        cycle_count++;
        
        ESP_LOGI(TAG, "\n--- Cycle %d/%d ---", cycle_count, max_cycles);
        
        // Active period: blink LED 3 times
        ESP_LOGI(TAG, "Active period: Blinking LED...");
        for (int i = 0; i < 3; i++) {
            toggle_led();
            vTaskDelay(pdMS_TO_TICKS(200));
            toggle_led();
            vTaskDelay(pdMS_TO_TICKS(200));
        }
        
        // Brief delay before sleep
        vTaskDelay(pdMS_TO_TICKS(500));
        
        // Turn off LED before sleep
        gpio_set_level(LED_GPIO, 0);
        
        // Enter light sleep
        enter_light_sleep();
        
        // Turn on LED after wake-up
        gpio_set_level(LED_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(100));
        gpio_set_level(LED_GPIO, 0);
    }
    
    ESP_LOGI(TAG, "\n=== Test Complete ===");
    ESP_LOGI(TAG, "Completed %d sleep cycles", max_cycles);
    ESP_LOGI(TAG, "System will continue running...");
    
    // Keep system running
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}