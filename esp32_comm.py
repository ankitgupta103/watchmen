import serial
import sys
import threading
import random
import json
import time
import threading

class EspComm:
    def __init__(self, devid):
        self.devid = devid
        # Initialize UART
        self.ser = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)     # /dev/serial0 ,  /dev/ttyS0,  /dev/ttyAMA0
        time.sleep(2)  # Give ESP32 time to reset

    def read_from_esp(self):
        while True:
            if self.ser.in_waiting > 0:
                try:
                    data = self.ser.readline().decode().strip()
                    if data:
                        print("\nFrom ESP32:", data)
                except UnicodeDecodeError:
                    print("\n[Warning] Received non-UTF8 data")

    # Non blocking, background thread
    def keep_reading(self):
        # Start background thread to read incoming data
        reader_thread = threading.Thread(target=self.read_from_esp, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        reader_thread.start()

    def get_msg_id(self, dest):
        r = random.randint(10000,20000)
        t = time.time_ns()
        id = f"msg_{self.devid}_{dest}_{t}_{r}"
        print(f"Id = {id}")
        return id

    def send(self, msg, dest):
        msgid = self.get_msg_id(dest)
        msg["espmsgid"] = msgid
        if dest is not None:
            msg["espdest"] = msgid
        msgstr = json.dumps(msg)
        self.ser.write((msgstr + "\n").encode())
        if dest is not None:
            print(f"Waiting for ack for {msgid}")

    # Blocking
    def keep_sending(self):
        try:
            while True:
                msg = input("To ESP32: ")
                if msg:
                    self.send(msg)
        except KeyboardInterrupt:
            print("\nExiting...")
            self.ser.close()

def main():
    devid = sys.argv[1]
    esp = EspComm(devid)
    msg = {"Name" : "Hello My name is " + devid}
    esp.keep_reading()
    esp.send(msg, "bb")
    time.sleep(10)

if __name__=="__main__":
    main()
