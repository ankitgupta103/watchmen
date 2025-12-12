/*
 * ESP32 SPI Slave Code
 * Bidirectional SPI communication with OpenMV RT1062
 * 
 * Uses ESP32's standard SPI Slave driver API
 */

#include <driver/spi_slave.h>
#include <string.h>

// SPI Pin Configuration for ESP32
#define SPI_MOSI 23  // Master Out, Slave In
#define SPI_MISO 19  // Master In, Slave Out
#define SPI_SCK 18   // Serial Clock
#define SPI_SS 5     // Slave Select (Chip Select)

// SPI Configuration
#define SPI_HOST_ID SPI2_HOST  // Use HSPI (SPI2)
#define DMA_CHAN 2
#define BUFFER_SIZE 64

// Global response counter
uint8_t response_counter = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32 SPI Slave Starting...");
  
  // Configure SPI Bus
  spi_bus_config_t buscfg = {
    .mosi_io_num = SPI_MOSI,
    .miso_io_num = SPI_MISO,
    .sclk_io_num = SPI_SCK,
    .quadwp_io_num = -1,
    .quadhd_io_num = -1,
    .max_transfer_sz = BUFFER_SIZE,
  };
  
  // Configure SPI Slave Interface
  spi_slave_interface_config_t slvcfg = {
    .mode = 0,                    // SPI Mode 0: CPOL=0, CPHA=0
    .spics_io_num = SPI_SS,
    .queue_size = 3,
    .flags = 0,
    .post_setup_cb = NULL,
    .post_trans_cb = NULL,
  };
  
  // Initialize SPI Slave
  esp_err_t ret = spi_slave_initialize(SPI_HOST_ID, &buscfg, &slvcfg, DMA_CHAN);
  
  if (ret != ESP_OK) {
    Serial.printf("SPI Slave init failed: %s\n", esp_err_to_name(ret));
    while(1) delay(1000);
  }
  
  Serial.println("ESP32 SPI Slave ready");
  Serial.println("Mode: 0 (CPOL=0, CPHA=0)");
  Serial.println();
}

void loop() {
  // Transaction buffers
  uint8_t rx_buffer[BUFFER_SIZE] = {0};
  uint8_t tx_buffer[BUFFER_SIZE] = {0};
  
  // Prepare response text
  char response_msg[64];
  snprintf(response_msg, sizeof(response_msg), "ESP32 Response #%d", response_counter);
  response_counter++;
  
  // Copy response to transmit buffer
  size_t msg_len = strlen(response_msg);
  if (msg_len >= BUFFER_SIZE) {
    msg_len = BUFFER_SIZE - 1;
  }
  memcpy(tx_buffer, response_msg, msg_len);
  memset(tx_buffer + msg_len, 0, BUFFER_SIZE - msg_len);
  
  // Initialize SPI transaction
  spi_slave_transaction_t trans = {};
  trans.length = BUFFER_SIZE * 8;  // Maximum length in bits
  trans.tx_buffer = tx_buffer;
  trans.rx_buffer = rx_buffer;
  
  // Wait for transaction from master (blocking)
  esp_err_t ret = spi_slave_transmit(SPI_HOST_ID, &trans, portMAX_DELAY);
  
  if (ret == ESP_OK) {
    // Get actual transaction length
    size_t actual_len = trans.trans_len / 8;  // Convert bits to bytes
    
    Serial.print("RX: ");
    Serial.print(actual_len);
    Serial.print(" bytes | ");
    
    // Print received data (hex)
    for (size_t i = 0; i < actual_len && i < BUFFER_SIZE; i++) {
      if (rx_buffer[i] < 0x10) Serial.print("0");
      Serial.print(rx_buffer[i], HEX);
      Serial.print(" ");
    }
    Serial.print("| ");
    
    // Print received data (text)
    for (size_t i = 0; i < actual_len && i < BUFFER_SIZE; i++) {
      if (rx_buffer[i] >= 32 && rx_buffer[i] < 127) {
        Serial.print((char)rx_buffer[i]);
      } else if (rx_buffer[i] == 0) {
        break;
      } else {
        Serial.print(".");
      }
    }
    
    Serial.print(" | TX: ");
    
    // Print sent data (hex)
    for (size_t i = 0; i < actual_len && i < BUFFER_SIZE; i++) {
      if (tx_buffer[i] < 0x10) Serial.print("0");
      Serial.print(tx_buffer[i], HEX);
      Serial.print(" ");
    }
    Serial.print("| ");
    
    // Print sent data (text)
    for (size_t i = 0; i < actual_len && i < BUFFER_SIZE; i++) {
      if (tx_buffer[i] >= 32 && tx_buffer[i] < 127) {
        Serial.print((char)tx_buffer[i]);
      } else if (tx_buffer[i] == 0) {
        break;
      } else {
        Serial.print(".");
      }
    }
    
    Serial.println();
  } else {
    Serial.printf("SPI error: %s\n", esp_err_to_name(ret));
  }
  
  delay(10);
}
