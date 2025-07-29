import time
from machine import SPI, Pin

class SC16IS750:
    # Register map
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
            pass
        self._write_register(self.REG_THR, byte)

    def ping(self):
        self._write_register(self.REG_SPR, 0x55)
        if self._read_register(self.REG_SPR) != 0x55:
            return False
        self._write_register(self.REG_SPR, 0xAA)
        if self._read_register(self.REG_SPR) != 0xAA:
            return False
        return True


class GPSModule:
    def __init__(self, spi_bus=1, cs_pin="P3", baudrate=9600):
        print("Initializing GPS module...")
        self.uart = SC16IS750(spi_bus, cs_pin)
        self.uart.reset_device()
        self.uart.set_baudrate(baudrate)
        self.uart.set_line()
        self.uart.enable_fifo()
        if not self.uart.ping():
            raise Exception("SC16IS750 not responding.")
        print("GPS module initialized and ready.")
        self.buffer = ""

    def _read_line(self):
        while True:
            byte = self.uart.read()
            if byte != -1:
                ch = chr(byte)
                self.buffer += ch
                if ch == '\n':
                    line = self.buffer.strip()
                    self.buffer = ""
                    return line
            else:
                time.sleep_ms(5)

    def get_sentence(self, prefix="$GNGGA"):
        while True:
            line = self._read_line()
            if line.startswith(prefix):
                return line

    def get_all_sentences(self, duration=1.0):
        start = time.ticks_ms()
        sentences = []
        while time.ticks_diff(time.ticks_ms(), start) < int(duration * 1000):
            line = self._read_line()
            sentences.append(line)
        return sentences
