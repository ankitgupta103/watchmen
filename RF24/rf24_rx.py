# Receiver.py
import time
from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)

tx_address = b"1Node"
rx_address = b"2Node"
MAX_CHUNK_SIZE = 32
END_FLAG = b"<END>"

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    radio.open_rx_pipe(1, tx_address)
    radio.listen = True
    radio.payloadSize = MAX_CHUNK_SIZE

def receive_chunks():
    message_chunks = []

    while True:
        has_payload, pipe = radio.available_pipe()
        if has_payload:
            data = radio.read(MAX_CHUNK_SIZE)
            if data.startswith(END_FLAG):
                full_message = b''.join(message_chunks).rstrip(b'\x00').decode('utf-8', errors='ignore')
                print(f"\n✅ Full message received ({len(full_message)} bytes):\n{full_message}\n")
                message_chunks = []  # Reset for next message
            else:
                message_chunks.append(data)
        time.sleep(0.01)

if __name__ == "__main__":
    setup()
    receive_chunks()
