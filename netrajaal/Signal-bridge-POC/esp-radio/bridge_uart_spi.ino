/**
 * UART -> SPI bridge for ESP32 (Arduino)
 * - Reads data from Serial2 (UART on GPIO16/17) in its own task
 * - Shares the latest UART payload over SPI slave (HSPI, pins 23/19/18/5)
 * - SPI runs in a separate task so UART + SPI work in parallel
 * - Blinks on-board LED whenever UART data is received or SPI is clocked
 * - Keeps GPIO21 and GPIO22 held LOW as in the reference sketches
 */

#include <Arduino.h>
#include "driver/spi_slave.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

// ---------------- GPIO CONFIG ----------------
const int PIN_D21 = 21;
const int PIN_D22 = 22;

const int UART2_RX_PIN = 16;
const int UART2_TX_PIN = 17;

const int LED_PIN = 2;
const int LED_BLINK_TIME = 10;  // ms

// SPI pins
#define PIN_MOSI 23
#define PIN_MISO 19
#define PIN_SCLK 18
#define PIN_CS   5

#define SPI_HOST HSPI_HOST
#define FRAME_SIZE 250

// ---------------- GLOBALS ----------------
unsigned long ledOffTime = 0;

uint8_t spi_tx_buf[FRAME_SIZE];   // Data sent to master (OpenMV)
uint8_t spi_rx_buf[FRAME_SIZE];   // Unused, but required by API

SemaphoreHandle_t txMutex;        // protects spi_tx_buf during update/transmit

// Task handles (optional for debugging)
TaskHandle_t uartTaskHandle = nullptr;
TaskHandle_t spiTaskHandle = nullptr;

// ---------------- UTIL ----------------
void blinkLED() {
  digitalWrite(LED_PIN, HIGH);
  ledOffTime = millis() + LED_BLINK_TIME;
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  pinMode(PIN_D21, OUTPUT);
  pinMode(PIN_D22, OUTPUT);
  digitalWrite(PIN_D21, LOW);
  digitalWrite(PIN_D22, LOW);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\nESP32 UART -> SPI bridge (HSPI slave)");

  // UART init
  Serial2.begin(115200, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN);
  Serial2.setTimeout(2000);

  // SPI slave init
  spi_bus_config_t buscfg = {};
  buscfg.mosi_io_num = PIN_MOSI;
  buscfg.miso_io_num = PIN_MISO;
  buscfg.sclk_io_num = PIN_SCLK;
  buscfg.quadwp_io_num = -1;
  buscfg.quadhd_io_num = -1;

  spi_slave_interface_config_t slvcfg = {};
  slvcfg.mode = 0;
  slvcfg.spics_io_num = PIN_CS;
  slvcfg.queue_size = 1;

  spi_slave_initialize(SPI_HOST, &buscfg, &slvcfg, SPI_DMA_CH_AUTO);

  // Initial SPI message
  memset(spi_tx_buf, 0, FRAME_SIZE);
  strcpy((char*)spi_tx_buf, "ESP32 READY (waiting for UART)");

  Serial.println("UART ready @115200, timeout=2000 ms");
  Serial.println("SPI slave ready (FRAME_SIZE=250)");

  txMutex = xSemaphoreCreateMutex();

  // Start tasks
  xTaskCreatePinnedToCore(
    [](void*) {
      for (;;) {
        size_t availableBytes = Serial2.available();
        if (availableBytes > 0) {
          uint8_t uart_buf[FRAME_SIZE] = {0};
          size_t toRead = availableBytes;
          if (toRead > FRAME_SIZE - 1) {
            toRead = FRAME_SIZE - 1;  // reserve space for terminator
          }
          size_t readLen = Serial2.readBytes(uart_buf, toRead);

          if (xSemaphoreTake(txMutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            memset(spi_tx_buf, 0, FRAME_SIZE);
            memcpy(spi_tx_buf, uart_buf, readLen);
            xSemaphoreGive(txMutex);
          }

          Serial.print("[UART RX] ");
          Serial.write(uart_buf, readLen);
          Serial.println();

          blinkLED();
        }
        vTaskDelay(pdMS_TO_TICKS(5));
      }
    },
    "uartTask",
    4096,
    nullptr,
    2,
    &uartTaskHandle,
    1  // pin to core 1
  );

  xTaskCreatePinnedToCore(
    [](void*) {
      spi_slave_transaction_t t = {};
      for (;;) {
        memset(&t, 0, sizeof(t));
        t.length = FRAME_SIZE * 8;

        // lock buffer while SPI uses it
        if (xSemaphoreTake(txMutex, portMAX_DELAY) == pdTRUE) {
          t.tx_buffer = spi_tx_buf;
          t.rx_buffer = spi_rx_buf;
          spi_slave_transmit(SPI_HOST, &t, portMAX_DELAY);
          xSemaphoreGive(txMutex);
        }

        blinkLED();  // SPI activity
      }
    },
    "spiTask",
    4096,
    nullptr,
    2,
    &spiTaskHandle,
    0  // pin to core 0
  );
}

// ---------------- LOOP ----------------
void loop() {
  // Turn LED OFF when timeout expires
  if (millis() > ledOffTime) {
    digitalWrite(LED_PIN, LOW);
  }
}


