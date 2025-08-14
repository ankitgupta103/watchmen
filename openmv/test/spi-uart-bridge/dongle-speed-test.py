from machine import SPI, Pin
import time

# SC16IS750 Register Addresses
RHR = 0x00  # Receive Holding Register (read)
THR = 0x00  # Transmit Holding Register (write)
FCR = 0x02  # FIFO Control Register
LCR = 0x03  # Line Control Register
LSR = 0x05  # Line Status Register
MCR = 0x04  # Modem Control Register
DLL = 0x00  # Divisor Latch LSB
DLH = 0x01  # Divisor Latch MSB
EFR = 0x02  # Enhanced Features Register
SPR = 0x07  # Scratchpad (used for ping)
TXLVL = 0x08
RXLVL = 0x09
IOCONTROL = 0x0E

CRYSTAL_FREQ = 14745600
BAUDRATE = 115200

# Initialize SPI
spi = SPI(1, baudrate=8000000, polarity=0, phase=0)
cs = Pin("P3", Pin.OUT)
cs.high()

def write_register(reg, val):
    cs.low()
    spi.write(bytearray([(reg << 3) & 0xF8]))  # Write command
    spi.write(bytearray([val]))
    cs.high()
    time.sleep_us(10)

def read_register(reg):
    cs.low()
    spi.write(bytearray([0x80 | ((reg << 3) & 0xF8)]))  # Read command
    val = spi.read(1)[0]
    cs.high()
    time.sleep_us(10)
    return val

def reset_device():
    iocontrol = read_register(IOCONTROL)
    write_register(IOCONTROL, iocontrol | 0x08)  # Reset FIFO and registers

def set_baudrate(baudrate):
    prescaler = 1 if (read_register(MCR) & 0x80) == 0 else 4
    divisor = int((CRYSTAL_FREQ / prescaler) / (baudrate * 16))
    lcr = read_register(LCR)
    write_register(LCR, lcr | 0x80)  # Enable divisor latch
    write_register(DLL, divisor & 0xFF)
    write_register(DLH, (divisor >> 8) & 0xFF)
    write_register(LCR, lcr & 0x7F)  # Disable divisor latch

def init_uart():
    print("Initializing SC16IS750...")
    reset_device()
    write_register(FCR, 0x07)  # Enable and reset FIFO
    set_baudrate(BAUDRATE)
    write_register(LCR, 0x03)  # 8N1 config
    print("SC16IS750 connected!")

def uart_write(data):
    for b in data:
        while (read_register(LSR) & 0x20) == 0:  # Wait for THR empty
            pass
        write_register(THR, b)

def uart_available():
    return read_register(RXLVL)

def uart_read_all():
    buffer = bytearray()
    while uart_available():
        buffer.append(read_register(RHR))
    return buffer

def send_at(command, delay=500):
    print(f"\n>> Sending: {command}")
    uart_write(command.encode('utf-8') + b"\r\n")
    time.sleep_ms(delay)
    response = uart_read_all()
    # print("<< Received:", response.decode(errors='replace'))
    print("<< Received:", response.decode('utf-8', 'ignore'))


# --- MAIN ---

init_uart()
print("Listening for SIM7600 responses...")

# Optional: test SIM7600 connectivity
send_at("AT")          # Should return "OK"
send_at("AT+CSQ")      # Signal Quality
send_at("AT+CREG?")    # Network registration
send_at("ATI")         # Module info
