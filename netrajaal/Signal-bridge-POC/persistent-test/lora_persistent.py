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
# MODE = "read"
# MODE = "write"

# Global addresses for this node and its peer
OWN_ADDR = 100
TARGET_ADDR = 200

def configure():
    """
    Configure LoRa module parameters.

    This method builds the 12-byte configuration register and sends it
    to the module. The configuration is written via UART while the module
    is in configuration mode (M0=LOW, M1=HIGH).

    Configuration Register Layout (12 bytes):
    [0]  Header (0xC0 for persistent, 0xC2 for volatile)
    [1]  Length high byte (always 0x00)
    [2]  Length low byte (always 0x09 for 9 parameters)
    [3]  Node address high byte
    [4]  Node address low byte
    [5]  Network ID
    [6]  UART baud rate (upper 3 bits) + Air data rate (lower 3 bits)
    [7]  Buffer size (upper 2 bits) + TX power (bits 1-2) + RSSI noise enable (bit 5)
    [8]  Frequency offset (0-18 for 900MHz, 0-83 for 400MHz)
    [9]  Operating mode (0x43 for fixed point, 0x03 for relay) + Packet RSSI enable (bit 7)
    [10] Encryption key high byte
    [11] Encryption key low byte

    Args:
        freq (int): Operating frequency in MHz
        addr (int): Node address 0-65535
        power (int): TX power: 10, 13, 17, or 22 dBm
        rssi (bool): Enable packet RSSI reporting
        air_speed (int): Air data rate: 1200-62500 bps
        net_id (int): Network ID 0-255
        buffer_size (int): Buffer size: 32, 64, 128, or 240 bytes
        crypt (int): Encryption key 0-65535 (0 = disabled)
        relay (bool): Enable relay mode
        lbt (bool): Enable Listen Before Talk (not implemented)
        wor (bool): Enable Wake On Radio (not implemented)

    Note:
        Configuration is sent with retry logic (up to 3 attempts).
        Module must respond with 0xC1 header to indicate success.
    """
    # Hardcoded configuration values
    freq = 868
    addr = OWN_ADDR
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
        0xC0,  # 0: persistent config header (write & save to flash)
        0x00,  # 1: payload length high byte (always 0 for 0x009)
        0x09,  # 2: payload length low byte (9 config bytes follow)
        (addr >> 8) & 0xFF,  # 3: ADDH - node address high
        addr & 0xFF,  # 4: ADDL - node address low
        net_id,  # 5: NETID - network/group id
        0xE0 + 0x02,  # 6: REG0 - UART baud 115200 (111) + air rate 2.4k (010)
        0x00 + 0x00 + 0x20,  # 7: REG1 - subpacket 240B (00) + power 22dBm (00) + RSSI noise off (1<<5)
        freq_offset,  # 8: REG2 - channel offset from 850 MHz (CH = 850+offset)
        0x43 + (0x80 if rssi else 0x00),  # 9: REG3 - fixed mode/LBT defaults + optional packet RSSI flag (bit7)
        (crypt >> 8) & 0xFF,  # 10: REG4 - encryption key high byte
        crypt & 0xFF  # 11: REG5 - encryption key low byte
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

def read():
    """Read data from module"""
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    own_addr = OWN_ADDR
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
    while True:
        start_time = time.ticks_ms()
        while not uart.any():
            if time.ticks_diff(time.ticks_ms(), start_time) > 10000:
                print("No data (timeout)")
                return
            time.sleep_ms(10)

        time.sleep_ms(250)
        data = uart.readline()

        print("Data:", data)

        # if data and len(data) > 0:
        #     if data[-1] == 0x0A:
        #         data = data[:-1]
        #     if len(data) >= 3:
        #         message = data[3:]
        #         print("Received message:", message)
        #         print("Message length:", len(message), "bytes")
        #     else:
        #         print("Data too short:", len(data), "bytes")
        # else:
        #     print("No data")

def write():
    """Write data to module"""
    uart_num = 1
    m0_pin_str = "P6"
    m1_pin_str = "P7"
    target_addr = TARGET_ADDR
    own_addr = OWN_ADDR
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
    if data[-1] != 0x0A:
        data = data + b"\n"

    while True:
        uart.write(data)
        time.sleep_ms(200)
        print("Sent", len(message), "bytes to address", target_addr)

# Main execution
if MODE == "configure":
    configure()
elif MODE == "read":
    read()
elif MODE == "write":
    write()
else:
    print("Unknown mode. Use: 'configure', 'read', 'write', or 'get_response'")
