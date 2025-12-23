#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_sleep.h"

// ============================================================================
// CONFIGURATION CONSTANTS
// ============================================================================

#define TAG "UART_READER"              // Logging tag

// Mode selection: READ_MODE or WRITE_MODE
#define READ_MODE  0
#define WRITE_MODE 1
#define CURRENT_MODE READ_MODE          // Change this to switch modes

// GPIO pin definitions
#define PIN_D21 21                     // GPIO21 - keep LOW
#define PIN_D22 22                     // GPIO22 - keep LOW
#define PIN_WAKE 4                     // GPIO4 (D4) - wake-up pin (HIGH normally, LOW to wake)
#define LED_PIN 2                      // On-board LED pin
#define LED_BLINK_TIME_MS 10           // LED blink duration

// UART2 pin definitions
#define UART2_RX_PIN 16                // GPIO16 - UART2 RX
#define UART2_TX_PIN 17                // GPIO17 - UART2 TX

// UART configuration
#define UART2_NUM UART_NUM_2
#define UART2_BAUD_RATE 115200
#define UART_RX_BUF_SIZE 512           // Application buffer size
#define UART_DRIVER_BUF_SIZE 2048      // UART driver buffer (handles 250+ byte packets)
#define PACKET_TIMEOUT_MS 50           // Wait time after last byte to consider packet complete

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

static TickType_t ledOffTime = 0;      // Timestamp when LED should turn off
static uint8_t uartRxBuf[UART_RX_BUF_SIZE];  // Buffer for received UART data

// UART write mode variables
static uint16_t target_addr = 200;     // Target address (default: 200)
static uint16_t own_addr = 100;        // Own address (default: 100)
static int freq = 868;                  // Frequency in MHz
static int freq_offset = 0;             // Frequency offset (freq - 850)
static int message_counter = 0;        // Message counter

// ============================================================================
// GPIO FUNCTIONS
// ============================================================================

/**
 * @brief Configure a GPIO pin as output and set it LOW
 */
static void gpio_set_output_low(int pin)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << pin),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));
    gpio_set_level(pin, 0);
}

/**
 * @brief Initialize GPIO pins D21, D22, and LED
 */
static void init_gpio_pins(void)
{
    gpio_set_output_low(PIN_D21);  // Set D21 LOW
    gpio_set_output_low(PIN_D22);  // Set D22 LOW
    gpio_set_output_low(LED_PIN);   // Set LED LOW initially
    
    ESP_LOGI(TAG, "GPIO21, GPIO22, and LED initialized");
}

/**
 * @brief Configure GPIO4 (D4) as wake-up source
 * Pin is normally HIGH, wakes ESP32 when it goes LOW
 */
static void init_wakeup_gpio(void)
{
    // Configure GPIO4 as input (external source keeps it HIGH)
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_WAKE),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));

    // Enable wake-up when GPIO4 goes LOW
    ESP_ERROR_CHECK(esp_sleep_enable_ext0_wakeup(GPIO_NUM_4, 0));
    
    ESP_LOGI(TAG, "Wake-up GPIO (D4) configured - will wake on LOW");
}

// ============================================================================
// LED FUNCTIONS
// ============================================================================

/**
 * @brief Turn LED ON and set timeout for auto-off
 */
static void led_blink(void)
{
    gpio_set_level(LED_PIN, 1);
    ledOffTime = xTaskGetTickCount() + pdMS_TO_TICKS(LED_BLINK_TIME_MS);
}

/**
 * @brief Turn LED OFF if timeout has expired
 */
static void led_update(void)
{
    if (xTaskGetTickCount() > ledOffTime) {
        gpio_set_level(LED_PIN, 0);
    }
}

// ============================================================================
// UART FUNCTIONS
// ============================================================================

/**
 * @brief Initialize UART2 for receiving data
 */
static void init_uart2(void)
{
    // Configure UART parameters: 115200 baud, 8N1
    uart_config_t uart_config = {
        .baud_rate = UART2_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    
    // Install UART driver with large RX buffer for 250+ byte packets
    // TX buffer: 512 bytes for write mode
    ESP_ERROR_CHECK(uart_driver_install(UART2_NUM, UART_DRIVER_BUF_SIZE, 512, 0, NULL, 0));
    
    // Apply UART configuration
    ESP_ERROR_CHECK(uart_param_config(UART2_NUM, &uart_config));
    
    // Set UART pins (TX, RX)
    ESP_ERROR_CHECK(uart_set_pin(UART2_NUM, UART2_TX_PIN, UART2_RX_PIN, 
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    
    ESP_LOGI(TAG, "UART2 initialized @ %d baud (RX=GPIO%d, TX=GPIO%d)", 
             UART2_BAUD_RATE, UART2_RX_PIN, UART2_TX_PIN);
}

/**
 * @brief Read a complete packet from UART2
 * Waits for first byte, then accumulates all data until timeout
 * @param buffer Buffer to store packet
 * @param buffer_size Maximum buffer size
 * @return Number of bytes read (0 if no data)
 */
static int uart_read_packet(uint8_t *buffer, size_t buffer_size)
{
    size_t total_read = 0;
    TickType_t last_byte_time = 0;
    bool packet_started = false;
    
    // Wait for first byte (100ms timeout)
    int len = uart_read_bytes(UART2_NUM, buffer, 1, pdMS_TO_TICKS(100));
    if (len <= 0) {
        return 0;  // No data available
    }
    
    total_read = len;
    last_byte_time = xTaskGetTickCount();
    packet_started = true;
    
    // Continue reading until no data arrives for PACKET_TIMEOUT_MS
    while (total_read < buffer_size - 1) {
        size_t available = 0;
        uart_get_buffered_data_len(UART2_NUM, &available);
        
        if (available > 0) {
            // Read all available data
            size_t to_read = (available < (buffer_size - total_read - 1)) ? 
                             available : (buffer_size - total_read - 1);
            
            len = uart_read_bytes(UART2_NUM, buffer + total_read, to_read, pdMS_TO_TICKS(10));
            
            if (len > 0) {
                total_read += len;
                last_byte_time = xTaskGetTickCount();  // Update last byte time
            }
        } else {
            // No data available - check if timeout expired
            TickType_t now = xTaskGetTickCount();
            if (packet_started && (now - last_byte_time) >= pdMS_TO_TICKS(PACKET_TIMEOUT_MS)) {
                break;  // Packet complete
            }
            vTaskDelay(pdMS_TO_TICKS(1));  // Small delay before checking again
        }
    }
    
    return total_read;
}

/**
 * @brief Write data packet to UART2
 * Packet format: [target_addr_high, target_addr_low, freq_offset, 
 *                 own_addr_high, own_addr_low, freq_offset, message, \n]
 * @param message Message data to send
 * @param message_len Length of message
 * @return Number of bytes written
 */
static int uart_write_packet(const uint8_t *message, size_t message_len)
{
    uint8_t packet[256];  // Max packet size
    int idx = 0;
    
    // Build packet header
    packet[idx++] = (target_addr >> 8) & 0xFF;      // target_addr high byte
    packet[idx++] = target_addr & 0xFF;             // target_addr low byte
    packet[idx++] = freq_offset & 0xFF;             // freq_offset
    packet[idx++] = (own_addr >> 8) & 0xFF;         // own_addr high byte
    packet[idx++] = own_addr & 0xFF;                 // own_addr low byte
    packet[idx++] = freq_offset & 0xFF;             // freq_offset (again)
    
    // Add message
    if (message_len > 0 && idx + message_len < sizeof(packet) - 1) {
        memcpy(packet + idx, message, message_len);
        idx += message_len;
    }
    
    // Ensure newline terminator
    if (idx == 0 || packet[idx - 1] != 0x0A) {
        packet[idx++] = 0x0A;  // '\n'
    }
    
    // Write to UART
    int bytes_written = uart_write_bytes(UART2_NUM, packet, idx);
    
    ESP_LOGI(TAG, "Wrote packet: %d bytes (target=0x%04X, own=0x%04X, freq_offset=%d)", 
             bytes_written, target_addr, own_addr, freq_offset);
    
    return bytes_written;
}

/**
 * @brief Print received packet in both ASCII and HEX format
 */
static void print_packet(uint8_t *data, int length)
{
    // Print ASCII representation
    printf("[Serial2 RX ASCII] ");
    for (int i = 0; i < length; i++) {
        printf("%c", data[i]);
    }
    printf("\n");

    // Print HEX representation
    printf("[Serial2 RX HEX] ");
    for (int i = 0; i < length; i++) {
        printf("%02X ", data[i]);
    }
    printf("\n");
    
    ESP_LOGI(TAG, "Received packet: %d bytes", length);
}

// ============================================================================
// MAIN TASK
// ============================================================================

/**
 * @brief UART write task - sends data packets periodically
 */
static void uart_write_task(void *pvParameters)
{
    ESP_LOGI(TAG, "UART write task started");
    
    // Ensure D21 and D22 are LOW in write mode
    gpio_set_level(PIN_D21, 0);
    gpio_set_level(PIN_D22, 0);
    
    while (1) {
        // Build message with counter
        char message[128];
        int msg_len = snprintf(message, sizeof(message), 
                              "Hello from LoRa! my name is anand and I am from heaven athat my meessage will not reach the target %d", 
                              message_counter);
        
        if (msg_len > 0 && msg_len < sizeof(message)) {
            // Write packet to UART
            uart_write_packet((uint8_t *)message, msg_len);
            
            // Increment counter
            message_counter++;
            
            // Blink LED to indicate data sent
            led_blink();
        }
        
        // Wait 800ms before next transmission
        vTaskDelay(pdMS_TO_TICKS(350));
    }
}

/**
 * @brief Main loop task - handles UART reading and LED control
 */
static void main_loop_task(void *pvParameters)
{
    ESP_LOGI(TAG, "UART reading task started");
    
    while (1) {
        // Update LED (turn off if timeout expired)
        led_update();
        
        // Read complete packet from UART2
        int packet_len = uart_read_packet(uartRxBuf, UART_RX_BUF_SIZE);
        
        if (packet_len > 0) {
            // Option 1: Print as HEX using ESP-IDF logging (recommended)
            ESP_LOG_BUFFER_HEX(TAG, uartRxBuf, packet_len);
            
            // Option 2: Print as characters (only printable chars shown)
            // ESP_LOG_BUFFER_CHAR(TAG, uartRxBuf, packet_len);
            
            // Option 3: Create null-terminated string for %s (if needed)
            // char temp_buf[UART_RX_BUF_SIZE + 1];
            // memcpy(temp_buf, uartRxBuf, packet_len);
            // temp_buf[packet_len] = '\0';
            // ESP_LOGI(TAG, "Data: %s", temp_buf);
            
            // Print packet in both formats (existing function)
            print_packet(uartRxBuf, packet_len);
            
            // Blink LED to indicate data received
            led_blink();
        }
        
        // Small delay to prevent CPU spinning
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

// ============================================================================
// APPLICATION ENTRY POINT
// ============================================================================

/**
 * @brief Main application entry point
 * Flow: Initialize -> (Read: Sleep -> Wake -> Read) or (Write: Start Writing)
 */
void app_main(void)
{
    ESP_LOGI(TAG, "=== ESP32 UART Application ===");
    
    // Step 1: Initialize GPIO pins (D21, D22 LOW, LED)
    init_gpio_pins();
    
    // Step 2: Initialize UART2
    init_uart2();
    
    // Step 3: Calculate frequency offset
    freq_offset = freq - 850;
    ESP_LOGI(TAG, "Config: target_addr=0x%04X, own_addr=0x%04X, freq=%d, freq_offset=%d", 
             target_addr, own_addr, freq, freq_offset);
    
#if CURRENT_MODE == READ_MODE
    // ========== READ MODE ==========
    ESP_LOGI(TAG, "Mode: READ - Entering light sleep. Wake when D4 (GPIO4) goes LOW...");
    
    // Configure wake-up GPIO (D4) and enter light sleep
    init_wakeup_gpio();
    esp_light_sleep_start();  // Sleep until D4 goes LOW
    
    // Woke up - check wake reason
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    ESP_LOGI(TAG, "Woke from sleep (cause: %d)", cause);
    
    // Start UART reading task
    xTaskCreate(main_loop_task, "uart_reader", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "UART reading task started");
    
#elif CURRENT_MODE == WRITE_MODE
    // ========== WRITE MODE ==========
    ESP_LOGI(TAG, "Mode: WRITE - Starting UART transmission");
    
    // Ensure D21 and D22 are LOW in write mode
    gpio_set_level(PIN_D21, 0);
    gpio_set_level(PIN_D22, 0);
    
    // Start UART write task
    xTaskCreate(uart_write_task, "uart_writer", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "UART write task started");
    
#else
    #error "Invalid CURRENT_MODE - must be READ_MODE or WRITE_MODE"
#endif
}
