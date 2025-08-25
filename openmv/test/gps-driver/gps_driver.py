import time
from machine import SPI, Pin

class SC16IS750:
    """SC16IS750 UART bridge driver"""

    def __init__(self, spi_bus, cs_pin):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=100000, polarity=0, phase=0)

    def _write_register(self, reg, val):
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytearray([reg << 3]))
        time.sleep_us(5)
        self.spi.write(bytearray([val]))
        time.sleep_us(10)
        self.cs.value(1)
        time.sleep_us(50)

    def _read_register(self, reg):
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        time.sleep_us(5)
        result = self.spi.read(1)[0]
        time.sleep_us(10)
        self.cs.value(1)
        time.sleep_us(50)
        return result

    def init_gps(self):
        """Initialize for GPS at 9600 baud"""
        # Reset
        reg = self._read_register(0x0E)
        self._write_register(0x0E, reg | 0x08)
        time.sleep_ms(200)

        # Set 9600 baud
        divisor = 96  # 14745600 / (9600 * 16)
        self._write_register(0x03, 0x80)  # Enable divisor access
        time.sleep_ms(10)
        self._write_register(0x00, divisor & 0xFF)  # DLL
        self._write_register(0x01, divisor >> 8)    # DLH
        self._write_register(0x03, 0x03)  # 8N1
        time.sleep_ms(10)

        # Setup UART
        self._write_register(0x02, 0x07)  # Reset & enable FIFO
        self._write_register(0x01, 0x00)  # Disable interrupts
        self._write_register(0x04, 0x00)  # Normal operation
        time.sleep_ms(100)

        # Clear buffer
        while self._read_register(0x09) > 0:
            self._read_register(0x00)

    def read_data(self):
        """Read available GPS data"""
        data = ""
        while self._read_register(0x09) > 0:  # bytes available
            byte_val = self._read_register(0x00)
            if (32 <= byte_val <= 126) or byte_val in [10, 13]:
                data += chr(byte_val)
        return data

class GPS:
    """Simple GPS coordinate extractor"""

    def __init__(self, uart):
        self.uart = uart
        self.buffer = ""
        self.latitude = None
        self.longitude = None
        self.fix_quality = 0

    def update(self):
        """Read GPS data and update coordinates"""
        data = self.uart.read_data()
        if not data:
            return

        self.buffer += data

        # Process complete sentences
        while '\n' in self.buffer or '\r' in self.buffer:
            # Find line end
            cr_pos = self.buffer.find('\r')
            lf_pos = self.buffer.find('\n')
            end_pos = min(p for p in [cr_pos, lf_pos] if p >= 0)

            sentence = self.buffer[:end_pos].strip()
            self.buffer = self.buffer[end_pos + 1:]

            if sentence.startswith('$') and '*' in sentence:
                self._parse_sentence(sentence)

    def _parse_sentence(self, sentence):
        """Parse NMEA sentence for coordinates"""
        try:
            # Validate checksum
            parts = sentence.split('*')
            if len(parts) != 2:
                return

            data_part = parts[0][1:]  # Remove '$'
            checksum_str = parts[1][:2]

            # Calculate checksum
            calc_checksum = 0
            for char in data_part:
                calc_checksum ^= ord(char)

            if calc_checksum != int(checksum_str, 16):
                return  # Invalid checksum

            # Parse GGA sentences (best for coordinates)
            if sentence.startswith('$GNGGA') or sentence.startswith('$GPGGA'):
                self._parse_gga(sentence)

        except:
            pass  # Ignore parsing errors

    def _parse_gga(self, sentence):
        """Parse GGA sentence for lat/lon"""
        try:
            parts = sentence.split(',')
            if len(parts) < 15:
                return

            # Extract fix quality
            quality = int(parts[6]) if parts[6] else 0
            self.fix_quality = quality

            if quality == 0:  # No fix
                return

            # Extract coordinates
            lat_str = parts[2]
            lat_dir = parts[3]
            lon_str = parts[4]
            lon_dir = parts[5]

            if lat_str and lon_str:
                # Convert from DDMM.MMMM to decimal degrees
                lat = self._nmea_to_decimal(lat_str, lat_dir)
                lon = self._nmea_to_decimal(lon_str, lon_dir)

                if lat is not None and lon is not None:
                    self.latitude = lat
                    self.longitude = lon

        except:
            pass

    def _nmea_to_decimal(self, coord_str, direction):
        """Convert NMEA coordinate to decimal degrees"""
        try:
            if not coord_str or not direction:
                return None

            # Find decimal point
            dot_pos = coord_str.find('.')
            if dot_pos < 3:
                return None

            # Extract degrees and minutes
            degrees = float(coord_str[:dot_pos-2])
            minutes = float(coord_str[dot_pos-2:])

            # Convert to decimal
            decimal = degrees + minutes / 60.0

            # Apply direction
            if direction in ['S', 'W']:
                decimal = -decimal

            return decimal

        except:
            return None

    def has_fix(self):
        """Check if GPS has a valid fix"""
        return self.fix_quality > 0

    def get_coordinates(self):
        """Get current coordinates"""
        if self.has_fix():
            return self.latitude, self.longitude
        return None, None


def main():
    """Main GPS coordinate reader"""
    print("GPS Coordinate Reader")
    print("Initializing...")

    # Initialize hardware
    uart = SC16IS750(spi_bus=1, cs_pin="P3")
    uart.init_gps()

    # Initialize GPS
    gps = GPS(uart)

    print("Ready. Searching for GPS fix...")
    print("(Move to outdoor location with clear sky view)")
    print("-" * 50)

    last_fix_time = 0

    try:
        while True:
            # Update GPS data
            gps.update()

            # Check for fix every second
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_fix_time) > 1000:
                last_fix_time = current_time

                if gps.has_fix():
                    lat, lon = gps.get_coordinates()
                    if lat is not None and lon is not None:
                        print(f"LAT: {lat:.6f}, LON: {lon:.6f}")
                else:
                    print("Searching for satellites...")

            time.sleep_ms(100)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
