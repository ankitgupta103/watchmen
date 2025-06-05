import socket
import sys
import threading
import time

from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)

MAX_CHUNK_SIZE = 32

hname = socket.gethostname()
myname = b""
othername = b""
if hname == "central":
    myname = b"n1"
    othername = b"n2"
if hname == "rpi2":
    myname = b"n2"
    othername = b"n1"
print(f"{myname} : {othername}")

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    radio.stop_listening(myname)
    radio.open_rx_pipe(1, othername)
    radio.payloadSize = MAX_CHUNK_SIZE
    radio.setAutoAck(True)
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
            datastr = data.decode()
            print(f"========{num_messages} Received data : {datastr}")
            if datastr.find("Ack") < 0:
                send_message(f"Ack:{datastr}")

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
    num_to_send = 10
    num_successfully_sent = 0
    for i in range(num_to_send):
        ms = f"M#{i}"
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
        time.sleep(1000)
    else:
        print("argv1 needs to be r OR s")
    reader_thread.join()

if __name__ == "__main__":
    main()
