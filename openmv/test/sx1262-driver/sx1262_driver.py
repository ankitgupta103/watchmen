from machine import Pin, SPI
import time

# --- Pin setup ---
cs    = Pin('P3', Pin.OUT)
busy  = Pin('P7', Pin.IN)
reset = Pin('P6', Pin.OUT)  # Changed P6 reset
dio1  = Pin('P13', Pin.IN)

# SPI init (OpenMV SPI1)
spi = SPI(1, baudrate=8000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)

# --- Low-level helpers ---
def wait_busy():
    while busy.value() == 1:
        pass

def sx1262_reset():
    reset.value(0)
    time.sleep_ms(1)
    reset.value(1)
    time.sleep_ms(10)

def write_cmd(cmd, data=[]):
    wait_busy()
    cs.value(0)
    spi.write(bytearray([cmd] + data))
    cs.value(1)
    wait_busy()

def read_cmd(cmd, nbytes, dummy=0x00):
    wait_busy()
    cs.value(0)
    spi.write(bytearray([cmd, dummy]))
    val = spi.read(nbytes, 0x00)
    cs.value(1)
    wait_busy()
    return val

def write_register(addr, value):
    write_cmd(0x0D, [(addr >> 8) & 0xFF, addr & 0xFF, value])

def read_register(addr):
    wait_busy()
    cs.value(0)
    spi.write(bytearray([0x1D, (addr >> 8) & 0xFF, addr & 0xFF, 0x00]))
    val = spi.read(1, 0x00)
    cs.value(1)
    wait_busy()
    return val[0]

# --- LoRa config ---
def set_standby():
    write_cmd(0x80, [0x00])  # STDBY_RC

def set_packet_type():
    write_cmd(0x8A, [0x01])  # LoRa packet type

def set_rf_frequency(freq_hz):
    frf = int(freq_hz / (32e6 / (1 << 25)))
    write_cmd(0x86, [(frf >> 24) & 0xFF, (frf >> 16) & 0xFF, (frf >> 8) & 0xFF, frf & 0xFF])

def set_modulation_params(sf=7, bw=0x04, cr=0x01):
    # bw: 0x04 = 125kHz, cr: 0x01 = 4/5
    write_cmd(0x8B, [sf, bw, cr, 0x00])  # Low data rate optimize off

def set_packet_params(preamble_len=12, payload_len=16):
    write_cmd(0x8C, [
        (preamble_len >> 8) & 0xFF, preamble_len & 0xFF,
        0x00,  # Explicit header
        payload_len,
        0x00,  # CRC on
        0x00   # IQ standard
    ])

def set_tx_power(power=14):
    write_cmd(0x8E, [power])

def write_fifo(data):
    write_cmd(0x0E, [0x00])  # FIFO base addr = 0
    write_cmd(0x0F, [0x00])  # FIFO ptr = 0
    write_cmd(0x00, data)    # Write payload

def read_fifo(size):
    write_cmd(0x0F, [0x00])
    return read_cmd(0x00, size)

def set_tx(timeout_ms=3000):
    timeout_ticks = int(timeout_ms / 15.625)
    write_cmd(0x83, [(timeout_ticks >> 8) & 0xFF, timeout_ticks & 0xFF])

def set_rx(timeout_ms=0):
    if timeout_ms == 0:
        write_cmd(0x82, [0xFF, 0xFF])  # Continuous RX
    else:
        timeout_ticks = int(timeout_ms / 15.625)
        write_cmd(0x82, [(timeout_ticks >> 8) & 0xFF, timeout_ticks & 0xFF])

# --- Init ---
sx1262_reset()
print("Chip version:", hex(read_register(0x0918)))  # should not be 0xFF

set_standby()
set_packet_type()
set_rf_frequency(868100000)
set_modulation_params(sf=7, bw=0x04, cr=0x01)
set_packet_params(preamble_len=12, payload_len=5)
set_tx_power(14)

# --- Choose mode ---
SEND_MODE = True  # Set False for receiver

if SEND_MODE:
    while True:
        msg = b"Hello"
        write_fifo(list(msg))
        set_tx()
        print("Sent:", msg)
        time.sleep(2)

else:
    set_rx()
    while True:
        if dio1.value() == 1:
            payload = read_fifo(5)
            print("Received:", payload)
            set_rx()
