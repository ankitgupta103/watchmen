# ESP32 UART ↔ SPI Bridge (with OpenMV Master)

This project turns the ESP32 into a **UART-to-SPI bridge**:

- ESP32 **receives data over UART1** (pins GPIO16 RX, GPIO17 TX) and/or from the USB console (UART0).
- The **latest received data is copied into a 250-byte SPI TX buffer**.
- OpenMV acts as **SPI master**, periodically clocking data out of the ESP32 (SPI slave) and printing what it receives.
- An on-board LED on **GPIO2** blinks briefly whenever UART data is received or sent.

All logic is implemented in `main.c` using **ESP-IDF (C, not Arduino)**.

---

## Hardware Overview

### ESP32 pins

- **UART (external device)**
  - `UART_EXT` = `UART_NUM_1`
  - **RX**: GPIO16 (data coming *into* ESP32 from your external UART source)
  - **TX**: GPIO17 (data going *out* of ESP32 to your external UART sink)

- **USB serial (console / monitor)**
  - `UART_USB` = `UART_NUM_0` (the default USB-JTAG / serial)

- **SPI (ESP32 as slave)**
  - `SPI_HOST` = `HSPI_HOST`
  - **MOSI**: GPIO23 (from OpenMV → ESP32, not used functionally here)
  - **MISO**: GPIO19 (from ESP32 → OpenMV; this is where our buffered data goes out)
  - **SCLK**: GPIO18
  - **CS**: GPIO5

- **LED**
  - **GPIO2**: activity indicator (blinks whenever UART data is processed).

- **Pull-down lines**
  - GPIO21 = `PIN_D21` (driven LOW)
  - GPIO22 = `PIN_D22` (driven LOW)

### OpenMV pins (master) vs ESP32 pins (slave)

From `pin_connection.md` and `openmv-spi-code.py`:

- **OpenMV (Master) → ESP32 (Slave)**
  - OpenMV `P0` (MOSI)  → ESP32 GPIO23 (MOSI)
  - OpenMV `P1` (MISO)  ← ESP32 GPIO19 (MISO)
  - OpenMV `P2` (SCK)   → ESP32 GPIO18 (SCLK)
  - OpenMV `P3` (CS)    → ESP32 GPIO5 (CS/SS)
  - Common **GND** between ESP32 and OpenMV is required.

---

## High-Level Data Flow

### 1. USB console (UART0) → UART1 → External device

1. You type data in the ESP32 serial monitor (USB console = `UART_USB`).
2. The **`usb_to_uart_ext_task`** running on the ESP32:
   - Reads bytes from `UART_USB`.
   - Forwards them to `UART_EXT` (GPIO17 TX) so the external UART device receives them.
   - Copies the same bytes into the shared SPI TX buffer `spi_tx_buf` so that OpenMV can also see them.
   - Blinks LED on GPIO2.

### 2. External device (UART1 RX) → USB console + SPI buffer

1. Your external device sends data into ESP32 **UART1 RX** (GPIO16).
2. The **`uart_ext_to_spi_task`** on the ESP32:
   - Reads the bytes from `UART_EXT` (RX=16).
   - Logs them to the USB console (`UART_USB`) with the tag `[UART_EXT -> USB]`.
   - Copies the bytes into `spi_tx_buf` (the global 250-byte buffer used by SPI slave).
   - Blinks LED on GPIO2.

### 3. SPI (OpenMV master) → ESP32 (slave) → OpenMV reads buffer

1. The **`spi_slave_task`** runs continuously on the ESP32:
   - It waits in a loop on `spi_slave_transmit(SPI_HOST, &t, portMAX_DELAY)`.
   - Each time OpenMV pulls CS low and clocks a transaction using `spi.write_readinto()`, the transaction completes.
   - The ESP32 sends the **current contents of `spi_tx_buf`** to OpenMV over MISO.
   - `spi_rx_buf` receives any bytes from OpenMV (currently not used).

2. Meanwhile, the OpenMV script (`openmv-spi-code.py`) does:
   - Configures itself as **SPI master** on its SPI1 bus.
   - In a loop:
     - Creates `tx = bytearray(FRAME_SIZE)` (dummy clocks) and `rx = bytearray(FRAME_SIZE)`.
     - Pulls **CS low**, waits a few µs.
     - Calls `spi.write_readinto(tx, rx)` to clock **250 bytes** from ESP32.
     - Releases **CS high**.
     - Prints `rx` as ASCII.

Because of this, **every OpenMV SPI frame shows whatever is currently stored in `spi_tx_buf` on the ESP32**.

---

## Detailed Code Behavior (ESP32 `main.c`)

### Global constants and buffers

- **UART configuration**
  - `UART_BAUD_RATE = 115200`
  - `UART_BUF_SIZE = 256`

- **SPI configuration**
  - `SPI_FRAME_SIZE = 250` bytes (must match `FRAME_SIZE` in `openmv-spi-code.py`).
  - Global buffers:
    - `static uint8_t spi_tx_buf[SPI_FRAME_SIZE];`  ← **what ESP32 sends to OpenMV**
    - `static uint8_t spi_rx_buf[SPI_FRAME_SIZE];`  ← receives data from OpenMV (currently just cleared and ignored)

- **LED helper**
  - `led_blink_short()` turns LED GPIO2 on, delays ~10 ms, then turns it off.

### Initialization in `app_main()`

Within `app_main`:

1. **GPIO21 and GPIO22** are configured as outputs and set LOW.
2. **LED GPIO2** is configured as output and initially set LOW.
3. Logs: `"ESP32 UART+SPI bridge example with LED activity blink"`.
4. **UART setup**:
   - Configures `UART_EXT` (UART1) on pins 16 (RX) and 17 (TX) at 115200 baud.
   - Ensures `UART_USB` (UART0) is also configured at 115200.
5. Logs: `"UART_EXT@115200 on TX=17 RX=16; bridging to SPI slave and console UART"`.
6. **SPI slave setup**:
   - `spi_bus_config_t buscfg` with MOSI=23, MISO=19, SCLK=18.
   - `spi_slave_interface_config_t slvcfg` with mode=0, CS=GPIO5, queue_size=1.
   - Calls `spi_slave_initialize(SPI_HOST, &buscfg, &slvcfg, SPI_DMA_CH_AUTO)`.
   - Logs SPI pin configuration and frame size.
7. **Initialize `spi_tx_buf` test pattern**:
   - Fills `spi_tx_buf` with zeros.
   - Copies string `"NO UART DATA YET - SPI TEST PATTERN"` into the beginning.
   - Therefore, before any UART data, OpenMV will see this pattern in each 250-byte frame.
8. **Start FreeRTOS tasks**:
   - `uart_ext_to_spi_task` (handles UART1 RX → USB + SPI buffer).
   - `usb_to_uart_ext_task` (handles USB → UART1 TX + SPI buffer).
   - `spi_slave_task` (handles continuous SPI slave transfers).

### `uart_ext_to_spi_task` (UART_EXT RX → usb log + SPI buffer)

- Runs forever:
  1. Calls `uart_read_bytes(UART_EXT, buf, sizeof(buf), pdMS_TO_TICKS(20));`.
  2. If `len > 0`:
     - Forwards the bytes to USB console: `uart_write_bytes(UART_USB, buf, len);`.
     - Logs `"[UART_EXT -> USB] <len> bytes"`.
     - Updates **`spi_tx_buf`**:
       - `to_send = min(len, SPI_FRAME_SIZE)`.
       - `memset(spi_tx_buf, 0, SPI_FRAME_SIZE);`
       - `memcpy(spi_tx_buf, buf, to_send);`
     - Calls `led_blink_short()`.

**Summary**: whenever your external UART device sends data to GPIO16, that payload is also what OpenMV will see (up to 250 bytes) on the next SPI frame.

### `usb_to_uart_ext_task` (USB → UART_EXT TX + SPI buffer)

- Runs forever:
  1. Calls `uart_read_bytes(UART_USB, buf, sizeof(buf), pdMS_TO_TICKS(20));`.
  2. If `len > 0`:
     - Forwards the bytes to external UART: `uart_write_bytes(UART_EXT, buf, len);`.
     - Logs `"[USB -> UART_EXT] <len> bytes"`.
     - Mirrors the same bytes into **`spi_tx_buf`**:
       - `to_send = min(len, SPI_FRAME_SIZE)`.
       - `memset(spi_tx_buf, 0, SPI_FRAME_SIZE);`
       - `memcpy(spi_tx_buf, buf, to_send);`
     - Calls `led_blink_short()`.

**Summary**: whatever you type on the ESP32 USB serial monitor is both sent out on UART1 TX=17 **and** exposed to OpenMV via `spi_tx_buf`.

### `spi_slave_task` (SPI slave loop)

- Runs forever:
  1. Clears `spi_rx_buf` with `memset(spi_rx_buf, 0, SPI_FRAME_SIZE);`.
  2. Sets up a `spi_slave_transaction_t t`:
     - `t.length = SPI_FRAME_SIZE * 8;` (bits)
     - `t.tx_buffer = spi_tx_buf;`
     - `t.rx_buffer = spi_rx_buf;`
  3. Calls `spi_slave_transmit(SPI_HOST, &t, portMAX_DELAY);`.
     - This **blocks until OpenMV (SPI master) performs a transaction** with CS low and clocks 250 bytes.
     - On success, it has sent the current contents of `spi_tx_buf` to OpenMV.

**Important**: `spi_tx_buf` is updated by the UART tasks; `spi_slave_task` just serves whatever the latest buffer contents are.

---

## OpenMV Master Script (`openmv-spi-code.py`)

### Configuration

- Sets up Chip Select pin:
  - `cs = Pin("P3", Pin.OUT, value=1)`  (idle HIGH, active LOW).

- Configures SPI1 as master:
  - `spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)`
  - `FRAME_SIZE = 250` (must match ESP32 `SPI_FRAME_SIZE`).

### Main loop

In each loop iteration:

1. Allocate `tx = bytearray(FRAME_SIZE)` and `rx = bytearray(FRAME_SIZE)`.
2. Pull CS low: `cs.low()`.
3. Small delay: `time.sleep_us(5)`.
4. SPI transfer:
   - `spi.write_readinto(tx, rx)`
   - This clocks **exactly 250 bytes**.
   - ESP32 responds as SPI slave with the current contents of `spi_tx_buf`.
5. Small delay and deassert CS: `cs.high()`.
6. Prints the 250-byte RX frame in ASCII form:
   - Non-printable bytes are replaced with `.`.

**Interpretation**:

- If you see: `NO UART DATA YET - SPI TEST PATTERN...` repeated, it means **no UART data has been copied yet**; you are still seeing the initial pattern from `app_main()`.
- Once you:
  - Type something on the ESP32 USB console, **or**
  - Send data from your external UART into GPIO16,

  then on the next SPI frame, the beginning of the 250-byte ASCII output on OpenMV should change to what you sent.

---

## Quick Test Checklist

1. **Wiring**:
   - Confirm MOSI/MISO/SCK/CS/GND between OpenMV and ESP32 exactly match `pin_connection.md`.
2. **Flash ESP32**:
   - `idf.py -p /dev/ttyUSBx flash monitor`
   - Watch logs: you should see initialization messages and the three tasks starting.
3. **Run OpenMV script**:
   - Load `openmv-spi-code.py` on OpenMV.
   - Observe printed `RX FRAME` blocks.
4. **USB → SPI test**:
   - In the ESP32 serial monitor, type: `HELLO_FROM_USB` and press Enter.
   - You should see a log `[USB -> UART_EXT] 15 bytes` on ESP32.
   - On OpenMV, the next SPI frame should begin with `HELLO_FROM_USB` (followed by dots for padding).
5. **External UART → SPI test** (if you have a UART device on GPIO16/17):
   - Send `HELLO_FROM_UART1` to ESP32 RX ( GPIO16 ).
   - Check ESP32 logs for `[UART_EXT -> USB] ...`.
   - OpenMV should start showing `HELLO_FROM_UART1` at the beginning of the next frames.

---

## Summary

- **UART data path**:
  - External device → `UART_EXT` (GPIO16 RX) → `uart_ext_to_spi_task` → `spi_tx_buf`.
  - USB console → `UART_USB` → `usb_to_uart_ext_task` → `UART_EXT` (GPIO17 TX) **and** `spi_tx_buf`.
- **SPI data path**:
  - OpenMV (master) periodically clocks 250-byte transactions.
  - `spi_slave_task` responds with **the current `spi_tx_buf` contents** each time.
- The LED on GPIO2 blinks whenever UART traffic is handled, indicating live UART activity.
