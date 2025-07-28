import time
from machine import SPI, Pin

class SC16IS750:
    # Register map (from datasheet)
    REG_RHR = 0x00
    REG_THR = 0x00
    REG_IER = 0x01
    REG_FCR = 0x02
    REG_IIR = 0x02
    REG_LCR = 0x03
    REG_MCR = 0x04
    REG_LSR = 0x05
    REG_MSR = 0x06
    REG_SPR = 0x07
    REG_TXLVL = 0x08
    REG_RXLVL = 0x09
    REG_IOCONTROL = 0x0E
    REG_EFCR = 0x0F

    REG_DLL = 0x00
    REG_DLH = 0x01
    REG_EFR = 0x02

    CRYSTAL_FREQ = 14745600

    def __init__(self, spi_bus, cs_pin):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=4000000, polarity=0, phase=0)

    def _write_register(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([reg << 3]))
        self.spi.write(bytearray([val]))
        self.cs.value(1)

    def _read_register(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        result = self.spi.read(1)[0]
        self.cs.value(1)
        return result

    def reset_device(self):
        reg = self._read_register(self.REG_IOCONTROL)
        self._write_register(self.REG_IOCONTROL, reg | 0x08)

    def set_baudrate(self, baudrate):
        prescaler = 1 if (self._read_register(self.REG_MCR) & 0x80) == 0 else 4
        divisor = int((self.CRYSTAL_FREQ // prescaler) // (baudrate * 16))

        lcr = self._read_register(self.REG_LCR)
        self._write_register(self.REG_LCR, lcr | 0x80)
        self._write_register(self.REG_DLL, divisor & 0xFF)
        self._write_register(self.REG_DLH, (divisor >> 8) & 0xFF)
        self._write_register(self.REG_LCR, lcr & 0x7F)

    def set_line(self):
        # 8-bit, no parity, 1 stop bit
        self._write_register(self.REG_LCR, 0x03)

    def enable_fifo(self):
        self._write_register(self.REG_FCR, 0x07)

    def available(self):
        return self._read_register(self.REG_RXLVL)

    def read(self):
        if self.available():
            return self._read_register(self.REG_RHR)
        return -1

    def write(self, byte):
        while (self._read_register(self.REG_LSR) & 0x20) == 0:
            pass  # wait for TX buffer
        self._write_register(self.REG_THR, byte)

    def ping(self):
        self._write_register(self.REG_SPR, 0x55)
        if self._read_register(self.REG_SPR) != 0x55:
            return False
        self._write_register(self.REG_SPR, 0xAA)
        if self._read_register(self.REG_SPR) != 0xAA:
            return False
        return True

# ----- usage exampele -------
print("Initializing SC16IS750...")
uart_bridge = SC16IS750(spi_bus=1, cs_pin="P3")

uart_bridge.reset_device()
uart_bridge.set_baudrate(9600)
uart_bridge.set_line()
uart_bridge.enable_fifo()

if uart_bridge.ping():
    print("SC16IS750 connected!")
else:
    print("SC16IS750 not responding.")

print("Listening for UART data via SPI...")
buffer = ""
while True:
    val = uart_bridge.read()
    if val != -1:
        char = chr(val)
        if char == '\n':
            if "$GPGGA" in buffer or "$GPRMC" in buffer:
                parts = buffer.strip().split(',')

                if buffer.startswith("$GPGGA") and len(parts) > 5:
                    # $GPGGA format: time, lat, N/S, lon, E/W
                    lat_raw = parts[2]
                    lat_dir = parts[3]
                    lon_raw = parts[4]
                    lon_dir = parts[5]

                    if lat_raw and lon_raw:
                        lat_deg = float(lat_raw[:2])
                        lat_min = float(lat_raw[2:])
                        lon_deg = float(lon_raw[:3])
                        lon_min = float(lon_raw[3:])
                        
                        latitude = lat_deg + (lat_min / 60.0)
                        if lat_dir == 'S':
                            latitude *= -1

                        longitude = lon_deg + (lon_min / 60.0)
                        if lon_dir == 'W':
                            longitude *= -1

                        print(f"Latitude: {latitude}, Longitude: {longitude}")

                elif buffer.startswith("$GPRMC") and len(parts) > 6:
                    # $GPRMC format: time, status, lat, N/S, lon, E/W,...
                    lat_raw = parts[3]
                    lat_dir = parts[4]
                    lon_raw = parts[5]
                    lon_dir = parts[6]

                    if lat_raw and lon_raw:
                        lat_deg = float(lat_raw[:2])
                        lat_min = float(lat_raw[2:])
                        lon_deg = float(lon_raw[:3])
                        lon_min = float(lon_raw[3:])
                        
                        latitude = lat_deg + (lat_min / 60.0)
                        if lat_dir == 'S':
                            latitude *= -1

                        longitude = lon_deg + (lon_min / 60.0)
                        if lon_dir == 'W':
                            longitude *= -1

                        print(f"Latitude: {latitude}, Longitude: {longitude}")
            
            buffer = ""  # Reset buffer after each line
        else:
            buffer += char
    time.sleep_ms(10)



