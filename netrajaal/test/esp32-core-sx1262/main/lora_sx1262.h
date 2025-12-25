/**
 * @file lora_sx1262.h
 * @brief SX1262 LoRa module driver for ESP-IDF
 * 
 * This driver implements point-to-point LoRa communication using the SX1262 chip.
 * The implementation follows the flow patterns documented in LORA_SX1262_FLOW.md,
 * which are derived from the LoRa-Test reference implementation.
 * 
 * @note This is a minimal implementation focused on P2P communication, not LoRaWAN.
 */

#ifndef LORA_SX1262_H
#define LORA_SX1262_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Pin configuration structure
 */
typedef struct {
    int cs_pin;      ///< Chip select (NSS) pin
    int reset_pin;   ///< Reset pin
    int busy_pin;    ///< BUSY pin (input)
    int dio1_pin;    ///< DIO1 interrupt pin (input)
    int rx_en_pin;   ///< RX enable pin (RF switch control)
    int tx_en_pin;   ///< TX enable pin (RF switch control)
} lora_sx1262_pins_t;

/**
 * @brief LoRa configuration structure
 */
typedef struct {
    uint32_t frequency;      ///< Frequency in Hz (e.g., 869525000 for 869.525 MHz)
    uint8_t bandwidth;       ///< Bandwidth index: 0=7.8kHz, 1=10.4kHz, ..., 7=125kHz, 8=250kHz, 9=500kHz
    uint8_t spreading_factor; ///< Spreading factor index: 0=SF5, 1=SF6, ..., 7=SF12 (actual SF = index + 5)
    uint8_t coding_rate;     ///< Coding rate index: 0=4/5, 1=4/6, 2=4/7, 3=4/8 (actual CR = index + 5)
    uint8_t sync_word;       ///< Sync word (0x12=private, 0x34=public, or custom like 0xE3)
    int8_t tx_power;         ///< TX power in dBm (-9 to 22)
    uint8_t preamble_length; ///< Preamble length index: 0=6 symbols, 1=7, ..., 14=20 (actual = index + 6)
    float tcxo_voltage;      ///< TCXO voltage: 1.6, 1.7, 1.8, 2.2, 2.4, 2.7, 3.0, 3.3
    bool use_ldo_only;       ///< Use LDO only (false = LDO + DC-DC, true = LDO only)
} lora_sx1262_config_t;

/**
 * @brief Default pin configuration (ESP32 from reference implementation)
 */
#define LORA_SX1262_PINS_DEFAULT { \
    .cs_pin = 5, \
    .reset_pin = 27, \
    .busy_pin = 26, \
    .dio1_pin = 32, \
    .rx_en_pin = 25, \
    .tx_en_pin = 33 \
}

/**
 * @brief Default LoRa configuration (from reference implementation)
 */
#define LORA_SX1262_CONFIG_DEFAULT { \
    .frequency = 869525000, \
    .bandwidth = 7,          /* 125 kHz */ \
    .spreading_factor = 4,   /* SF9 (4+5) */ \
    .coding_rate = 2,         /* 4/7 (2+5) */ \
    .sync_word = 0xE3,       /* Custom sync word */ \
    .tx_power = 9,           /* 9 dBm */ \
    .preamble_length = 2,    /* 8 symbols (2+6) */ \
    .tcxo_voltage = 1.7f,    /* 1.7V */ \
    .use_ldo_only = false    /* LDO + DC-DC */ \
}

/**
 * @brief Error codes
 */
typedef enum {
    LORA_SX1262_OK = 0,              ///< Success
    LORA_SX1262_ERR_INVALID_ARG,     ///< Invalid argument
    LORA_SX1262_ERR_TIMEOUT,         ///< Operation timeout
    LORA_SX1262_ERR_BUSY_TIMEOUT,    ///< BUSY pin timeout
    LORA_SX1262_ERR_SPI,             ///< SPI communication error
    LORA_SX1262_ERR_CRC,             ///< CRC error (packet corrupted)
    LORA_SX1262_ERR_RX_TIMEOUT,      ///< RX timeout (no packet received)
    LORA_SX1262_ERR_TX_TIMEOUT,      ///< TX timeout
    LORA_SX1262_ERR_INIT,            ///< Initialization error
    LORA_SX1262_ERR_NOT_INIT,        ///< Driver not initialized
} lora_sx1262_err_t;

/**
 * @brief Initialize the SX1262 LoRa module
 * 
 * This function performs full initialization:
 * - Hardware reset
 * - SPI and GPIO configuration
 * - Register configuration
 * - RF switch setup
 * - DIO1 interrupt setup
 * - RX boosted gain mode
 * - Start receive mode
 * 
 * @param pins Pin configuration
 * @param config LoRa configuration parameters
 * @return LORA_SX1262_OK on success, error code otherwise
 */
lora_sx1262_err_t lora_sx1262_init(const lora_sx1262_pins_t *pins, const lora_sx1262_config_t *config);

/**
 * @brief Deinitialize the SX1262 driver
 * 
 * Cleans up resources and puts the chip in sleep mode.
 * 
 * @return LORA_SX1262_OK on success
 */
lora_sx1262_err_t lora_sx1262_deinit(void);

/**
 * @brief Transmit a packet
 * 
 * This function performs the full TX flow:
 * - Enter standby mode
 * - Set RF switch to TX
 * - Write packet to FIFO
 * - Start transmission
 * - Wait for TX done interrupt
 * - Clear IRQ flags
 * - Return to standby
 * - Set RF switch to RX
 * 
 * @param data Packet data to transmit
 * @param len Packet length in bytes (max 255)
 * @param timeout_ms Timeout in milliseconds (0 = use calculated TOA + margin)
 * @return LORA_SX1262_OK on success, error code otherwise
 */
lora_sx1262_err_t lora_sx1262_transmit(const uint8_t *data, size_t len, uint32_t timeout_ms);

/**
 * @brief Receive a packet (blocking)
 * 
 * This function performs a single RX operation:
 * - Enter standby mode
 * - Set RF switch to RX
 * - Start RX mode
 * - Wait for RX done interrupt or timeout
 * - Read IRQ flags
 * - Check for CRC errors
 * - Read packet from FIFO
 * - Clear IRQ flags
 * - Return to standby
 * 
 * @param data Buffer to store received packet
 * @param len Maximum buffer length
 * @param received_len Pointer to store actual received length (can be NULL)
 * @param timeout_ms Timeout in milliseconds (0 = infinite)
 * @return LORA_SX1262_OK on success, LORA_SX1262_ERR_RX_TIMEOUT on timeout, 
 *         LORA_SX1262_ERR_CRC on CRC error, other error codes on failure
 */
lora_sx1262_err_t lora_sx1262_receive(uint8_t *data, size_t len, size_t *received_len, uint32_t timeout_ms);

/**
 * @brief Start continuous receive mode
 * 
 * This function starts RX mode and returns immediately. The application should
 * call lora_sx1262_wait_packet() to wait for incoming packets.
 * 
 * @return LORA_SX1262_OK on success, error code otherwise
 */
lora_sx1262_err_t lora_sx1262_start_receive(void);

/**
 * @brief Wait for a packet in continuous receive mode
 * 
 * This function waits for a DIO1 interrupt indicating a packet was received.
 * It should be called after lora_sx1262_start_receive().
 * 
 * @param data Buffer to store received packet
 * @param len Maximum buffer length
 * @param received_len Pointer to store actual received length (can be NULL)
 * @param timeout_ms Timeout in milliseconds (0 = infinite)
 * @return LORA_SX1262_OK on success, LORA_SX1262_ERR_RX_TIMEOUT on timeout,
 *         LORA_SX1262_ERR_CRC on CRC error, other error codes on failure
 */
lora_sx1262_err_t lora_sx1262_wait_packet(uint8_t *data, size_t len, size_t *received_len, uint32_t timeout_ms);

/**
 * @brief Enter standby mode
 * 
 * Puts the chip in STANDBY_RC mode. This should be called before
 * switching between TX and RX modes.
 * 
 * @return LORA_SX1262_OK on success, error code otherwise
 */
lora_sx1262_err_t lora_sx1262_standby(void);

/**
 * @brief Get RSSI of last received packet
 * 
 * @return RSSI value in dBm
 */
float lora_sx1262_get_rssi(void);

/**
 * @brief Get SNR of last received packet
 * 
 * @return SNR value in dB
 */
float lora_sx1262_get_snr(void);

/**
 * @brief Get frequency error of last received packet
 * 
 * @return Frequency error in Hz
 */
float lora_sx1262_get_frequency_error(void);

/**
 * @brief Calculate time-on-air for a packet
 * 
 * Calculates the transmission time for a packet with the current configuration.
 * 
 * @param len Packet length in bytes
 * @return Time-on-air in microseconds
 */
uint32_t lora_sx1262_get_time_on_air(size_t len);

#ifdef __cplusplus
}
#endif

#endif // LORA_SX1262_H

