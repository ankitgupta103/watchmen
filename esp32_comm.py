import serial
import time
import threading

class EspComm:
    def __init__(self):
        # Initialize UART
        self.ser = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)     # /dev/serial0 ,  /dev/ttyS0,  /dev/ttyAMA0
        time.sleep(2)  # Give ESP32 time to reset

    def read_from_esp(self):
        while True:
            if self.ser.in_waiting > 0:
                try:
                    data = ser.readline().decode().strip()
                    if data:
                        print("\nFrom ESP32:", data)
                except UnicodeDecodeError:
                    print("\n[Warning] Received non-UTF8 data")

    # Non blocking, background thread
    def keep_reading(self):
        # Start background thread to read incoming data
        reader_thread = threading.Thread(target=self.read_from_esp, daemon=True)
        reader_thread.start()

    def send(msg):
        self.ser.write((msg + "\n").encode())

    # Blocking
    def keep_sending(self):
        try:
            while True:
                msg = input("To ESP32: ")
                if msg:
                    self.send(msg)
        except KeyboardInterrupt:
            print("\nExiting...")
            ser.close()

def main():
    esp = EspComm()
    esp.keep_reading()
    print("Two-way communication started. Type to send to ESP32.\nPress Ctrl+C to exit.")
    esp.keep_sending()

if __name__=="__main__":
    main()
