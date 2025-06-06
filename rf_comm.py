import sys
import threading
import random
import json
import socket
import time
import threading

# Local
import constants
import image

from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)
MAX_CHUNK_SIZE = 32
hname = socket.gethostname()

class RFComm:
    msg_unacked = {} # id -> list of ts
    msg_acked = {} # id -> (tries, timetoack)
    msg_unacked_lock = threading.Lock()
    msg_received = [] # Only for testing
    
    def __init__(self, devid):
        self.devid = devid
        time.sleep(2)  # Give ESP32 time to reset
        self.msg_chunks_expected = {} # Receiver uses this. cid->num_chunks
        self.msg_chunks_received = {} # Receiver uses this. cid->list of ids got
        self.msg_parts = {} # Receiver uses this. cid->data
        self.msg_cunks_missing = {} # Sender gets this from ack.
        self.node = None
        self.setup_rf()

    def setup_rf(self):
        if not radio.begin():
            raise RuntimeError("nRF24L01+ not responding")
        radio.setPALevel(RF24_PA_LOW)
        radio.setDataRate(RF24_1MBPS)
        radio.setChannel(76)
        radio.stop_listening(b"n1")
        radio.open_rx_pipe(1, b"n1")
        radio.payloadSize = MAX_CHUNK_SIZE

    def add_node(self, node):
        self.node = node

    def process_message(self, msgstr):
        print(f"Processing incoming message : {msgstr}")
        self.msg_received.append(msgstr)
        if self.node is not None:
            # If in a real device, all messages are json
            msg = json.loads(msgstr)
            self.node.process_msg(msg)

    def print_status(self):
        with self.msg_unacked_lock:
            print(f"Acked messages = {len(self.msg_acked)}, unacked messages = {len(self.msg_unacked)}")
            print(self.msg_acked)
            print(self.msg_unacked)
            for mi in self.msg_received:
                print(f"Message received at receiver = {mi}")

    # Four kinds of messages:
    # 1. Has a dest, but not for me, ignore
    # 2. Has a dest, and the dest is myself, ack and process.
    # 3. Has no dest, is a broadcast, process, but dont ack.
    # 4. Is an ack, try to unblock my send.
    def _process_read_message(self, msgstr):
        # Handle ack
        msgid, msgpyl = self.sep_part(msgstr, ';')
        (msgtype, src, dest, rid) = self._parse_msg_id(msgid)
        if dest is None or dest == "None":
            print(f"{msgstr} is a broadcast")
            self.process_message(msgpyl)
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
            self._send_unicast(msg_to_send, src, False, 0)
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
            self.msg_parts[cid].append((i, msg["c_d"]))
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
                self.process_message(self._recompile_msg(cid))
            msg_to_send = {
                    constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_ACK,
                    "ackid" : msgid,
                    "cid" : cid,
                    "missing_chunks" : f"{missing_chunks}"
                    }
            self._send_unicast(msg_to_send, src, False, 0)
            return
        
        self.process_message(msgpyl)
        print(f"{self.devid} : Sending ack for {msgid} to {src}")
        msg_to_send = msgid
        self._send_unicast(msg_to_send, constants.MESSAGE_TYPE_ACK, src, False, 0)

    def _recompile_msg(self, cid):
        print(self.msg_parts[cid])
        p = sorted(self.msg_parts[cid], key=lambda x: x[0])
        parts = []
        for (_, d) in p:
            parts.append(d)
        orig_payload = "".join(parts)
        orig_msg = json.loads(orig_payload)
        if "i_d" in orig_msg:
            imstr = orig_msg["i_d"]
            im = image.imstrtoimage(imstr)
            im.save("/tmp/recompiled.jpg")
            im.show()
        else:
            print(f"Recompiled message =\n{orig_msg}")
        return orig_msg

    def _read_from_rf(self):
        radio.listen = True
        print("Starting to receive")
        while True:
            has_payload, pipe = radio.available_pipe()
            if has_payload:
                data = radio.read(MAX_CHUNK_SIZE)
                datastr = data.rstrip(b'\x00').decode()
                print(f"=============== Received data : {datastr}")
                self._process_read_message(datastr)

    # Non blocking, background thread
    def keep_reading(self):
        # Start background thread to read incoming data
        reader_thread = threading.Thread(target=self._read_from_rf, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        reader_thread.start()

    def _get_msg_id(self, msgtype, dest):
        r = random.randint(900,999)
        print(r)
        id = f"{msgtype}{self.devid}{dest}{r}"
        print(f"Id = {id}")
        return id

    def sep_part(self, msgstr, sepchar):
        firstloc = msgstr.find(sepchar)
        if firstloc < 0:
            return (None, None)
        if firstloc == len(msgstr) - 1:
            return (msgstr[0:firstloc], "")
        else:
            return (msgstr[0:firstloc], msgstr[firstloc+1:])

    def _parse_msg_id(self, msgid):
        if len(msgid) != 6:
            print(f"Failed Parsing Key : {msgid}")
            return None
        msgtype = msgid[0]
        src = msgid[1]
        dest = None
        if msgid[2] != constants.NO_DEST:
            dest = msgid[2]
        rid = msgid[3:]
        return (msgtype, src, dest, rid)

    def _actual_send(self, msgstr):
        if len(msgstr) > 32:
            print(f"Message is exceeding length {len(msgstr)} : {msgstr}")
            return False
        print(f"Sending message : {msgstr}")
        data_bytes = msgstr.encode('utf-8')
        total_len = len(data_bytes)
        buffer = data_bytes.ljust(MAX_CHUNK_SIZE, b'\x00')
        radio.listen = False
        succ = radio.write(buffer)
        radio.listen = True
        return succ
  
    # TODO mst is stuffed into ID and in message both places.
    # It is in msg just so we can take it out and stuff it into id.
    # Fixit.
    # No ack, no retry
    def _send_broadcast(self, payload, mst):
        msgid = self._get_msg_id(mst, constants.NO_DEST) # Message type has to improve
        msgstr = f"{msgid};{payload}"
        return self._actual_send(msgstr)

    # dest = None = broadcast, no ack waited, assumed success.
    # dest = IF = unicast, ack awaited with retry_count retries and a 2 sec sleep
    # TODO set limit on size
    def _send_unicast(self, payload, mst, dest, wait_for_ack = True, retry_count = 3):
        msgid = self._get_msg_id(mst, dest) # Message type has to improve
        msgstr = f"{msgid};{payload}"
        if not wait_for_ack:
            return self._actual_send(msgstr)
        # We have to wait for ack.
        sent_succ = False
        for i in range(retry_count):
            if sent_succ:
                break
            print(f"Sending {msgid} for the {i}th time")
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
        sent = self._send_unicast(msg, dest, True, 3)
        time.sleep(1) # TODO Needed for corruption free sending.
        return sent 

    # Note retry here is separate retry per chunk.
    # We will send 100 chunks, with/without retries, but then the receiver will tell at the end whats missing.
    def _send_chunks(self, msg_chunks, dest, retry_count = 3):
        num_chunks = len(msg_chunks)
        print(f"Getting ready to push {num_chunks} chunks")
        chunk_identifier = random.randint(100,200) # TODO better.
        msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_CHUNK_BEGIN,
                "num_chunks" : f"{num_chunks}",
                "cid" : f"{chunk_identifier}"
                }
        sent = self._send_unicast(msg, dest, True, 3)
        time.sleep(1) # TODO Needed for corruption free sending.
        if not sent:
            print(f"Failed to send chunk begin")
            return False
        for i in range(num_chunks):
            self._send_chunk_i(msg_chunks, chunk_identifier, i, dest)
        sent = self._send_chunk_end(chunk_identifier, dest)
        time.sleep(1)
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
            return True
        else:
            print(f" **** Finally after all attempts, Could not deliver {len(chunks_undelivered)} chunks : {chunks_undelivered}")
            return False

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

    # Note long message cant be a boradcast
    def _send_long_msg(self, long_msg, dest):
        msgstr = long_msg
        msg_chunks = []
        while len(msgstr) > 0:
            msg = {"c_d": msgstr[0:120]}
            msg_chunks.append(msg)
            msgstr = msgstr[120:]
        print(len(msg_chunks))
        return self._send_chunks(msg_chunks, dest, 3)

    def send_message(self, payload, mst, dest):
        if dest is None:
            if len(payload) < 30:
                msg = payload
                self._send_broadcast(msg, mst)
                return True
            else:
                print(f"Please dont broadcast big messages, this one is of size {len(payload)}")
                return False
        if len(payload) < 30:
            msg = payload
            sent = self._send_unicast(msg, mst, dest)
            return sent
        else:
            print("Too big, will chunk msg {len(payload)}")
            sent = self._send_long_msg(payload, dest)
            return sent

def test_send_img(rf, imgfile, dest):
    mst = constants.MESSAGE_TYPE_PHOTO
    # Allowing json here, since the overhead is worth the metadata.
    im = {"i_m" : "Image metadata",
          "i_d" : image.image2string(imgfile)}
    msgstr = json.dumps(im)
    rf.send_message(msgstr, mst, dest)

def test_send_long_msg(rf, dest):
    mst = constants.MESSAGE_TYPE_SPATH
    long_string = ""
    for i in range(500):
        long_string = long_string + str(i) + "_"
    rf.send_message(long_string, mst, dest)

def test_send_types(rf, devid, dest):
    mst = constants.MESSAGE_TYPE_SPATH
    msg = "Sending a message"
    rf.send_message(msg, mst, None)
    msg = f"Sending a message to {dest}"
    rf.send_message(msg, mst, dest)

# 50 is overhead + size of string of msgsize
def test_send_time_to_ack(rf, dest, mst, msgsize):
    x = "x"*msgsize
    rf.send_message(x, mst, dest)

def main():
    if hname not in constants.HN_ID:
        print(f"Unknown hostname ({hname}) not in {constants.HN_ID}")
        return
    devid = str(constants.HN_ID[hname])
    rf = RFComm(devid)
    rf.keep_reading()
    if len(sys.argv) > 1:
        dest = sys.argv[1]
        # test_send_time_to_ack(rf, dest, int(sys.argv[2]))
        test_send_types(rf, devid, dest)
        # test_send_long_msg(rf, dest) # Assumes its an image
        # test_send_img(rf, "pencil.jpg", dest)
    if devid == "aa":
        time.sleep(100)
    time.sleep(10)
    rf.print_status()

if __name__=="__main__":
    main()
