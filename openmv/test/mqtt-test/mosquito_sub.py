import time
from machine import SPI, Pin

# ========== CONFIG ==========
SPI_BUS = 1
CS_PIN = "P3"
BAUDRATE = 921600
BROKER = "broker.hivemq.com"
PORT = 1883
CLIENT_ID = "modem-client"
TOPIC = "openmv/test"
APN = "airtelgprs.com"  # Change to your SIM provider's APN
# ============================

# --- SC16IS750 Driver ---
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

    def __init__(self, spi_bus, cs_pin, baudrate=921600):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=1000000, polarity=0, phase=0)
        self.init_uart(baudrate)

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

    def init_uart(self, baudrate):
        self.reset_device()
        self.set_baudrate(baudrate)
        self.set_line()
        self.enable_fifo()

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

# --- Helper Functions ---
def send_at(uart, cmd, delay=1.5):
    print(f">> {cmd}")
    for b in cmd.encode():
        uart.write(b)
    uart.write(13)  # Carriage return
    time.sleep(delay)

    res = ""
    for _ in range(100):
        c = uart.read()
        if c != -1:
            res += chr(c)
        else:
            time.sleep(0.05)
    print("<<", res)
    return res

# --- Main ---
print("Initializing SC16IS750...")
uart = SC16IS750(spi_bus=SPI_BUS, cs_pin=CS_PIN, baudrate=BAUDRATE)

if uart.ping():
    print("SC16IS750 connected!")
else:
    print("SC16IS750 not responding.")
    raise SystemExit

# --- Initialize Modem and MQTT ---
send_at(uart, "AT")  # basic check
send_at(uart, f'AT+CGDCONT=1,"IP","{APN}"')  # set APN
send_at(uart, "AT+CGACT=1,1")  # activate PDP

send_at(uart, "AT+CMQTTSTART")
send_at(uart, f'AT+CMQTTACCQ=0,"{CLIENT_ID}"')
send_at(uart, f'AT+CMQTTCONNECT=0,"tcp://{BROKER}:{PORT}",60,1')

# --- Publish MQTT Message ---
topic = TOPIC
message = "Hello from modem"

send_at(uart, f'AT+CMQTTTOPIC=0,{len(topic)}')
send_at(uart, topic)

send_at(uart, f'AT+CMQTTPAYLOAD=0,{len(message)}')
send_at(uart, message)

send_at(uart, "AT+CMQTTPUB=0,1,60")

print("MQTT message published!")
