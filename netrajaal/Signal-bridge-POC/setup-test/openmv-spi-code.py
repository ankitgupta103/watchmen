"""
OpenMV RT1062 SPI Master Code
Bidirectional SPI communication with ESP32

Uses standard OpenMV SPI API
"""

from machine import SPI, Pin
import time

# Pin Configuration
cs = Pin("P3", Pin.OUT, value=1)  # CS pin, active low, start high

# SPI Configuration
BAUDRATE = 1000000  # 1 MHz
spi = SPI(1, baudrate=BAUDRATE, polarity=0, phase=0)

print("OpenMV SPI Master initialized")
print(f"SPI: {spi}")
print()

def spi_transfer(tx_data, rx_length=None):
    """
    Standard SPI transfer: send and receive data
    tx_data: bytes to send
    rx_length: number of bytes to receive (default: same as tx_data length)
    Returns: bytes received
    """
    if rx_length is None:
        rx_length = len(tx_data)
    
    # Prepare receive buffer
    rx_buffer = bytearray(rx_length)
    
    # CS low (select slave)
    cs.low()
    time.sleep_us(5)  # CS setup time
    
    try:
        # Write and read simultaneously
        if len(tx_data) == rx_length:
            # Same length: use write_readinto
            spi.write_readinto(tx_data, rx_buffer)
        else:
            # Different lengths: write first, then read
            if len(tx_data) > 0:
                spi.write(tx_data)
            if rx_length > 0:
                spi.readinto(rx_buffer, 0x00)
    finally:
        time.sleep_us(5)  # CS hold time
        cs.high()  # Deselect slave
    
    return bytes(rx_buffer)

def send_binary(data):
    """
    Send binary data and receive response of same length
    data: bytes to send
    Returns: bytes received
    """
    return spi_transfer(data, len(data))

def send_text(text, rx_size=64):
    """
    Send text string and receive text response
    text: string to send
    rx_size: number of bytes to receive (default 64)
    Returns: bytes received
    """
    # Convert text to bytes
    tx_bytes = text.encode('utf-8')
    
    # Pad or truncate to match rx_size
    if len(tx_bytes) < rx_size:
        tx_bytes = tx_bytes + b'\x00' * (rx_size - len(tx_bytes))
    else:
        tx_bytes = tx_bytes[:rx_size]
    
    return spi_transfer(tx_bytes, rx_size)

def bytes_to_text(data):
    """
    Convert bytes to text string, handling null terminators
    data: bytes to convert
    Returns: string
    """
    try:
        # Find null terminator
        null_pos = data.find(0)
        if null_pos != -1:
            data = data[:null_pos]
        # Filter out non-printable characters for display
        text = data.decode('utf-8', errors='ignore')
        # Remove non-printable characters except common whitespace
        filtered = ''.join(c if (32 <= ord(c) < 127) or c in '\n\r\t' else '' for c in text)
        return filtered
    except:
        return str(data)

def receive_text(rx_size=64):
    """
    Receive text from ESP32 (send zeros to trigger response)
    rx_size: number of bytes to receive
    Returns: bytes received
    """
    tx_bytes = b'\x00' * rx_size
    return spi_transfer(tx_bytes, rx_size)

# Main loop
print("Starting SPI communication...")
print()

counter = 0
while True:
    try:
        print(f"--- Transfer #{counter} ---")
        
        # Test 1: Binary data (4 bytes) - quick handshake
        tx_bin = bytes([0x01, 0x02, 0x03, counter & 0xFF])
        print(f"TX (bin): {[hex(b) for b in tx_bin]}")
        
        rx_bin = send_binary(tx_bin)
        print(f"RX (bin): {[hex(b) for b in rx_bin]}")
        
        # Try to interpret as text if possible
        rx_text_bin = bytes_to_text(rx_bin)
        if rx_text_bin and len(rx_text_bin.strip()) > 0:
            print(f"RX (text from binary): '{rx_text_bin}'")
        print()
        
        # Test 2: Text data (64 bytes) - full bidirectional text communication
        tx_text = f"Hello ESP32 #{counter}"
        print(f"TX (text): '{tx_text}'")
        
        rx_bytes = send_text(tx_text, rx_size=64)
        
        # Show first 30 bytes in hex for debugging
        hex_preview = [hex(b) for b in rx_bytes[:30]]
        print(f"RX (hex): {hex_preview}...")
        
        rx_text = bytes_to_text(rx_bytes)
        print(f"RX (text): '{rx_text}'")
        print()
        
        counter += 1
        time.sleep_ms(500)
        
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.print_exception(e)
        time.sleep(1)
