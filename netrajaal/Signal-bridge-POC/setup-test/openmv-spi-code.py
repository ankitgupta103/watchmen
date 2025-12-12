"""
OpenMV RT1062 SPI Master Code
Bidirectional SPI communication with ESP32
"""

from machine import SPI, Pin
import time

# Pin Configuration
cs = Pin("P3", Pin.OUT, value=1)

# SPI Configuration
BAUDRATE = 1000000  # 1 MHz
spi = SPI(1, baudrate=BAUDRATE, polarity=0, phase=0)

print("OpenMV SPI Master initialized\n")

def spi_transfer(tx_data, rx_length=None):
    """SPI transfer: send and receive data simultaneously"""
    if rx_length is None:
        rx_length = len(tx_data)
    
    rx_buffer = bytearray(rx_length)
    
    # Ensure tx and rx lengths match
    if len(tx_data) < rx_length:
        tx_padded = tx_data + b'\x00' * (rx_length - len(tx_data))
    elif len(tx_data) > rx_length:
        tx_padded = tx_data[:rx_length]
    else:
        tx_padded = tx_data
    
    cs.low()
    time.sleep_us(10)
    
    try:
        spi.write_readinto(tx_padded, rx_buffer)
    finally:
        time.sleep_us(10)
        cs.high()
        time.sleep_us(5)
    
    return bytes(rx_buffer)

def send_binary(data):
    """Send binary data and receive response"""
    return spi_transfer(data, len(data))

def send_text(text, rx_size=64):
    """Send text string and receive response"""
    tx_bytes = text.encode('utf-8')
    
    # Pad to match rx_size
    if len(tx_bytes) < rx_size:
        tx_bytes = tx_bytes + b'\x00' * (rx_size - len(tx_bytes))
    else:
        tx_bytes = tx_bytes[:rx_size]
    
    return spi_transfer(tx_bytes, rx_size)

def bytes_to_text(data):
    """Convert bytes to text string"""
    try:
        # Find null terminator
        null_pos = data.find(0)
        if null_pos != -1:
            data = data[:null_pos]
        
        # Decode to string
        text = data.decode('utf-8', errors='ignore')
        
        # Remove only control characters (keep printable ASCII 32-126 and common whitespace)
        # This is less aggressive - only removes actual control chars
        filtered = ''.join(c for c in text if (32 <= ord(c) <= 126) or c in '\n\r\t')
        
        return filtered.strip() if filtered else ""
    except:
        return ""

def receive_text(rx_size=64):
    """Read response from ESP32 (send zeros to trigger response)"""
    tx_bytes = b'\x00' * rx_size
    return spi_transfer(tx_bytes, rx_size)

# Main loop
print("Starting SPI communication...\n")

counter = 0
while True:
    try:
        print(f"--- Transfer #{counter} ---")
        
        # Binary handshake (4 bytes)
        tx_bin = bytes([0x01, 0x02, 0x03, counter & 0xFF])
        rx_bin = send_binary(tx_bin)
        rx_text_bin = bytes_to_text(rx_bin)
        if rx_text_bin and len(rx_text_bin.strip()) > 0:
            print(f"TX (binary): {[hex(b) for b in tx_bin]}")
            print(f"RX: '{rx_text_bin}'\n")
        
        time.sleep_ms(10)
        
        # Text communication
        tx_text = f"Hello ESP32 #{counter}"
        print(f"TX: '{tx_text}'")
        
        # Send text message
        rx_bytes_send = send_text(tx_text, rx_size=64)
        rx_text_send = bytes_to_text(rx_bytes_send)
        if rx_text_send and len(rx_text_send.strip()) > 0:
            print(f"RX (during send): '{rx_text_send}'")
        
        # Wait for ESP32 to prepare response
        time.sleep_ms(50)
        
        # Read response
        rx_bytes = receive_text(rx_size=64)
        rx_text = bytes_to_text(rx_bytes)
        
        if rx_text and len(rx_text.strip()) > 0:
            print(f"RX: '{rx_text}'\n")
        else:
            # Fallback: try to extract text directly
            try:
                null_pos = rx_bytes.find(0)
                if null_pos > 0:
                    raw_text = rx_bytes[:null_pos].decode('utf-8', errors='ignore').strip()
                    if raw_text:
                        print(f"RX: '{raw_text}'\n")
                    else:
                        print(f"RX: [No response]\n")
                else:
                    print(f"RX: [No response]\n")
            except:
                print(f"RX: [No response]\n")
        
        counter += 1
        time.sleep_ms(500)
        
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.print_exception(e)
        time.sleep(1)
