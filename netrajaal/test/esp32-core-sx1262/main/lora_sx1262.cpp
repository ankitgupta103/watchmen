/**
 * @file lora_sx1262.c
 * @brief SX1262 LoRa module driver using RadioLib for ESP-IDF
 * 
 * This is a simplified wrapper around RadioLib that provides the same API
 * but uses RadioLib's proven SX1262 implementation. This directly reuses
 * the logic from the LoRa-Test reference implementation.
 */

#include "lora_sx1262.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include <string.h>

// RadioLib includes - we'll use Arduino as ESP-IDF component
#include "Arduino.h"
#include "SPI.h"
#include "RadioLib.h"

static const char *TAG = "LORA_SX1262";

// RadioLib objects
static Module *radio_module = NULL;
static SX1262 *radio = NULL;
static TaskHandle_t dio1_task_handle = NULL;

// Configuration storage
static lora_sx1262_pins_t stored_pins;
static lora_sx1262_config_t stored_config;
static bool initialized = false;

// Bandwidth lookup table (from RadioLib)
static const float bandwidth_values[] = {7.8f, 10.4f, 15.6f, 20.8f, 31.25f, 41.7f, 62.5f, 125.0f, 250.0f, 500.0f};

// Last received packet stats
static float last_rssi = 0.0f;
static float last_snr = 0.0f;
static float last_freq_error = 0.0f;

/**
 * @brief DIO1 interrupt handler wrapper (IRAM)
 * 
 * RadioLib's setDio1Action expects a function pointer with no arguments.
 * This wrapper calls the FreeRTOS notification.
 */
static void IRAM_ATTR dio1_isr_wrapper(void)
{
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    if (dio1_task_handle != NULL) {
        vTaskNotifyGiveFromISR(dio1_task_handle, &xHigherPriorityTaskWoken);
        portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
    }
}

/**
 * @brief Initialize the SX1262 LoRa module using RadioLib
 * 
 * This follows the exact initialization sequence from the reference implementation:
 * 1. SPI.begin() with pins
 * 2. setRfSwitchPins()
 * 3. setDio1Action()
 * 4. beginDefault()
 * 5. setRxBoostedGainMode()
 * 6. startReceive()
 */
lora_sx1262_err_t lora_sx1262_init(const lora_sx1262_pins_t *pins, const lora_sx1262_config_t *config)
{
    if (pins == NULL || config == NULL) {
        return LORA_SX1262_ERR_INVALID_ARG;
    }

    if (initialized) {
        ESP_LOGW(TAG, "Driver already initialized");
        return LORA_SX1262_OK;
    }

    memcpy(&stored_pins, pins, sizeof(lora_sx1262_pins_t));
    memcpy(&stored_config, config, sizeof(lora_sx1262_config_t));

    // Store DIO1 task handle
    dio1_task_handle = xTaskGetCurrentTaskHandle();

    // Initialize Arduino SPI (from reference implementation)
    // ESP32: SPI.begin(sck, miso, mosi, ss)
    // Using pins from reference: CLK=18, MISO=19, MOSI=23, CS=5
    SPI.begin(18, 19, 23, pins->cs_pin);
    
    // Create SPI settings (from reference: 2MHz, MSB first, MODE0)
    SPISettings spi_settings(2000000, MSBFIRST, SPI_MODE0);
    
    // Create RadioLib Module object
    // Module(CS, DIO1, RESET, BUSY, SPI, SPISettings)
    radio_module = new Module(pins->cs_pin, pins->dio1_pin, pins->reset_pin, pins->busy_pin, SPI, spi_settings);
    if (radio_module == NULL) {
        ESP_LOGE(TAG, "Failed to create Module");
        return LORA_SX1262_ERR_INIT;
    }

    // Create SX1262 object
    radio = new SX1262(radio_module);
    if (radio == NULL) {
        ESP_LOGE(TAG, "Failed to create SX1262");
        delete radio_module;
        radio_module = NULL;
        return LORA_SX1262_ERR_INIT;
    }

    // Configure RF switch pins (from reference implementation)
    radio->setRfSwitchPins(pins->rx_en_pin, pins->tx_en_pin);

    // Set DIO1 interrupt handler (from reference implementation)
    // RadioLib expects a function pointer with no arguments
    radio->setDio1Action(dio1_isr_wrapper);

    // Initialize with default settings (following beginDefault() from reference)
    float freq_mhz = (float)config->frequency / 1000000.0f;
    float bw = bandwidth_values[config->bandwidth];
    uint8_t sf = config->spreading_factor + 5;  // Convert index to actual SF
    uint8_t cr = config->coding_rate + 5;        // Convert index to actual CR
    uint8_t sync_word = config->sync_word;
    int8_t tx_power = config->tx_power;
    uint8_t preamble_len = config->preamble_length + 6;  // Convert index to actual length
    float tcxo_voltage = config->tcxo_voltage;
    bool use_ldo = config->use_ldo_only;

    int16_t state = radio->begin(freq_mhz, bw, sf, cr, sync_word, tx_power, preamble_len, tcxo_voltage, use_ldo);
    if (state != RADIOLIB_ERR_NONE) {
        ESP_LOGE(TAG, "SX1262 begin failed: %d", state);
        delete radio;
        delete radio_module;
        radio = NULL;
        radio_module = NULL;
        return LORA_SX1262_ERR_INIT;
    }

    // Enable RX boosted gain mode (from reference implementation)
    state = radio->setRxBoostedGainMode(true);
    if (state != RADIOLIB_ERR_NONE) {
        ESP_LOGE(TAG, "setRxBoostedGainMode failed: %d", state);
        delete radio;
        delete radio_module;
        radio = NULL;
        radio_module = NULL;
        return LORA_SX1262_ERR_INIT;
    }

    // Start receive mode (from reference implementation)
    state = radio->startReceive();
    if (state != RADIOLIB_ERR_NONE) {
        ESP_LOGE(TAG, "startReceive failed: %d", state);
        delete radio;
        delete radio_module;
        radio = NULL;
        radio_module = NULL;
        return LORA_SX1262_ERR_INIT;
    }

    initialized = true;
    ESP_LOGI(TAG, "SX1262 initialized successfully using RadioLib");
    return LORA_SX1262_OK;
}

/**
 * @brief Deinitialize the SX1262 driver
 */
lora_sx1262_err_t lora_sx1262_deinit(void)
{
    if (!initialized) {
        return LORA_SX1262_ERR_NOT_INIT;
    }

    if (radio) {
        radio->sleep();
        delete radio;
        radio = NULL;
    }

    if (radio_module) {
        delete radio_module;
        radio_module = NULL;
    }

    SPI.end();
    initialized = false;
    return LORA_SX1262_OK;
}

/**
 * @brief Enter standby mode
 */
lora_sx1262_err_t lora_sx1262_standby(void)
{
    if (!initialized || radio == NULL) {
        return LORA_SX1262_ERR_NOT_INIT;
    }
    int16_t state = radio->standby();
    return (state == RADIOLIB_ERR_NONE) ? LORA_SX1262_OK : LORA_SX1262_ERR_INIT;
}

/**
 * @brief Start continuous receive mode
 */
lora_sx1262_err_t lora_sx1262_start_receive(void)
{
    if (!initialized || radio == NULL) {
        return LORA_SX1262_ERR_NOT_INIT;
    }
    int16_t state = radio->startReceive();
    return (state == RADIOLIB_ERR_NONE) ? LORA_SX1262_OK : LORA_SX1262_ERR_INIT;
}

/**
 * @brief Wait for a packet in continuous receive mode
 * 
 * Following the WaitForPacket pattern from reference implementation
 */
lora_sx1262_err_t lora_sx1262_wait_packet(uint8_t *data, size_t len, size_t *received_len, uint32_t timeout_ms)
{
    if (!initialized || radio == NULL) {
        return LORA_SX1262_ERR_NOT_INIT;
    }
    if (data == NULL || len == 0) {
        return LORA_SX1262_ERR_INVALID_ARG;
    }

    // Clear previous notifications (from reference implementation)
    xTaskNotifyStateClear(NULL);
    ulTaskNotifyValueClear(NULL, 0xFFFFFFFF);

    // Wait for DIO1 interrupt
    TickType_t timeout_ticks = timeout_ms > 0 ? pdMS_TO_TICKS(timeout_ms) : portMAX_DELAY;
    if (ulTaskNotifyTake(pdTRUE, timeout_ticks) == 0) {
        // Timeout: return to standby (clearIrqStatus is protected, RadioLib handles it internally)
        radio->standby();
        return LORA_SX1262_ERR_RX_TIMEOUT;
    }

    // Interrupt occurred, read packet
    // RadioLib's readData signature: readData(uint8_t* data, size_t len)
    // Length is available via getPacketLength() after readData
    int16_t state = radio->readData(data, len);

    // Check for CRC error (from reference: restart RX on CRC error)
    if (state == RADIOLIB_ERR_CRC_MISMATCH) {
        // RadioLib clears IRQ internally, just restart RX
        radio->startReceive();
        return LORA_SX1262_ERR_CRC;
    }

    if (state != RADIOLIB_ERR_NONE) {
        return LORA_SX1262_ERR_INIT;
    }

    // Get packet length (RadioLib stores it after readData)
    size_t length = radio->getPacketLength();

    // Get packet statistics
    last_rssi = radio->getRSSI();
    last_snr = radio->getSNR();
    last_freq_error = radio->getFrequencyError();

    if (received_len) {
        *received_len = length;
    }

    // Restart RX for continuous mode (from reference)
    radio->startReceive();

    return LORA_SX1262_OK;
}

/**
 * @brief Receive a packet (blocking, single RX)
 */
lora_sx1262_err_t lora_sx1262_receive(uint8_t *data, size_t len, size_t *received_len, uint32_t timeout_ms)
{
    if (!initialized || radio == NULL) {
        return LORA_SX1262_ERR_NOT_INIT;
    }

    // Start RX mode
    lora_sx1262_err_t err = lora_sx1262_start_receive();
    if (err != LORA_SX1262_OK) {
        return err;
    }

    // Wait for packet
    err = lora_sx1262_wait_packet(data, len, received_len, timeout_ms);
    if (err == LORA_SX1262_ERR_CRC) {
        // For single RX, return timeout on CRC error
        return LORA_SX1262_ERR_RX_TIMEOUT;
    }

    // Return to standby after single RX
    if (err == LORA_SX1262_OK) {
        radio->standby();
    }

    return err;
}

/**
 * @brief Transmit a packet
 * 
 * Following the transmit pattern from reference implementation
 */
lora_sx1262_err_t lora_sx1262_transmit(const uint8_t *data, size_t len, uint32_t timeout_ms)
{
    if (!initialized || radio == NULL) {
        return LORA_SX1262_ERR_NOT_INIT;
    }
    if (data == NULL || len == 0 || len > 255) {
        return LORA_SX1262_ERR_INVALID_ARG;
    }

    // Clear previous notifications
    xTaskNotifyStateClear(NULL);
    ulTaskNotifyValueClear(NULL, 0xFFFFFFFF);

    // Transmit (RadioLib handles standby, TX, wait, etc.)
    int16_t state = radio->transmit((uint8_t *)data, len);
    
    if (state != RADIOLIB_ERR_NONE) {
        ESP_LOGE(TAG, "Transmit failed: %d", state);
        return LORA_SX1262_ERR_INIT;
    }

    // Return to receive mode (from reference pattern)
    radio->startReceive();

    return LORA_SX1262_OK;
}

/**
 * @brief Get RSSI of last received packet
 */
float lora_sx1262_get_rssi(void)
{
    if (!initialized || radio == NULL) {
        return 0.0f;
    }
    return last_rssi;
}

/**
 * @brief Get SNR of last received packet
 */
float lora_sx1262_get_snr(void)
{
    if (!initialized || radio == NULL) {
        return 0.0f;
    }
    return last_snr;
}

/**
 * @brief Get frequency error of last received packet
 */
float lora_sx1262_get_frequency_error(void)
{
    if (!initialized || radio == NULL) {
        return 0.0f;
    }
    return last_freq_error;
}

/**
 * @brief Calculate time-on-air for a packet
 */
uint32_t lora_sx1262_get_time_on_air(size_t len)
{
    if (!initialized || radio == NULL) {
        return 0;
    }
    return radio->getTimeOnAir(len);
}
