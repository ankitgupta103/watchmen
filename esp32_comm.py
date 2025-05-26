import serial
import sys
import threading
import random
import json
import time
import threading

class EspComm:
    msg_unacked = []
    msg_unacked_lock = threading.Lock()
    
    def __init__(self, devid):
        self.devid = devid
        # Initialize UART
        self.ser = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)     # /dev/serial0 ,  /dev/ttyS0,  /dev/ttyAMA0
        time.sleep(2)  # Give ESP32 time to reset

    # Four kinds of messages:
    # 1. Has a dest, but not for me, ignore
    # 2. Has a dest, and the dest is myself, ack and process.
    # 3. Has no dest, is a broadcast, process, but dont ack.
    # 4. Is an ack, try to unblock my send.
    def process_read_message(self, msgstr):
        # Handle ack
        # Format expected = 'Ack <msgid>'
        if msgstr[0:3] == "Ack":
            msgid = msgstr[4:]
            with self.msg_unacked_lock:
                if msgid in self.msg_unacked:
                    self.msg_unacked = [m for m in self.msg_unacked if m != msgid]
            return
        msg = json.loads(msgstr)
        dest = msg["espdest"]
        msgid = msg["espmsgid"]
        if dest is None:
            print(f"{msgid} is a broadcast")
            #TODO process message
            return
        if dest != self.devid:
            print(f"{msgid} is a unicast but not for me")
            return
        print(f"{msgid} is a unicast for me")
        self.send(f"Ack {msgid}", dest)

    def read_from_esp(self):
        while True:
            if self.ser.in_waiting > 0:
                try:
                    data = self.ser.readline().decode().strip()
                    if data:
                        print("\nFrom ESP32:", data)
                        self.process_read_message(data)
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
        if dest is None:
            self.ser.write((msgstr + "\n").encode())
            return True
        with self.msg_unacked_lock:
             if msgid not in self.msg_unacked:
                 self.msg_unacked.append(msgid)
             else:
                 print(f"Should never happen that message is already in queue")
        self.ser.write((msgstr + "\n").encode())
        ack_received = False
        time_ack_start = time.time_ns()
        while not ack_received:
            print(f"Waiting for ack for {msgid}")
            with self.msg_unacked_lock:
                if msgid in self.msg_unacked:
                    print(f"Still waiting for ack for {msgid}")
                else:
                    print(f"Looks like ack received for {msgid}")
                    return True # Hopefully lock is received
            time.sleep(2)
            ts = time.time_ns()
            print(f"Timing check = {ts - time_ack_start}")
            if (ts - time_ack_start) > 10000000000:
                print(f"Timing out received for {msgid}")
                break
        return False

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
    esp.keep_reading()
    for i in range(5):
        time.sleep(random.randint(1000,3000)/1000)
        msga = f"Sending msg #{devid}_{i}"
        msg = {"Name" : msga}
        sent = esp.send(msg, "bb")
        print(f"Sending success = {sent}")
    time.sleep(10)

if __name__=="__main__":
    main()
