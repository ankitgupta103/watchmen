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
    
    # Pull CS low - minimal delay for slave to detect CS
    cs.low()
    time.sleep_us(5)
    
    try:
        # Perform the SPI transaction
        spi.write_readinto(tx_padded, rx_buffer)
    finally:
        # Keep CS low briefly to ensure transaction completes
        time.sleep_us(5)
        cs.high()
        # Small delay after CS high for slave to process
        time.sleep_us(10)
    
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
        if not data:
            return ""
        
        # Find null terminator or end of printable data
        null_pos = data.find(0)
        if null_pos != -1:
            data = data[:null_pos]
        
        # If no null terminator, find first non-printable character
        if null_pos == -1:
            for i, byte in enumerate(data):
                if byte < 32 and byte not in [9, 10, 13]:  # Not printable and not tab/lf/cr
                    data = data[:i]
                    break
        
        # Decode to string
        text = data.decode('utf-8', errors='ignore')
        
        # Remove only control characters (keep printable ASCII 32-126 and common whitespace)
        # This is less aggressive - only removes actual control chars
        filtered = ''.join(c for c in text if (32 <= ord(c) <= 126) or c in '\n\r\t')
        
        return filtered.strip() if filtered else ""
    except:
        return ""

def receive_text(rx_size=64):
    """Read response from ESP32 (send read request command)"""
    # Send 0xFF as read request command (ESP32 recognizes this)
    # Using 0xFF instead of 0x00 because SPI driver drives MISO better with non-zero data
    tx_bytes = b'\xFF' + b'\x00' * (rx_size - 1)
    return spi_transfer(tx_bytes, rx_size)

# Main loop
print("Starting SPI communication...\n")

counter = 0
# First transaction to get initial "ESP32 Ready" message
print("--- Initial handshake ---")
init_rx = send_text("", rx_size=64)
print(f"Initial RX (all bytes): {init_rx}\n")
init_text = bytes_to_text(init_rx)
if init_text:
    print(f"Initial RX (text): '{init_text}'\n")
else:
    # Show raw bytes
    printable = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in init_rx[:40])
    print(f"Initial RX (raw): {init_rx[:40]}\n")
    print(f"Initial RX (printable): '{printable}'\n")
    # Check if all zeros (no response)
    if all(b == 0 for b in init_rx):
        print("WARNING: Received all zeros - ESP32 may not be responding\n")

time.sleep_ms(50)

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
        else:
            # Show raw bytes for debugging
            printable = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in rx_bin[:20])
            print(f"TX (binary): {[hex(b) for b in tx_bin]}")
            print(f"RX (raw): {rx_bin[:20]}\n")
            print(f"RX (printable): '{printable}'\n")
        
        time.sleep_ms(20)
        
        # Text communication
        # ESP32 prepares response AFTER receiving data, so response is one transaction behind
        # We need TWO transactions:
        # 1. Send our message (ESP32 prepares response for next transaction)
        # 2. Send dummy data to get the response
        tx_text = f"Hello ESP32 #{counter}"
        print(f"TX: '{tx_text}'")
        
        # Transaction 1: Send message (ESP32 will prepare response)
        rx_bytes1 = send_text(tx_text, rx_size=64)
        time.sleep_ms(10)
        
        # Transaction 2: Send dummy to get response to our message
        # ESP32 prepared response after transaction 1, so it's ready now
        rx_bytes2 = send_text(b'\x00' * 64, rx_size=64)
        
        # Check both responses - response should be in rx_bytes2
        rx_text1 = bytes_to_text(rx_bytes1)
        rx_text2 = bytes_to_text(rx_bytes2)
        
        # Response should be in rx_bytes2 (response to our message)
        if rx_text2 and len(rx_text2.strip()) > 0:
            print(f"RX: '{rx_text2}'\n")
        elif rx_text1 and len(rx_text1.strip()) > 0:
            # Fallback: maybe response came in first transaction
            print(f"RX: '{rx_text1}'\n")
        else:
            # Debug: show both raw responses
            print(f"RX1 (all bytes): {rx_bytes1}\n")
            print(f"RX2 (all bytes): {rx_bytes2}\n")
            printable1 = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in rx_bytes1[:40])
            printable2 = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in rx_bytes2[:40])
            print(f"RX1 (printable): '{printable1}'\n")
            print(f"RX2 (printable): '{printable2}'\n")
            # Check if all zeros
            if all(b == 0 for b in rx_bytes1) and all(b == 0 for b in rx_bytes2):
                print(f"RX: [No response - all zeros]\n")
            else:
                print(f"RX: [No readable response]\n")
        
        counter += 1
        time.sleep_ms(500)
        
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.print_exception(e)
        time.sleep(1)
