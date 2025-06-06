import random
import socket
import sys
import threading
import time

from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)

MAX_CHUNK_SIZE = 32

nodenames = [b"n2", b"n3"]#, b"nc"]
hname = socket.gethostname()

myname = b""
othernames = []
ind = -1

if hname == "rpi2":
    ind = 0
elif hname == "rpi3":
    ind = 1
elif hname == "central":
    ind = 2
else:
    print(f"Unknown host")
    sys.exit(1)

for i in range(len(nodenames)):
    if i == ind:
        myname = nodenames[i]
    else:
        othernames.append(nodenames[i])
print(f"{myname} : {othernames}")

msgs_recd = []

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    radio.stop_listening(myname)
    for i in range(len(othernames)):
        radio.open_rx_pipe(i+1, othernames[i])
    radio.payloadSize = MAX_CHUNK_SIZE
    #radio.setAutoAck(True)
    radio.set_retries(10, 5)

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
            msgs_recd.append(datastr)
            print(f"==============={num_messages} Received data : {datastr}")
            #if datastr.find("Ack") < 0:
            #    send_message(f"Ack:{datastr}")

def send_message(msg):
    data_bytes = msg.encode('utf-8')
    total_len = len(data_bytes)
    buffer = data_bytes.ljust(MAX_CHUNK_SIZE, b'\x00')
    print(f"Sending {total_len} bytes...{msg}")
    t1 = time.time()
    radio.listen = False
    succ = radio.write(buffer)
    radio.listen = True
    t2 = time.time()
    print(f"Sending {succ} in time {(t2-t1)*1000} msec")
    return succ

def send_messages():
    num_to_send = 5
    num_successfully_sent = 0
    for i in range(num_to_send):
        r = random.randint(3,6)
        time.sleep(r)
        ms = f"{hname}#{i}"
        succ = send_message(ms)
        if succ:
            num_successfully_sent += 1
    print(f"Num messages sent = {num_to_send}, success = {num_successfully_sent}")

def main():
    setup()
    reader_thread = threading.Thread(target=keep_receiving_bg, daemon=True)
    reader_thread.start()
    if sys.argv[1] == "r":
        time.sleep(1000)
    elif sys.argv[1] == "s":
        send_messages()
        time.sleep(10)
        print(sorted(msgs_recd))
        time.sleep(1000)
    else:
        print("argv1 needs to be r OR s")
    reader_thread.join()

if __name__ == "__main__":
    main()
