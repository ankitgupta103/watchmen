"""
OpenMV RT1062 SPI Master - Simple Communication with ESP32
"""

from machine import SPI, Pin
import time

# Pin Configuration - CS pin (P10 is default for SPI1, but using P3 as currently connected)
cs = Pin("P3", Pin.OUT, value=1)

# SPI Configuration
BUFFER_SIZE = 32
spi = SPI(1, baudrate=1000000, polarity=0, phase=0)

print("OpenMV SPI Master initialized")

counter = 0

while True:
    try:
        # Prepare TX buffer with message
        tx_buffer = bytearray(BUFFER_SIZE)
        message = f"Hello #{counter}"
        tx_buffer[:len(message)] = message.encode('utf-8')
        
        # Prepare RX buffer
        rx_buffer = bytearray(BUFFER_SIZE)
        
        # SPI transaction
        cs.low()
        spi.write_readinto(tx_buffer, rx_buffer)
        cs.high()
        
        # Print results
        print(f"TX: {message}")
        print(f"RX: {bytes(rx_buffer).hex()}")
        print(f"RX (text): {bytes(rx_buffer).decode('utf-8', errors='ignore')[:BUFFER_SIZE]}\n")
        
        counter += 1
        time.sleep_ms(500)
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
