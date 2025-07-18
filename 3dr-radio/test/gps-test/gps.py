from machine import UART
import time

# # UART(3) uses P4 (TX) and P5 (RX) on OpenMV RT1062
# uart = UART(1, baudrate=9600, tx=Pin("P4"), rx=Pin("P5"))

UART_PORT = 1
UART_BAUDRATE = 9600

uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

print("Listening to GPS...")

while True:
    if uart.any():
        data = uart.readline()
        print(data)
        # if data:
        #     print(data.decode('utf-8', 'ignore'))
    time.sleep(0.1)
