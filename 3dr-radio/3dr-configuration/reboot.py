import time
from machine import UART

# Configure UART - pins parameter is not required in this setup
uart = UART(1, baudrate=57600, timeout=1000)

def hard_reboot():
    CONFIG_MODE = False
    while uart.any():
        uart.read()  # clear buffer
    time.sleep(1.2)  # guard time before sending reboot command
    uart.write(b"+++")
    time.sleep(1.2)  # guard time after sending +++

    response = uart.read()
    if response and b'OK' in response:
        CONFIG_MODE = True
    else:
        print("Failed to enter CONFIG mode for reboot.")

    if CONFIG_MODE:
        uart.write(b'ATZ\r\n')


hard_reboot()

