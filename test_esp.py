import serial
import time
import threading

# Initialize UART
ser = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)     # /dev/serial0 ,  /dev/ttyS0,  /dev/ttyAMA0
time.sleep(2)  # Give ESP32 time to reset

def read_from_esp():
    while True:
        if ser.in_waiting > 0:
            try:
                data = ser.readline().decode().strip()
                if data:
                    print("\nFrom ESP32:", data)
            except UnicodeDecodeError:
                print("\n[Warning] Received non-UTF8 data")

# Start background thread to read incoming data
reader_thread = threading.Thread(target=read_from_esp, daemon=True)
reader_thread.start()

print("Two-way communication started. Type to send to ESP32.\nPress Ctrl+C to exit.")

try:
    while True:
        msg = input("To ESP32: ")
        if msg:
            ser.write((msg + "\n").encode())
except KeyboardInterrupt:
    print("\nExiting...")
    ser.close()



