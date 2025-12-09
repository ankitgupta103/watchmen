"""
Simple LoRa Module Configuration and Communication Script
"""

try:
    from machine import Pin, UART
except ImportError:
    print("Error: machine module not found. This script requires OpenMV or MicroPython.")
    raise

import time

# Operation Mode: "configure", "read", or "write"
MODE = "configure"

def configure():
    """Configure module with persistent settings (hardcoded values)"""
    # Hardcoded configuration values
    freq = 868
    addr = 100
    power = 22
    rssi = False
    air_speed = 2400
    net_id = 0
    buffer_size = 240
    crypt = 0
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    
    # Calculate frequency offset
    freq_offset = freq - 850  # 868 - 850 = 18
    
    # Initialize GPIO
    m0_pin = Pin(m0_pin_str, Pin.OUT)
    m1_pin = Pin(m1_pin_str, Pin.OUT)
    
    # Enter config mode
    m0_pin.value(0)
    m1_pin.value(1)
    time.sleep_ms(100)
    
    # Initialize UART at 9600 baud
    uart = UART(uart_num, 9600, timeout=2000)
    time.sleep_ms(500)
    
    # Build configuration (12 bytes)
    cfg_reg = [
        0xC0,  # Persistent header
        0x00,  # Length high
        0x09,  # Length low
        (addr >> 8) & 0xFF,  # Address high
        addr & 0xFF,  # Address low
        net_id,  # Network ID
        0xE0 + 0x02,  # UART 115200 + Air 2400
        0x00 + 0x00 + 0x20,  # Buffer 240 + Power 22 + RSSI noise
        freq_offset,  # Frequency offset
        0x43 + (0x80 if rssi else 0x00),  # Mode + RSSI
        (crypt >> 8) & 0xFF,  # Crypt high
        crypt & 0xFF  # Crypt low
    ]
    
    # Clear buffer
    while uart.any():
        uart.read()
    
    # Send configuration
    uart.write(bytes(cfg_reg))
    time.sleep_ms(300)
    
    # Get response
    if uart.any():
        time.sleep_ms(200)
        response = uart.read()
        print("Raw response:", [hex(x) for x in response] if response else "None")
        if response and len(response) > 0 and response[0] == 0xC1:
            print("Configuration successful")
        else:
            print("Configuration failed")
    else:
        print("No response")
    
    # Reopen at 115200 baud
    uart.deinit()
    time.sleep_ms(300)
    m0_pin.value(0)
    m1_pin.value(1)
    time.sleep_ms(500)
    uart = UART(uart_num, 115200, timeout=2000)
    while uart.any():
        uart.read()
    time.sleep_ms(30)
    
    # Exit config mode
    m0_pin.value(0)
    m1_pin.value(0)
    time.sleep_ms(100)

def get_response():
    """Get response from module and print raw"""
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    
    m0_pin = Pin(m0_pin_str, Pin.OUT)
    m1_pin = Pin(m1_pin_str, Pin.OUT)
    
    # Enter config mode
    m0_pin.value(0)
    m1_pin.value(1)
    time.sleep_ms(100)
    
    uart = UART(uart_num, 115200, timeout=2000)
    time.sleep_ms(200)
    
    if uart.any():
        response = uart.read()
        print("Raw response bytes:", [hex(x) for x in response] if response else "None")
        print("Raw response hex:", response.hex() if response else "None")
        print("Raw response length:", len(response) if response else 0)
    else:
        print("No response available")
    
    # Exit config mode
    m0_pin.value(0)
    m1_pin.value(0)
    time.sleep_ms(100)

def read():
    """Read data from module"""
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    own_addr = 100
    freq = 868
    freq_offset = freq - 850
    
    m0_pin = Pin(m0_pin_str, Pin.OUT)
    m1_pin = Pin(m1_pin_str, Pin.OUT)
    
    # Normal mode
    m0_pin.value(0)
    m1_pin.value(0)
    time.sleep_ms(100)
    
    uart = UART(uart_num, 115200, timeout=2000)
    
    # Wait for data
    start_time = time.ticks_ms()
    while not uart.any():
        if time.ticks_diff(time.ticks_ms(), start_time) > 10000:
            print("No data (timeout)")
            return
        time.sleep_ms(10)
    
    time.sleep_ms(250)
    data = uart.readline()
    
    if data and len(data) > 0:
        if data[-1] == 0x0A:
            data = data[:-1]
        if len(data) >= 3:
            message = data[3:]
            print("Received message:", message)
            print("Message length:", len(message), "bytes")
        else:
            print("Data too short:", len(data), "bytes")
    else:
        print("No data")

def write():
    """Write data to module"""
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    target_addr = 200
    own_addr = 100
    freq = 868
    freq_offset = freq - 850
    message = b"Hello from LoRa!"
    
    m0_pin = Pin(m0_pin_str, Pin.OUT)
    m1_pin = Pin(m1_pin_str, Pin.OUT)
    
    # Normal mode
    m0_pin.value(0)
    m1_pin.value(0)
    time.sleep_ms(100)
    
    uart = UART(uart_num, 115200, timeout=2000)
    
    # Build message packet
    data = (
        bytes([target_addr >> 8]) +
        bytes([target_addr & 0xFF]) +
        bytes([freq_offset]) +
        bytes([own_addr >> 8]) +
        bytes([own_addr & 0xFF]) +
        bytes([freq_offset]) +
        message +
        b"\n"
    )
    
    # Replace newlines
    data = data.replace(b"\n", b"{}[]")
    if data[-1] != 0x0A:
        data = data + b"\n"
    
    uart.write(data)
    time.sleep_ms(150)
    print("Sent", len(message), "bytes to address", target_addr)

# Main execution
if MODE == "configure":
    configure()
elif MODE == "read":
    read()
elif MODE == "write":
    write()
elif MODE == "get_response":
    get_response()
else:
    print("Unknown mode. Use: 'configure', 'read', 'write', or 'get_response'")
