import machine
from machine import UART
import time


UART_BAUDRATE = 57600
UART_PORT = 1

uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

count_msg = 0


def send_msg(data):

    if isinstance(data, str):
        data = bytes(data, 'utf-8')
    byte_written = uart.write(data)
    print(f"Send {byte_written} bytes: {data} Count: {count_msg}")

while True:
    send_msg("Hello from OpneMV!")
    time.sleep(1)
    count_msg += 1
