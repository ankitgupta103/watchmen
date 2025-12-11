"""
OpenMV RT1062 SPI Controller Code
Bidirectional SPI communication with ESP32 Classic

# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
"""

from machine import SPI, Pin
import time

# Pin Configuration - adjust these based on your OpenMV board
# CS (Chip Select) pin
cs = Pin("P7", Pin.OUT, value=1)  # Active low, start high

# The hardware SPI bus for your OpenMV RT1062 is always SPI bus 1.
# NOTE: The SPI clock frequency will not always be the requested frequency. 
# The hardware only supports frequencies that are the bus frequency divided by 
# a prescaler (which can be 2, 4, 8, 16, 32, 64, 128 or 256).
BAUDRATE = 1000000  # 1 MHz - adjust as needed
spi = SPI(1, baudrate=BAUDRATE, polarity=0, phase=0)

print("OpenMV SPI Controller initialized")
print("SPI Configuration:", spi)

def send_receive_data(tx_data):
    """
    Send data to ESP32 and receive response
    tx_data: bytes to send
    Returns: bytes received
    """
    # Prepare receive buffer
    rx_data = bytearray(len(tx_data))
    
    # Select ESP32 (CS low)
    cs.low()
    time.sleep_us(10)  # Small delay for CS setup
    
    try:
        # Simultaneous write and read
        spi.write_readinto(tx_data, rx_data)
    finally:
        # Deselect ESP32 (CS high)
        time.sleep_us(10)
        cs.high()
    
    return bytes(rx_data)

def send_data(tx_data):
    """
    Send data to ESP32 without reading
    tx_data: bytes to send
    """
    cs.low()
    time.sleep_us(10)
    
    try:
        spi.write(tx_data)
    finally:
        time.sleep_us(10)
        cs.high()

def receive_data(length, write_byte=0x00):
    """
    Receive data from ESP32
    length: number of bytes to receive
    write_byte: byte to send while receiving (usually 0x00)
    Returns: bytes received
    """
    cs.low()
    time.sleep_us(10)
    
    try:
        rx_data = spi.read(length, write_byte)
    finally:
        time.sleep_us(10)
        cs.high()
    
    return rx_data

# Main loop
print("Starting SPI communication...")

counter = 0
while True:
    try:
        # Example 1: Send data and receive response
        tx_buffer = bytes([0x01, 0x02, 0x03, counter & 0xFF])
        print(f"\nSending: {[hex(b) for b in tx_buffer]}")
        
        rx_buffer = send_receive_data(tx_buffer)
        print(f"Received: {[hex(b) for b in rx_buffer]}")
        
        counter += 1
        time.sleep_ms(500)  # Wait 500ms between transfers
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

