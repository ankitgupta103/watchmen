from machine import UART
import time

UART_PORT = 1
UART_BAUDRATE = 115200

uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

uart.write(b'AT\r')
time.sleep(1)
print(uart.read())

uart.write(b'AT+CPIN?\r')
time.sleep(1)
print(uart.read())  # Expect: b'+CPIN: READY\r\n\r\nOK\r\n'

uart.write(b'AT+CSQ\r')
time.sleep(1)
print(uart.read())  # Expect: b'+CSQ: 15,99\r\n\r\nOK\r\n' (value >= 10 is usable)

uart.write(b'AT+CREG?\r')
time.sleep(1)
print(uart.read())  # Expect: b'+CREG: 0,1' or '0,5' (registered)
