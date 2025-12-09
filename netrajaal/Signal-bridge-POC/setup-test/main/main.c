#include <stdio.h>
#include <string.h>
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/task.h"

/*
 * ESP-IDF implementation mirroring reference.py modes:
 * - configure: write persistent settings (0xC0 header)
 * - get_response: read any pending bytes in config mode
 * - read: receive data in normal mode
 * - write: send data in normal mode
 *
 * Select one MODE below.
 */

static const char *TAG = "LORA";

// ===== User selection (pick ONE) =====
// #define MODE_CONFIGURE
// #define MODE_GET_RESPONSE
// #define MODE_READ
#define MODE_WRITE
// =====================================

// Pin definitions (ESP32)
#define UART_PORT       UART_NUM_1
#define UART_TX_PIN     GPIO_NUM_16
#define UART_RX_PIN     GPIO_NUM_17
#define M0_PIN          GPIO_NUM_21
#define M1_PIN          GPIO_NUM_22

// Defaults from reference
#define UART_BAUD_CFG   9600
#define UART_BAUD_DATA  115200

// Hardcoded settings from reference.py
#define FREQ_MHZ        868
#define ADDR            100
#define TARGET_ADDR     200
#define NET_ID          0
#define AIR_SPEED_BITS  0x02      // 2400bps air speed
#define UART_BITS_CFG   0xE0      // 115200 UART per reference (C0 header mode)
#define BUFFER_BITS     0x00      // 240 bytes
#define POWER_BITS      0x00      // 22dBm (per reference script uses +0x00)
#define RSSI_NOISE_BIT  0x20      // enable RSSI noise
#define MODE_BITS       0x43      // mode + RSSI packet bit
#define CRYPT_KEY       0x0000

static inline void set_mode(uint8_t m0, uint8_t m1)
{
    gpio_set_level(M0_PIN, m0);
    gpio_set_level(M1_PIN, m1);
    vTaskDelay(100 / portTICK_PERIOD_MS);
}

static esp_err_t uart_setup(int baud)
{
    uart_driver_delete(UART_PORT);
    vTaskDelay(50 / portTICK_PERIOD_MS);

    uart_config_t cfg = {
        .baud_rate = baud,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB
    };

    if (uart_driver_install(UART_PORT, 2048, 2048, 0, NULL, 0) != ESP_OK) {
        ESP_LOGE(TAG, "UART driver install failed");
        return ESP_FAIL;
    }
    if (uart_param_config(UART_PORT, &cfg) != ESP_OK) {
        ESP_LOGE(TAG, "UART param config failed");
        return ESP_FAIL;
    }
    if (uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN,
                     UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) != ESP_OK) {
        ESP_LOGE(TAG, "UART set pin failed");
        return ESP_FAIL;
    }

    uart_flush_input(UART_PORT);
    uart_flush(UART_PORT);
    return ESP_OK;
}

static void gpio_init_mode(void)
{
    gpio_config_t io = {
        .intr_type = GPIO_INTR_DISABLE,
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = (1ULL << M0_PIN) | (1ULL << M1_PIN),
        .pull_down_en = 0,
        .pull_up_en = 0,
    };
    gpio_config(&io);
}

static void configure_mode(void) __attribute__((unused));
static void configure_mode(void)
{
    ESP_LOGI(TAG, "Configure mode selected");

    gpio_init_mode();
    set_mode(0, 1); // config mode
    uart_setup(UART_BAUD_CFG);

    int freq_offset = FREQ_MHZ - 850; // per reference (868->18)
    uint8_t cfg_reg[12] = {
        0xC0,               // persistent header
        0x00, 0x09,
        (ADDR >> 8) & 0xFF,
        ADDR & 0xFF,
        NET_ID,
        UART_BITS_CFG + AIR_SPEED_BITS,
        BUFFER_BITS + POWER_BITS + RSSI_NOISE_BIT,
        freq_offset,
        MODE_BITS, // includes RSSI bit when needed
        (CRYPT_KEY >> 8) & 0xFF,
        CRYPT_KEY & 0xFF
    };

    uart_flush_input(UART_PORT);
    uart_write_bytes(UART_PORT, (const char *)cfg_reg, sizeof(cfg_reg));
    uart_wait_tx_done(UART_PORT, 200 / portTICK_PERIOD_MS);
    vTaskDelay(300 / portTICK_PERIOD_MS);

    uint8_t resp[32] = {0};
    int len = uart_read_bytes(UART_PORT, resp, sizeof(resp), 500 / portTICK_PERIOD_MS);
    if (len > 0) {
        ESP_LOGI(TAG, "Response (%d bytes):", len);
        for (int i = 0; i < len; i++) ESP_LOGI(TAG, "  [%d]=0x%02X", i, resp[i]);
        if (resp[0] == 0xC1) ESP_LOGI(TAG, "Configuration successful");
        else ESP_LOGW(TAG, "Unexpected response");
    } else {
        ESP_LOGW(TAG, "No response");
    }

    // reopen at 115200 in config mode (per reference)
    uart_setup(UART_BAUD_DATA);
    set_mode(0, 1);
    vTaskDelay(500 / portTICK_PERIOD_MS);

    // exit config mode
    set_mode(0, 0);
    ESP_LOGI(TAG, "Configure mode done");
}

static void get_response_mode(void) __attribute__((unused));
static void get_response_mode(void)
{
    ESP_LOGI(TAG, "Get-response mode");
    gpio_init_mode();
    set_mode(0, 1);
    uart_setup(UART_BAUD_DATA);
    vTaskDelay(200 / portTICK_PERIOD_MS);

    uint8_t buf[64];
    int len = uart_read_bytes(UART_PORT, buf, sizeof(buf), 2000 / portTICK_PERIOD_MS);
    if (len > 0) {
        ESP_LOGI(TAG, "Raw response (%d bytes):", len);
        for (int i = 0; i < len; i++) ESP_LOGI(TAG, "  [%d]=0x%02X", i, buf[i]);
    } else {
        ESP_LOGW(TAG, "No response available");
    }
    set_mode(0, 0);
}

static void read_mode(void) __attribute__((unused));
static void read_mode(void)
{
    ESP_LOGI(TAG, "Read mode");
    gpio_init_mode();
    set_mode(0, 0);  // Normal mode
    uart_setup(UART_BAUD_DATA);
    
    // Flush any stale data and let UART stabilize
    uart_flush_input(UART_PORT);
    uart_flush(UART_PORT);
    vTaskDelay(200 / portTICK_PERIOD_MS);
    
    ESP_LOGI(TAG, "UART initialized, starting to read from buffer...");

    uint8_t line[256];
    while (1) {
        // Check if data is available in UART buffer
        size_t buffered_len = 0;
        uart_get_buffered_data_len(UART_PORT, &buffered_len);
        
        if (buffered_len > 0) {
            ESP_LOGI(TAG, "Data available in buffer: %d bytes", buffered_len);
            // Read available data
            int available = uart_read_bytes(UART_PORT, line, sizeof(line) - 1, 100 / portTICK_PERIOD_MS);
            if (available > 0) {
                line[available] = 0;
                ESP_LOGI(TAG, "Raw data (%d bytes):", available);
                for (int i = 0; i < available; i++) {
                    ESP_LOGI(TAG, "  [%d]=0x%02X", i, line[i]);
                }
                if (available >= 3) {
                    ESP_LOGI(TAG, "Message: %s", (char *)&line[3]);
                }
                // Continue reading in case there's more data
                continue;
            }
        }
        
        // Also try direct read in case buffered_len doesn't catch it
        int available = uart_read_bytes(UART_PORT, line, sizeof(line) - 1, 50 / portTICK_PERIOD_MS);
        if (available > 0) {
            line[available] = 0;
            ESP_LOGI(TAG, "Raw data (%d bytes):", available);
            for (int i = 0; i < available; i++) {
                ESP_LOGI(TAG, "  [%d]=0x%02X", i, line[i]);
            }
            if (available >= 3) {
                ESP_LOGI(TAG, "Message: %s", (char *)&line[3]);
            }
            // Continue reading in case there's more data
        }
        
        vTaskDelay(50 / portTICK_PERIOD_MS);
    }
}

static void write_mode(void) __attribute__((unused));
static void write_mode(void)
{
    ESP_LOGI(TAG, "Write mode");
    gpio_init_mode();
    set_mode(0, 0);
    uart_setup(UART_BAUD_DATA);

    int freq_offset = FREQ_MHZ - 850;
    const char *msg = "Hello from LoRa!";
    uint8_t packet[256];
    int idx = 0;
    packet[idx++] = (TARGET_ADDR >> 8) & 0xFF;
    packet[idx++] = TARGET_ADDR & 0xFF;
    packet[idx++] = freq_offset;
    packet[idx++] = (ADDR >> 8) & 0xFF;
    packet[idx++] = ADDR & 0xFF;
    packet[idx++] = freq_offset;
    memcpy(&packet[idx], msg, strlen(msg));
    idx += strlen(msg);
    packet[idx++] = '\n';

    while (1) {
        uart_write_bytes(UART_PORT, (const char *)packet, idx);
        uart_wait_tx_done(UART_PORT, 200 / portTICK_PERIOD_MS);
        ESP_LOGI(TAG, "Sent %d bytes to address %d", (int)strlen(msg), TARGET_ADDR);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }

    // uart_write_bytes(UART_PORT, (const char *)packet, idx);
    // uart_wait_tx_done(UART_PORT, 200 / portTICK_PERIOD_MS);
    // ESP_LOGI(TAG, "Sent %d bytes to address %d", (int)strlen(msg), TARGET_ADDR);
}

void app_main(void)
{
    ESP_LOGI(TAG, "LoRa ESP-IDF port of reference.py");

#if defined(MODE_CONFIGURE)
    configure_mode();
#elif defined(MODE_GET_RESPONSE)
    get_response_mode();
#elif defined(MODE_READ)
    read_mode();
#elif defined(MODE_WRITE)
    write_mode();
#else
#error "Select one MODE_ option at top of file"
#endif
}
