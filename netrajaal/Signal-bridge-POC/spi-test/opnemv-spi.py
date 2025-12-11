from machine import SPI, Pin
import time

# Example: SPI2 supports slave mode on RT1062 OpenMV boards
spi = SPI(2,
          baudrate=1000000,
          polarity=0,
          phase=0,
          bits=8,
          firstbit=SPI.MSB,
          mode=SPI.SLAVE,
          sck=Pin("P2"),
          mosi=Pin("P0"),
          miso=Pin("P1"))

cs = Pin("P3", Pin.IN)  # chip select from ESP32

rx_buf = bytearray(4)   # incoming bytes
tx_buf = bytearray([0xAA, 0x55, 0x11, 0x22])  # example reply

print("OpenMV SPI Slave ready...")

while True:
    # Wait for CS LOW = active
    if cs.value() == 0:
        # Perform full-duplex transfer
        spi.write_readinto(tx_buf, rx_buf)

        print("Received:", [hex(b) for b in rx_buf])
        print("Sent:", [hex(b) for b in tx_buf])

        # Optional: modify reply based on input
        tx_buf[0] = rx_buf[0] ^ 0xFF   # example response logic

    time.sleep_ms(10)

