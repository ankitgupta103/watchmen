"""
OpenMV RT1062 SPI Master - Simple Communication with ESP32
"""

from machine import SPI, Pin
import time

# Pin Configuration - Explicitly set pins to match physical connections
cs = Pin("P3", Pin.OUT, value=1)

# SPI Configuration - Explicitly specify pins: MOSI=P0, MISO=P1, SCK=P2
BUFFER_SIZE = 32
spi = SPI(
    1,
    baudrate=1000000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin("P2"),
    mosi=Pin("P0"),
    miso=Pin("P1"),
)

print("OpenMV SPI Master initialized")

counter = 0

while True:
    try:
        # --- Transaction 1: send message, ESP32 prepares response for next txn ---
        tx1 = bytearray(BUFFER_SIZE)
        msg = f"Hello #{counter}"
        tx1[: len(msg)] = msg.encode("utf-8")
        rx1 = bytearray(BUFFER_SIZE)

        cs.low()
        time.sleep_us(5)
        spi.write_readinto(tx1, rx1)
        time.sleep_us(5)
        cs.high()

        # --- Transaction 2: dummy write to read ESP32 response from previous txn ---
        tx2 = bytearray(BUFFER_SIZE)  # all zeros
        rx2 = bytearray(BUFFER_SIZE)

        time.sleep_us(50)  # brief gap between transactions
        cs.low()
        time.sleep_us(5)
        spi.write_readinto(tx2, rx2)
        time.sleep_us(5)
        cs.high()

        # Show what we sent and what we received (response expected in rx2)
        print(f"TX: {msg}")
        rx_bytes = bytes(rx2)
        print(f"RX: {rx_bytes.hex()}")
        rx_text = rx_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
        print(f"RX (text): {rx_text}\n")

        counter += 1
        time.sleep_ms(500)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
