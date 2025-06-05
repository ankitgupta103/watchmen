import socket
import sys
import time

from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)

tx_address = b"1Node"
rx_address = b"2Node"
MAX_CHUNK_SIZE = 32

def get_hostname():
    return socket.gethostname()

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    hname = get_hostname()
    radio.open_rx_pipe(1, b"test")
    radio.listen = True
    radio.payloadSize = MAX_CHUNK_SIZE

def keep_receiving():
    print("Starting to receive")
    while True:
        has_payload, pipe = radio.available_pipe()
        if has_payload:
            data = radio.read(MAX_CHUNK_SIZE)
            datastr = data.decode()
            print(f"Received data : {datastr}")

def send_message(msg):
    data_bytes = msg.encode('utf-8')
    total_len = len(data_bytes)
    buffer = data_bytes.ljust(MAX_CHUNK_SIZE, b'\x00')
    print(f"Sending {total_len} bytes...{msg}")
    t1 = time.time()
    succ = radio.write(buffer)
    t2 = time.time()
    print(f"Sending {succ} in time {(t2-t1)*1000} msec")
    time.sleep(0.01)  # slight delay

def send_messages():
    for i in range(10):
        send_message(f"Message#{i}")

def main():
    setup()
    if sys.argv[1] == "r":
        keep_receiving()
    elif sys.argv[1] == "s":
        radio.stopListening(b"test")
        radio.listen = False
        send_messages()
    else:
        print("argv1 needs to be r OR s")

if __name__ == "__main__":
    main()
