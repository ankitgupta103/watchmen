# Transmission.py
# * we are using this repo base lib https://github.com/nRF24/pyRF24/tree/main

import time
from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS

radio = RF24(22, 0)

tx_address = b"1Node"
rx_address = b"2Node"
MAX_CHUNK_SIZE = 32
END_FLAG = b"<END>"
count = 0

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ not responding")
    radio.setPALevel(RF24_PA_LOW)
    radio.setDataRate(RF24_1MBPS)
    radio.setChannel(76)
    radio.stopListening(tx_address)
    radio.open_rx_pipe(1, rx_address)
    radio.payloadSize = MAX_CHUNK_SIZE

def send_large_message(message):
    data_bytes = message.encode('utf-8')
    total_len = len(data_bytes)
    print(f"Sending {total_len} bytes...")
    
    for i in range(0, total_len, MAX_CHUNK_SIZE):
        chunk = data_bytes[i:i+MAX_CHUNK_SIZE]
        buffer = chunk.ljust(MAX_CHUNK_SIZE, b'\x00')  # pad to 32 bytes
        if not radio.write(buffer):
            print("Chunk send failed")
        time.sleep(0.01)  # slight delay

    # Send end flag
    radio.write(END_FLAG.ljust(MAX_CHUNK_SIZE, b'\x00'))
    print("Transmission complete")

def transmit_loop():
    long_text = (
        "This is a very long message that exceeds 32 bytes and needs to be sent in chunks "
        "using the nRF24L01+ module with PA and LNA enabled for long-range communication."
    )
    
    while True:
        send_large_message(long_text)
        count +=1
        if count == 6400:   # For 1 mb
        break

if __name__ == "__main__":
    setup()
    transmit_loop()
