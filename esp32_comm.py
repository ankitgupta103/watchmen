import serial
import sys
import threading
import random
import json
import time
import threading
import constants

class EspComm:
    msg_unacked = {} # id -> list of ts
    msg_acked = {} # id -> (tries, timetoack)
    msg_unacked_lock = threading.Lock()
    msg_received = [] # Only for testing
    
    def __init__(self, devid):
        self.devid = devid
        # Initialize UART
        self.ser = serial.Serial("/dev/ttyAMA0", 9600, timeout=1)     # /dev/serial0 ,  /dev/ttyS0,  /dev/ttyAMA0
        time.sleep(2)  # Give ESP32 time to reset

    def print_status(self):
        with self.msg_unacked_lock:
            print(f"Acked messages = {len(self.msg_acked)}, unacked messages = {len(self.msg_unacked)}")
            print(self.msg_acked)
            print(self.msg_unacked)
            for mi in self.msg_received:
                print(mi)

    # Four kinds of messages:
    # 1. Has a dest, but not for me, ignore
    # 2. Has a dest, and the dest is myself, ack and process.
    # 3. Has no dest, is a broadcast, process, but dont ack.
    # 4. Is an ack, try to unblock my send.
    def process_read_message(self, msgstr):
        # Handle ack
        print(f" ******* {self.devid} : Received message {msgstr}")
        msg = json.loads(msgstr)
        msgid = msg["espmsgid"]
        dest = msg["espdest"]
        if msg["msgtype"] == constants.MESSAGE_TYPE_ACK and dest == self.devid:
            print(f" ------------- Received Ack for {msgid} at {time.time() }!!!!!")
            ackid = msg["ackid"]
            with self.msg_unacked_lock:
                print(f"Should clear {ackid} from unacked messages : {self.msg_unacked}")
                if ackid in self.msg_unacked:
                    print(f"Clearing {ackid} from unacked messages : {self.msg_unacked}")
                    unack = self.msg_unacked.pop(ackid, None)
                    time_to_ack = time.time() - unack[-1]
                    self.msg_acked[ackid] = (len(unack), time_to_ack)
                    print(f"Cleared {ackid} from unacked messages : {self.msg_unacked}")
                    print(f"{ackid} --- time for ack = {time_to_ack}")
            return
        dest = msg["espdest"]
        src = msg["espsrc"]
        msgid = msg["espmsgid"]
        if dest is None:
            print(f"{msgid} is a broadcast")
            #TODO process message
            return
        if dest != self.devid:
            print(f"{self.devid} : {msgid} is a unicast but not for me but for {dest}")
            return
        print(f"{self.devid} : {msgid} is a unicast for me")
        self.msg_received.append(msg)
        print(f"{self.devid} : Sending ack for {msgid} to {src}")
        msg_to_send = {
                "msgtype" : constants.MESSAGE_TYPE_ACK,
                "ackid" : msgid,
                }
        self.send(msg_to_send, src)

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

    def actual_send(self, msgstr):
        if len(msgstr) > 200:
            print(f"Message is exceeding length {len(msgstr)}")
        self.ser.write((msgstr + "\n").encode())
   
    # No ack, no retry
    def send_broadcast(self, msg):
        msgstr = json.dumps(msg)
        self.actual_send(msgstr)

    # dest = None = broadcast, no ack waited, assumed success.
    # dest = IF = unicast, ack awaited with retry_count retries and a 2 sec sleep
    def send_unicast(self, msg, dest, wait_for_ack = True, retry_count = 3):
        msgid = self.get_msg_id(dest)
        msg["espmsgid"] = msgid
        msg["espsrc"] = self.devid
        msg["espdest"] = dest
        msgstr = json.dumps(msg)
        if not wait_for_ack:
            self.actual_send(msgstr)
            return True
        # We have to wait for ack.
        sent_succ = False
        for i in range(retry_count):
            if sent_succ:
                break
            print(f"Sending {msgid} for the {i}th time")
            sent_succ = self._send_with_retries(msgstr, msgid)
        return sent_succ

    # Note retry here is separate retry per chunk.
    # We will send 100 chunks, with/without retries, but then the receiver will tell at the end whats missing.
    def send_chunks(self, msg_chunks, dest, retry_count = 3):
        print(f"Getting ready to push {len(msg_chunks)} chunks")

    def _send_with_retries(self, msgstr, msgid):
        with self.msg_unacked_lock:
             if msgid not in self.msg_unacked:
                 self.msg_unacked[msgid] = [time.time()]
             else:
                 self.msg_unacked[msgid].append(time.time())
        self.actual_send(msgstr)
        ack_received = False
        time_ack_start = time.time_ns()
        while not ack_received:
            with self.msg_unacked_lock:
                if msgid in self.msg_unacked:
                    print(f"Still waiting for ack for {msgid}")
                else:
                    print(f" =========== Looks like ack received for {msgid}")
                    return True # Hopefully lock is received
            time.sleep(2)
            ts = time.time_ns()
            if (ts - time_ack_start) > 5000000000:
                print(f" Timed out received for {msgid}")
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

def send(esp, devid, dest):
    msg = {"msgtype" : constants.MESSAGE_TYPE_SCAN, "data": "Scantest"}
    esp.send_broadcast(msg)
    msg = {"msgtype" : constants.MESSAGE_TYPE_HEARTBEAT, "data": "Someone else"}
    esp.send_unicast(msg, "cc", True)

    for i in range(5):
        rt = random.randint(1000,2000)/1000
        print(f"Sending message #{i} but first, sleeping for {rt} secs")
        time.sleep(rt)
        msga = f"HB#{devid}_{i}"
        msg = {"msgtype" : constants.MESSAGE_TYPE_HEARTBEAT, "data": msga}
        sent = esp.send_unicast(msg, dest, True)
        print(f"Sending success = {sent}")

    crazy_long_message = {
            "msgtype" : constants.MESSAGE_TYPE_HEARTBEAT
            }
    for i in range(10):
        crazy_long_message[f"k{i}"] = f"Hello 123456 This is a test to make a very long message {i}"
    sent = esp.send_unicast(crazy_long_message, dest, True)
    print(f"Sending success = {sent}")

    esp.send_chunks([msg], dest, 3)

def main():
    devid = sys.argv[1]
    dest  = sys.argv[2]
    esp = EspComm(devid)
    esp.keep_reading()
    if devid == "bb":
        send(esp, devid, dest)
    if devid == "aa":
        time.sleep(60)
    time.sleep(10)
    esp.print_status()

if __name__=="__main__":
    main()
