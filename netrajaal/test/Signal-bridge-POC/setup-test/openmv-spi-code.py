from machine import SPI, Pin
import time

cs = Pin("P3", Pin.OUT, value=1)

spi = SPI(
    1,
    baudrate=1_000_000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB
)

FRAME_SIZE = 250

print("OpenMV SPI MASTER READY")

def bytes_to_printable(b):
    # Convert bytes to readable ASCII (dot for non-printable)
    return "".join(chr(x) if 32 <= x <= 126 else "." for x in b)

while True:
    tx = bytearray(FRAME_SIZE)   # dummy clocks
    rx = bytearray(FRAME_SIZE)

    cs.low()
    time.sleep_us(1000)
    spi.write_readinto(tx, rx)
    time.sleep_us(5)
    cs.high()

    print("---- RX FRAME (250 bytes) ----")

    # print ASCII view
    ascii_view = bytes_to_printable(rx)
    print("ASCII:")
    print(ascii_view)

    # # Print HEX view (formatted)
    # print("\nHEX:")
    # for i in range(0, FRAME_SIZE, 16):
    #     chunk = rx[i:i+16]
    #     hex_line = " ".join("{:02X}".format(x) for x in chunk)
    #     print("{:03d}: {}".format(i, hex_line))

    print("------------------------------\n")
    time.sleep_ms(299)
