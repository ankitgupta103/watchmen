import random
import socket
import sys
import threading
import time

from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)
MAX_CHUNK_SIZE = 32
hname = socket.gethostname()
msgs_sent = []
msgs_recd = []

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    radio.stop_listening(b"n1")
    radio.open_rx_pipe(1, b"n1")
    radio.payloadSize = MAX_CHUNK_SIZE
    #radio.setAutoAck(True)
    #radio.set_retries(10, 5)

def keep_receiving_bg():
    radio.listen = True
    num_messages = 0
    print("Starting to receive")
    while True:
        has_payload, pipe = radio.available_pipe()
        if has_payload:
            data = radio.read(MAX_CHUNK_SIZE)
            num_messages += 1
            datastr = data.rstrip(b'\x00').decode()
            msgs_recd.append((datastr, time.time()))
            print(f"==============={num_messages} Received data : {datastr}")
            if datastr.find("Ack") < 0:
                send_message(f"Ack:{datastr}")

def send_message(msg):
    data_bytes = msg.encode('utf-8')
    total_len = len(data_bytes)
    buffer = data_bytes.ljust(MAX_CHUNK_SIZE, b'\x00')
    t1 = time.time()
    radio.listen = False
    msgs_sent.append((msg, time.time()))
    succ = radio.write(buffer)
    radio.listen = True
    t2 = time.time()
    print(f"Sending {succ} in time {(t2-t1)*1000} msec")
    return succ

def send_messages(num_to_send):
    num_successfully_sent = 0
    time.sleep(10)
    for i in range(num_to_send):
        r = random.randint(1,2)
        time.sleep(r/10.0)
        ms = f"{hname}#{i}"
        succ = send_message(ms)
        if succ:
            num_successfully_sent += 1

def ack_time(msg):
    for (m, t) in msgs_recd:
        if m == f"Ack:{msg}":
            return t
    return -1

def print_status():
    print(f"{hname} : {len(msgs_recd)} {sorted(msgs_recd)}")
    print(f"Num messages sent = {len(msgs_sent)}")
    for s,t in msgs_sent:
        ackt = ack_time(s)
        if ackt > 0:
            print(f"Acktime for {s} = {ackt-t}")


def main():
    setup()
    reader_thread = threading.Thread(target=keep_receiving_bg, daemon=True)
    reader_thread.start()
    send_messages(int(sys.argv[1]))
    time.sleep(10)
    print_status()
    time.sleep(1000)
    reader_thread.join()

if __name__ == "__main__":
    main()
