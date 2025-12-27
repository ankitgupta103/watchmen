# Changes Made for OpenMV RT1062 Support

## Library Modifications

### `lib/sx126x.py`

Modified the `SX126X.__init__()` method to support OpenMV RT1062 SPI configuration:

1. **Added SPI parameters**: The constructor now accepts `spi_baudrate`, `spi_polarity`, and `spi_phase` parameters (with defaults matching the original implementation).

2. **OpenMV RT1062 SPI initialization**: Added a new try/except block that attempts to initialize SPI using the OpenMV RT1062 format:
   ```python
   SPI(spi_bus, baudrate=spi_baudrate, polarity=spi_polarity, phase=spi_phase,
       bits=8, firstbit=SPI.MSB, sck=Pin(clk), mosi=Pin(mosi), miso=Pin(miso))
   ```

3. **Fallback compatibility**: The code maintains backward compatibility by trying:
   - OpenMV RT1062 format (new)
   - Pycom variant (existing)
   - Generic MicroPython variant (existing)

## Pin Mapping

The examples use the following pin configuration for OpenMV RT1062:

| Pin | Function | Core1262-868M Connection |
|-----|----------|--------------------------|
| P0  | MOSI     | MOSI                     |
| P1  | MISO     | MISO                     |
| P2  | SCLK     | SCLK                     |
| P3  | CS       | CS                       |
| P6  | RESET    | RESET                    |
| P7  | BUSY     | BUSY                     |
| P13 | DIO1/IRQ | DIO1                     |

## Usage

To use the library with OpenMV RT1062, simply pass the pin names (as strings) and SPI configuration parameters:

```python
from sx1262 import SX1262

sx = SX1262(
    spi_bus=1,
    clk='P2',
    mosi='P0',
    miso='P1',
    cs='P3',
    irq='P13',
    rst='P6',
    gpio='P7',
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)
```

The library will automatically detect and use the appropriate SPI initialization method for your platform.

## Notes

- Pin names can be passed as strings ('P0', 'P1', etc.) or as pin numbers, depending on your OpenMV RT1062 configuration.
- The SPI configuration (baudrate, polarity, phase) can be customized via constructor parameters.
- All other functionality remains unchanged from the original library.

