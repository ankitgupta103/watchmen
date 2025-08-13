from machine import UART
import time

# Initialize UART1 for GPS module
uart_num = 1
ser = UART(uart_num, 9600, timeout=2000)
print(f"UART {uart_num} initialized at 9600 baud")
print("Reading GPS data...")
print("-" * 50)

while True:
    if ser.any():
        data = ser.readline()
        print(f"{data}")
        if data:
            print(f"Raw bytes ({len(data)}): {data}")



    time.sleep(0.1)
