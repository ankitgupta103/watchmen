# openmv_spi_master.py  (run on the OpenMV Cam RT)
from machine import SPI, Pin
import time

# Use SPI(2) or whichever bus your OpenMV board exposes for SPI master
spi = SPI(2,
          baudrate=1000000,   # 1 MHz (match ESP32)
          polarity=0,
          phase=0,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin("P2"),
          mosi=Pin("P0"),
          miso=Pin("P1"))

cs = Pin("P3", Pin.OUT, value=1)  # Chip select (active low)

TRANSFER_SIZE = 64

def master_transaction(tx_bytes):
    # tx_bytes must be a buffer of TRANSFER_SIZE bytes
    rx = bytearray(TRANSFER_SIZE)
    cs.value(0)  # pull CS low
    spi.write_readinto(tx_bytes, rx)  # full-duplex transfer
    cs.value(1)  # release CS
    return rx

count = 0
while True:
    tx = bytearray([0]*TRANSFER_SIZE)
    # populate tx with a simple payload
    for i in range(TRANSFER_SIZE):
        tx[i] = (i + (count & 0xFF)) & 0xFF
    rx = master_transaction(tx)
    print("Sent:", [hex(b) for b in tx[:8]], "...")
    print("Recv:", [hex(b) for b in rx[:8]], "...")
    count += 1
    time.sleep_ms(200)
