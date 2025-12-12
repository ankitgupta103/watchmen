/*
 * ESP32 Classic SPI Peripheral (Slave) Code
 * Bidirectional SPI communication with OpenMV RT1062
 * 
 * This uses ESP32's native SPI Slave driver for proper slave operation
 */

#include <driver/spi_slave.h>
#include <esp_log.h>

// SPI Pin Configuration for ESP32
// Adjust these pins based on your ESP32 board and connections
#define SPI_MOSI 23  // Master Out, Slave In (from OpenMV perspective)
#define SPI_MISO 19  // Master In, Slave Out (from OpenMV perspective)
#define SPI_SCK 18   // Serial Clock
#define SPI_SS 5     // Slave Select (Chip Select)

// SPI Configuration
#define SPI_HOST_ID SPI2_HOST  // Use HSPI (SPI2)
#define DMA_CHAN 2              // DMA channel for SPI
#define BUFFER_SIZE 64          // Maximum transaction size

// Response counter
uint8_t response_counter = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP32 SPI Peripheral (Slave) Starting...");
  
  // Configure SPI Bus
  spi_bus_config_t buscfg = {
    .mosi_io_num = SPI_MOSI,
    .miso_io_num = SPI_MISO,
    .sclk_io_num = SPI_SCK,
    .quadwp_io_num = -1,  // Not used
    .quadhd_io_num = -1,  // Not used
    .max_transfer_sz = BUFFER_SIZE,
  };
  
  // Configure SPI Slave Interface
  // Note: Field order must match struct declaration order
  spi_slave_interface_config_t slvcfg = {};
  slvcfg.mode = 0;                    // SPI Mode 0: CPOL=0, CPHA=0 (matches OpenMV)
  slvcfg.spics_io_num = SPI_SS;       // CS pin
  slvcfg.queue_size = 3;              // Transaction queue size
  slvcfg.flags = 0;                   // No special flags
  slvcfg.post_setup_cb = NULL;        // Optional callback after CS setup
  slvcfg.post_trans_cb = NULL;        // Optional callback after transaction
  
  // Initialize SPI Slave
  esp_err_t ret = spi_slave_initialize(SPI_HOST_ID, &buscfg, &slvcfg, DMA_CHAN);
  
  if (ret != ESP_OK) {
    Serial.printf("SPI Slave initialization failed: %s\n", esp_err_to_name(ret));
    while(1) delay(1000);
  }
  
  Serial.println("ESP32 SPI Slave initialized successfully");
  Serial.println("Mode: 0 (CPOL=0, CPHA=0)");
  Serial.println("Waiting for data from OpenMV...");
  Serial.println();
}

void loop() {
  // Buffers for SPI transaction
  uint8_t rx_data[BUFFER_SIZE];
  uint8_t tx_data[BUFFER_SIZE];
  
  // Prepare transmit buffer (response data)
  // You can modify this to send any data you want
  for (int i = 0; i < BUFFER_SIZE; i++) {
    tx_data[i] = response_counter + i;  // Simple pattern for testing
  }
  response_counter++;
  
  // Create SPI transaction structure
  spi_slave_transaction_t t = {};
  t.length = 32;  // Length in bits (4 bytes = 32 bits for this example)
  t.tx_buffer = tx_data;
  t.rx_buffer = rx_data;
  
  // Wait for and process SPI transaction (blocking)
  // This will wait until the master (OpenMV) initiates a transfer
  esp_err_t ret = spi_slave_transmit(SPI_HOST_ID, &t, portMAX_DELAY);
  
  if (ret == ESP_OK) {
    // Transaction completed successfully
    Serial.print("Transaction received! Length: ");
    Serial.print(t.trans_len / 8);  // Convert bits to bytes
    Serial.println(" bytes");
    
    // Print received data
    Serial.print("Received: ");
    uint8_t bytes_received = t.trans_len / 8;
    for (int i = 0; i < bytes_received && i < BUFFER_SIZE; i++) {
      Serial.print("0x");
      if (rx_data[i] < 0x10) Serial.print("0");
      Serial.print(rx_data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
    
    // Print sent data
    Serial.print("Sent: ");
    for (int i = 0; i < bytes_received && i < BUFFER_SIZE; i++) {
      Serial.print("0x");
      if (tx_data[i] < 0x10) Serial.print("0");
      Serial.print(tx_data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
    Serial.println("---");
  } else {
    Serial.printf("SPI transaction error: %s\n", esp_err_to_name(ret));
  }
  
  // Small delay to prevent overwhelming the serial output
  delay(10);
}

