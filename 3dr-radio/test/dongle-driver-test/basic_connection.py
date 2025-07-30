import time
from machine import SPI, Pin

class SC16IS750:
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
            pass
        self._write_register(self.REG_THR, byte)

    def write_str(self, data):
        for char in data:
            self.write(ord(char))

    def readline(self, timeout=3000):
        start = time.ticks_ms()
        line = b""
        while time.ticks_diff(time.ticks_ms(), start) < timeout:
            if self.available():
                byte = self.read()
                if byte in (10, 13):  # \n or \r
                    if line:
                        return line.decode('utf-8', 'ignore')
                else:
                    line += bytes([byte])
            time.sleep_ms(10)
        return line.decode('utf-8', 'ignore') if line else None

    def ping(self):
        self._write_register(self.REG_SPR, 0x55)
        if self._read_register(self.REG_SPR) != 0x55:
            return False
        self._write_register(self.REG_SPR, 0xAA)
        if self._read_register(self.REG_SPR) != 0xAA:
            return False
        return True


# ----------------------- Modem Helper Functions -----------------------------

def flush_input():
    while uart_bridge.available():
        uart_bridge.read()
        time.sleep_ms(5)

def send_at(command, wait=3000):
    flush_input()
    print("\nSending:", command)
    uart_bridge.write_str(command + "\r")
    time.sleep_ms(200)

    start = time.ticks_ms()
    lines = []

    while time.ticks_diff(time.ticks_ms(), start) < wait:
        line = uart_bridge.readline(timeout=wait)
        if line:
            line = line.strip()
            if line:
                print("->", line)
                lines.append(line)
                if "OK" in line or "ERROR" in line:
                    break
        time.sleep_ms(10)
    return lines

# ----------------------- Main Setup & AT Sequence -----------------------------

print("Initializing SC16IS750 UART bridge...")

spi_bus = 1
cs_pin = "P3"         # Change if needed
baudrate = 115200     # SIM7600G default

uart_bridge = SC16IS750(spi_bus=spi_bus, cs_pin=cs_pin)
uart_bridge.reset_device()
uart_bridge.set_baudrate(baudrate)
uart_bridge.set_line()
uart_bridge.enable_fifo()

if uart_bridge.ping():
    print("SC16IS750 is connected.")
else:
    print("SC16IS750 not responding.")
    while True:
        pass

# ----------- Step-by-step AT initialization -------------
send_at("AT")                      # Modem alive
send_at("AT+CSQ")                  # Signal strength
send_at("AT+CREG?")                # Network registration
send_at("AT+CGATT?")               # GPRS attachment
send_at("AT+COPS?")                # Operator name

# ----------- Activate Internet (PDP context) -------------
send_at('AT+CGDCONT=1,"IP","airtelgprs.com"')  # Set APN for Airtel
send_at("AT+CGACT=1,1")                        # Activate PDP context
send_at("AT+CIFSR")                            # Get IP address
