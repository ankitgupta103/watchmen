import serial
import sys
import threading
import random
import json
import time
import threading

# Local
import constants
import image

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
        self.msg_chunks_expected = {} # Receiver uses this. cid->num_chunks
        self.msg_chunks_received = {} # Receiver uses this. cid->list of ids got
        self.msg_parts = {} # Receiver uses this. cid->data
        self.msg_cunks_missing = {} # Sender gets this from ack.

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
    def _process_read_message(self, msgstr):
        # Handle ack
        msg = json.loads(msgstr)
        msgid = msg["nid"]
        (msgtype, src, dest, ts) = self._parse_msg_id(msgid)
        if dest is None:
            print(f"{msgstr} is a broadcast")
            #TODO process message
            return
        if msgtype == constants.MESSAGE_TYPE_ACK and dest == self.devid:
            print(f" ------------- Received Ack for {msgid} at {time.time() }!!!!!")
            ackid = msg["ackid"]
            if "missing_chunks" in msg:
                print(f"Receiver did not get chunks : {msg['missing_chunks']}")
                self.msg_cunks_missing[msg["cid"]] = eval(msg["missing_chunks"])
            with self.msg_unacked_lock:
                if ackid in self.msg_unacked:
                    unack = self.msg_unacked.pop(ackid, None)
                    time_to_ack = time.time() - unack[-1]
                    self.msg_acked[ackid] = (len(unack), time_to_ack)
                    print(f"{ackid} --- Cleared ack, time for ack = {time_to_ack}")
                else:
                    print(f"Ack {ackid} isnt for me")
            return
        if dest != self.devid:
            print(f"{self.devid} : {msgid} is a unicast but not for me but for {dest}")
            return
        self.msg_received.append(msg)
        if msgtype == constants.MESSAGE_TYPE_CHUNK_BEGIN:
            self.msg_chunks_expected[msg["cid"]] = int(msg["num_chunks"])
            self.msg_chunks_received[msg["cid"]] = []
            self.msg_parts[msg["cid"]] = []
            print(f"at cb : self.msg_chunks_received = {self.msg_chunks_received}")
            print(f"{self.devid} : Sending ack for {msgid} to {src}")
            msg_to_send = {
                    constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_ACK,
                    "ackid" : msgid,
                    }
            self.send_unicast(msg_to_send, src, False, 0)
            return
        if msgtype == constants.MESSAGE_TYPE_CHUNK_ITEM:
            # TODO aggregate by original message id of begin.
            parts = msg["cid"].split('_')
            if len(parts) != 2:
                print(f"Error parsing cid in {msgstr}")
                return
            cid = parts[0]
            i = int(parts[1])
            print(f"at ci : self.msg_chunks_received = {self.msg_chunks_received}")
            self.msg_chunks_received[cid].append(i)
            self.msg_parts[cid].append((i, msg["imc"]))
            return
        if msgtype == constants.MESSAGE_TYPE_CHUNK_END:
            cid = msg["cid"]
            expected_chunks = self.msg_chunks_expected[cid]
            missing_chunks = []
            for i in range(expected_chunks):
                if i not in self.msg_chunks_received[cid]:
                    missing_chunks.append(i)
            print(f"At end I am missing {len(missing_chunks)} chunks, namely : {missing_chunks}")
            if len(missing_chunks) == 0:
                self._recompile_msg(cid)
            msg_to_send = {
                    constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_ACK,
                    "ackid" : msgid,
                    "cid" : cid,
                    "missing_chunks" : f"{missing_chunks}"
                    }
            self.send_unicast(msg_to_send, src, False, 0)
            return
        print(f"{self.devid} : Sending ack for {msgid} to {src}")
        msg_to_send = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_ACK,
                "ackid" : msgid,
                }
        self.send_unicast(msg_to_send, src, False, 0)

    def _recompile_msg(self, cid):
        print(self.msg_parts[cid])
        p = sorted(self.msg_parts[cid], key=lambda x: x[0])
        parts = []
        for (_, d) in p:
            parts.append(d)
        imstr = "".join(parts)
        im = image.imstrtoimage(imstr)
        im.save("/tmp/recompiled.jpg")
        im.show()

    def _read_from_esp(self):
        print(f"{self.devid} is reading messages now")
        while True:
            if self.ser.in_waiting > 0:
                try:
                    data = self.ser.readline().decode().strip()
                    if data:
                        print("\nFrom ESP32:", data)
                        self._process_read_message(data)
                except UnicodeDecodeError:
                    print("\n[Warning] Received non-UTF8 data")

    # Non blocking, background thread
    def keep_reading(self):
        # Start background thread to read incoming data
        reader_thread = threading.Thread(target=self._read_from_esp, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        reader_thread.start()

    def _get_msg_id(self, msgtype, dest):
        r = random.randint(100,200)
        t = int(time.time())
        t = 0
        id = f"{msgtype}_{self.devid}_{dest}_{t}_{r}"
        print(f"Id = {id}")
        return id

    def _parse_msg_id(self, msgid):
        parts = msgid.split('_')
        if len(parts) != 5:
            print(f"Failed Parsing Key")
            return None
        msgtype = parts[0]
        src = parts[1]
        dest = None
        if len(parts[2]) > 0:
            dest = parts[2]
        ts = parts[3]
        return (msgtype, src, dest, ts)

    def _actual_send(self, msgstr):
        if len(msgstr) > 200:
            print(f"Message is exceeding length {len(msgstr)}")
            return False
        self.ser.write((msgstr + "\n").encode())
        return True
   
    # No ack, no retry
    # TODO set limit on size
    def send_broadcast(self, msg):
        msgstr = json.dumps(msg)
        return self._actual_send(msgstr)

    # dest = None = broadcast, no ack waited, assumed success.
    # dest = IF = unicast, ack awaited with retry_count retries and a 2 sec sleep
    # TODO set limit on size
    def send_unicast(self, msg, dest, wait_for_ack = True, retry_count = 3):
        msgid = self._get_msg_id(msg[constants.JK_MESSAGE_TYPE], dest)
        msg["nid"] = msgid
        msgstr = json.dumps(msg)
        if not wait_for_ack:
            return self._actual_send(msgstr)
        # We have to wait for ack.
        sent_succ = False
        for i in range(retry_count):
            if sent_succ:
                break
            print(f"Sending {msgid} of type {msg[constants.JK_MESSAGE_TYPE]} for the {i}th time")
            sent_succ = self._send_with_retries(msgstr, msgid)
        return sent_succ

    def _send_chunk_i(self, msg_chunks, chunk_identifier, i, dest):
        num_chunks = len(msg_chunks)
        print(f"Sending chunk {i} out of {num_chunks}")
        msgid = self._get_msg_id(constants.MESSAGE_TYPE_CHUNK_ITEM, dest)
        msg = msg_chunks[i]
        msg[constants.JK_MESSAGE_TYPE] = constants.MESSAGE_TYPE_CHUNK_ITEM
        msg["nid"] = msgid
        msg["cid"] = f"{chunk_identifier}_{i}"
        msgstr = json.dumps(msg)
        self._actual_send(msgstr)
        time.sleep(1) # TODO Needed for corruption free sending.

    def _send_chunk_end(self, chunk_identifier, dest):
        msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_CHUNK_END,
                "cid" : f"{chunk_identifier}"
                }
        sent = self.send_unicast(msg, dest, True, 3)
        time.sleep(1) # TODO Needed for corruption free sending.
        return sent 

    # Note retry here is separate retry per chunk.
    # We will send 100 chunks, with/without retries, but then the receiver will tell at the end whats missing.
    def send_chunks(self, msg_chunks, dest, retry_count = 3):
        num_chunks = len(msg_chunks)
        print(f"Getting ready to push {num_chunks} chunks")
        chunk_identifier = random.randint(100,200) # TODO better.
        msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_CHUNK_BEGIN,
                "num_chunks" : f"{num_chunks}",
                "cid" : f"{chunk_identifier}"
                }
        sent = self.send_unicast(msg, dest, True, 3)
        time.sleep(1) # TODO Needed for corruption free sending.
        if not sent:
            print(f"Failed to send chunk begin")
            return False
        for i in range(num_chunks):
            self._send_chunk_i(msg_chunks, chunk_identifier, i, dest)
        sent = self._send_chunk_end(chunk_identifier, dest)
        if not sent:
            return False
        for i in range(retry_count):
            chunks_undelivered = self.msg_cunks_missing[str(chunk_identifier)]
            print(f"Could not deliver {len(chunks_undelivered)} chunks : {chunks_undelivered}")
            if len(chunks_undelivered) == 0:
                break
            for cid in chunks_undelivered:
                self._send_chunk_i(msg_chunks, chunk_identifier, cid, dest)
            sent = self._send_chunk_end(chunk_identifier, dest)
            if not sent:
                return False
        chunks_undelivered = self.msg_cunks_missing[str(chunk_identifier)]
        if len(chunks_undelivered) == 0:
            print(f" ==== Successfully delivered all chunks!!!")
        else:
            print(f" **** Finally after all attempts, Could not deliver {len(chunks_undelivered)} chunks : {chunks_undelivered}")


    def _send_with_retries(self, msgstr, msgid):
        with self.msg_unacked_lock:
             if msgid not in self.msg_unacked:
                 self.msg_unacked[msgid] = [time.time()]
             else:
                 self.msg_unacked[msgid].append(time.time())
        sent_succ = self._actual_send(msgstr)
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
                    self._actual_send(msg)
        except KeyboardInterrupt:
            print("\nExiting...")
            self.ser.close()

def test_send_img(esp, devid, dest, imgfile):
    im = image.image2string(imgfile)
    msg_chunks = []
    while len(im) > 0:
        msg = {"imc": im[0:120]}
        msg_chunks.append(msg)
        im = im[120:]
    print(len(msg_chunks))
    esp.send_chunks(msg_chunks, dest, 3)

def test_send_chunks(esp, devid, dest):
    msg_chunks = []
    for i in range(12):
        msg = {"data": f"{i}"}
        msg_chunks.append(msg)
    esp.send_chunks(msg_chunks, dest, 3)

def test_send_types(esp, devid, dest):
    msg = {constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_SCAN, "data": "Scantest"}
    esp.send_broadcast(msg)
    msg = {constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT, "data": "Someone else"}
    esp.send_unicast(msg, "cc", True, 2)

    for i in range(3):
        rt = random.randint(1000,2000)/1000
        print(f"Sending message #{i} but first, sleeping for {rt} secs")
        time.sleep(rt)
        msga = f"HB#{devid}_{i}"
        msg = {"mst" : constants.MESSAGE_TYPE_HEARTBEAT, "data": msga}
        sent = esp.send_unicast(msg, dest, True)
        print(f"Sending success = {sent}")

    crazy_long_message = {
            constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT
            }
    for i in range(10):
        crazy_long_message[f"k{i}"] = f"Hello 123456 This is a test to make a very long message {i}"
    sent = esp.send_unicast(crazy_long_message, dest, True)
    print(f"Sending success = {sent}")

def test_send_time_to_ack(esp, devid, dest, msgsize):
    msg = {
            constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT, 
            "data": "timecheck"}
    esp.send_unicast(msg, dest, True, 3)

def main():
    if sys.argv[1] == "r":
        devid = "aa"
        dest = "bb"
    elif sys.argv[1] == "s":
        devid = "bb"
        dest = "aa"
    else:
        print(f"arg1 has to be r or s only")
    esp = EspComm(devid)
    esp.keep_reading()
    if devid == "bb":
        test_send_time_to_ack(esp, devid, dest, 10)
        test_send_img(esp, devid, dest, "pencil.jpg")
        test_send_chunks(esp, devid, dest)
        test_send_types(esp, devid, dest)
    if devid == "aa":
        time.sleep(60)
    time.sleep(10)
    esp.print_status()

if __name__=="__main__":
    main()
