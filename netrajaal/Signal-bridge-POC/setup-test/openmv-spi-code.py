"""
OpenMV RT1062 SPI Master - Simple Communication with ESP32
"""

from machine import SPI, Pin
import time

# Pin Configuration - Explicitly set pins to match physical connections
cs = Pin("P3", Pin.OUT, value=1)

# SPI Configuration - Explicitly specify pins: MOSI=P0, MISO=P1, SCK=P2
BUFFER_SIZE = 32
spi = SPI(1, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB, sck=Pin("P2"), mosi=Pin("P0"), miso=Pin("P1"))

print("OpenMV SPI Master initialized")

counter = 0

while True:
    try:
        # Prepare TX buffer with message
        tx_buffer = bytearray(BUFFER_SIZE)
        message = f"Hello #{counter}"
        tx_buffer[:len(message)] = message.encode('utf-8')
        
        # Prepare RX buffer (initialize to zeros)
        rx_buffer = bytearray(BUFFER_SIZE)
        
        # SPI transaction
        cs.low()
        time.sleep_us(10)  # Small delay for slave to detect CS
        spi.write_readinto(tx_buffer, rx_buffer)
        time.sleep_us(10)  # Small delay before releasing CS
        cs.high()
        
        # Print results
        print(f"TX: {message}")
        rx_bytes = bytes(rx_buffer)
        print(f"RX: {rx_bytes.hex()}")
        # Find null terminator or end of data
        rx_text = rx_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        print(f"RX (text): {rx_text}\n")
        
        counter += 1
        time.sleep_ms(500)
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
