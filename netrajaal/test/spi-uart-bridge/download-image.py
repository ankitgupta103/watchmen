# import time
# from machine import SPI, Pin

# # Minimal SC16IS750 class for SPI UART (works with your hardware)
# class SC16IS750:
#     REG_THR = 0x00 << 3
#     REG_RHR = 0x00 << 3
#     REG_LSR = 0x05 << 3
#     REG_SPR = 0x07 << 3

#     def __init__(self, spi, cs):
#         self.spi = spi
#         self.cs = cs
#         self.cs.init(self.cs.OUT, value=1)

#     def _read_reg(self, reg):
#         self.cs(0)
#         self.spi.write(bytearray([0x80 | reg]))
#         result = self.spi.read(1)[0]
#         self.cs(1)
#         return result

#     def _write_reg(self, reg, val):
#         self.cs(0)
#         self.spi.write(bytearray([reg, val]))
#         self.cs(1)

#     def ping(self):
#         self._write_reg(self.REG_SPR, 0x55)
#         if self._read_reg(self.REG_SPR) != 0x55:
#             return False
#         self._write_reg(self.REG_SPR, 0xAA)
#         return self._read_reg(self.REG_SPR) == 0xAA

#     def any(self):
#         return self._read_reg(0x09 << 3)  # RXLVL

#     def read(self):
#         return self._read_reg(self.REG_RHR)

#     def write(self, data):
#         for byte in data:
#             while (self._read_reg(self.REG_LSR) & 0x20) == 0:
#                 pass
#             self._write_reg(self.REG_THR, byte)

# # SPI setup
# spi = SPI(1, baudrate=1000000, polarity=0, phase=0)
# cs = Pin("P3", Pin.OUT)
# uart = SC16IS750(spi, cs)

# # Helper to send AT command
# def send_at(cmd, delay=2, verbose=True):
#     uart.write((cmd + "\r\n").encode())
#     time.sleep(delay)
#     response = b""
#     t_start = time.ticks_ms()
#     while time.ticks_diff(time.ticks_ms(), t_start) < 5000:
#         while uart.any():
#             response += bytes([uart.read()])
#     if verbose:
#         print(">>", cmd)
#         # print("<<", response.decode("utf-8", "ignore"))
#         try:
#             print("<<", response.decode("utf-8", "ignore"))
#         except UnicodeError:
#             print("<< (Binary Data):", response)

#     return response

# # --------- MAIN FLOW ---------
# print("Initializing SC16IS750...")
# if uart.ping():
#     print("SC16IS750 connected!")
# else:
#     raise Exception("SC16IS750 not detected!")

# print("Initializing SIM7600...")
# send_at("AT")
# send_at("ATE0")  # Disable echo
# send_at("AT+CSQ")  # Signal quality
# send_at("AT+CREG?")  # Registration status

# # Apn : (jionet, airtelgprs.com)
# send_at('AT+CSTT="airtelgprs.com","",""')
# send_at("AT+CIICR")
# send_at("AT+CIFSR")  # Get IP

# # Start TCP connection
# send_at('AT+CIPSTART="TCP","picsum.photos","80"', delay=5)

# # Send HTTP GET request
# send_at("AT+CIPSEND")
# time.sleep(1)

# http_get = (
#     "GET /200.jpg HTTP/1.1\r\n"
#     "Host: picsum.photos\r\n"
#     "Connection: close\r\n\r\n"
# )
# uart.write(http_get.encode())
# uart.write(b"\x1A")  # End of data (Ctrl+Z)

# # Receive image data
# print("Receiving image...")
# img_bytes = b""
# start = time.ticks_ms()
# while time.ticks_diff(time.ticks_ms(), start) < 10000:
#     while uart.any():
#         img_bytes += bytes([uart.read()])

# # Extract image from HTTP
# header_end = img_bytes.find(b"\r\n\r\n")
# if header_end != -1:
#     image_data = img_bytes[header_end + 4:]
#     try:
#         with open("/temp.jpg", "wb") as f:
#             f.write(image_data)
#         print("Image saved to /temp.jpg")
#     except Exception as e:
#         print("Failed to write image:", e)
# else:
#     print("Failed to parse HTTP response.")


import time
import sensor, image
from machine import SPI, Pin
import os

# Register addresses
RHR = 0x00
THR = 0x00
LSR = 0x05
LSR_RX_READY = 0x01

class SC16IS750:
    def __init__(self, spi, cs):
        self.spi = spi
        self.cs = cs
        self.init()

    def reg_read(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        val = self.spi.read(1)
        self.cs.value(1)
        return val[0]

    def reg_write(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([(reg << 3), val]))
        self.cs.value(1)

    def init(self):
        print("Initializing SC16IS750...")
        self.reg_write(0x0E, 0x08)  # Reset FIFO
        self.reg_write(0x02, 0x01)  # Enable FIFO
        self.set_baudrate(115200)
        self.reg_write(0x03, 0x03)  # 8 data bits, 1 stop, no parity
        print("SC16IS750 connected!")

    def set_baudrate(self, baudrate):
        divisor = int(14745600 / (baudrate * 16))
        lcr = self.reg_read(0x03)
        self.reg_write(0x03, lcr | 0x80)  # Enable divisor latch
        self.reg_write(0x00, divisor & 0xFF)
        self.reg_write(0x01, (divisor >> 8) & 0xFF)
        self.reg_write(0x03, lcr & ~0x80)

    def available(self):
        return self.reg_read(0x09)

    def read(self):
        if self.available():
            return self.reg_read(RHR)
        return None

    def write(self, data):
        for b in data:
            self.reg_write(THR, b)

# Setup SPI + CS
spi = SPI(1, baudrate=8000000, polarity=0, phase=0)
cs = Pin("P3", Pin.OUT)
cs.value(1)

uart = SC16IS750(spi, cs)

def send_cmd(cmd, wait=2):
    print(">>", cmd)
    uart.write((cmd + "\r\n").encode())
    time.sleep(wait)
    buf = bytearray()
    while uart.available():
        ch = uart.read()
        if ch:
            buf.append(ch)
    try:
        text = buf.decode("utf-8", "ignore")
        print("<<", text)
        return text
    except Exception as e:
        print("<< Binary:", buf)
        return ""

def setup_sim():
    print("Initializing SIM7600...")
    for cmd in [
        "AT", "ATE0", "AT+CSQ", "AT+CREG?", "AT+CSTT=\"airtelgprs.com\",\"\",\"\"",
        "AT+CIICR", "AT+CIFSR"
    ]:
        send_cmd(cmd)
        time.sleep(2)

def http_get_image():
    send_cmd('AT+CIPSTART="TCP","picsum.photos","80"', 4)
    send_cmd("AT+CIPSEND", 2)
    uart.write(b"GET /200.jpg HTTP/1.1\r\nHost: picsum.photos\r\n\r\n")
    time.sleep(1)

    # Read until we find JPEG header
    img_data = bytearray()
    started = False
    while True:
        if uart.available():
            b = uart.read()
            if b is not None:
                img_data.append(b)
                if not started and img_data[-2:] == b'\xFF\xD8':
                    started = True
                    img_data = b'\xFF\xD8'
                elif started and img_data[-2:] == b'\xFF\xD9':
                    print("Received complete JPEG!")
                    break
        else:
            time.sleep(0.01)

    with open("/flash/received.jpg", "wb") as f:
        f.write(img_data)
    print("Image saved as /flash/received.jpg")

setup_sim()
http_get_image()
