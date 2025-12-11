# SPI Communication between OpenMV RT1062 and ESP32 Classic

This project implements bidirectional SPI communication between OpenMV RT1062 (Controller/Master) and ESP32 Classic (Peripheral/Slave).

## Hardware Connections

Connect the following pins between OpenMV RT1062 and ESP32 Classic:

| Signal | OpenMV RT1062 Pin | ESP32 Pin | Description |
|--------|-------------------|-----------|-------------|
| MOSI   | P8 (or your MOSI pin) | GPIO 23 | Master Out, Slave In |
| MISO   | P9 (or your MISO pin) | GPIO 19 | Master In, Slave Out |
| SCK    | P10 (or your SCK pin) | GPIO 18 | Serial Clock |
| CS/SS  | P7 (or your CS pin)  | GPIO 5  | Chip Select (Slave Select) |
| GND    | GND                 | GND      | Common Ground |

**Important Notes:**
- Adjust the pin numbers in both code files to match your actual hardware connections
- Ensure both devices share a common ground (GND)
- The CS pin on OpenMV should be configured as OUTPUT
- The CS pin on ESP32 is automatically handled by the SPI Slave driver

## SPI Configuration

Both devices are configured with:
- **Mode**: 0 (CPOL=0, CPHA=0)
- **Bit Order**: MSB First
- **Data Width**: 8 bits
- **Baudrate**: 1 MHz (can be adjusted in both files)

## Code Files

### `opnemv-spi.py`
OpenMV RT1062 code that acts as SPI Controller (Master). It:
- Initializes SPI in controller mode
- Sends data to ESP32
- Receives response from ESP32
- Uses `write_readinto()` for simultaneous bidirectional communication

### `esp-spi.ino`
ESP32 Classic code that acts as SPI Peripheral (Slave). It:
- Uses ESP32's native SPI Slave driver
- Waits for transactions from OpenMV
- Receives data and sends response simultaneously
- Prints received/sent data to Serial Monitor

## Usage

1. **Upload ESP32 code:**
   - Open `esp-spi.ino` in Arduino IDE
   - Select your ESP32 board
   - Adjust pin numbers if needed
   - Upload to ESP32
   - Open Serial Monitor at 115200 baud

2. **Upload OpenMV code:**
   - Connect OpenMV to your computer
   - Open `opnemv-spi.py` in OpenMV IDE
   - Adjust pin numbers to match your hardware
   - Run the script

3. **Monitor Communication:**
   - OpenMV IDE will show sent/received data
   - ESP32 Serial Monitor will show received/sent data

## Customization

### Changing Data Length
- In `opnemv-spi.py`: Modify the `tx_buffer` size in the main loop
- In `esp-spi.ino`: Modify `t.length` (in bits) in the `loop()` function

### Changing Baudrate
- In `opnemv-spi.py`: Change `BAUDRATE` variable
- In `esp-spi.ino`: The baudrate is controlled by the master (OpenMV), but you can add frequency setting if needed

### Changing Pin Numbers
- **OpenMV**: Modify `CS_PIN` and SPI pin configuration in `opnemv-spi.py`
- **ESP32**: Modify `SPI_MOSI`, `SPI_MISO`, `SPI_SCK`, `SPI_SS` defines in `esp-spi.ino`

## Troubleshooting

1. **No communication:**
   - Verify all connections (especially GND)
   - Check pin numbers match in both files
   - Ensure CS pin is properly configured on OpenMV

2. **Wrong data received:**
   - Verify SPI mode matches (should be Mode 0)
   - Check bit order (MSB first)
   - Ensure baudrate is reasonable (start with 1 MHz)

3. **ESP32 not responding:**
   - Check Serial Monitor for initialization messages
   - Verify ESP32 code uploaded successfully
   - Check if SPI Slave driver initialized correctly

## References

- [OpenMV SPI Documentation](https://docs.openmv.io/library/machine.SPI.html)
- [ESP32 SPI Slave Driver](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/spi_slave.html)

