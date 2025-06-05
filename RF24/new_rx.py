import time
import struct
from pyrf24 import RF24, RF24_PA_LOW, RF24_1MBPS, RF24_PA_MAX, RF24_250KBPS, RF24_PA_HIGH, RF24_IRQ_NONE, RF24_IRQ_ALL

radio = RF24(22, 0)  # CE=GPIO22, CSN=SPI0 CE0 => /dev/spidev0.0

tx_address = b"1Node"
rx_address = b"2Node"

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ hardware not responding")

    radio.setPALevel(RF24_PA_HIGH)
    radio.setDataRate(RF24_250KBPS)
    radio.setChannel(76) #115, 125

    radio.setAutoAck(True)  # Enable auto-acknowledgmentr
    radio.setRetries(15, 100)  # Set retries: delay=15, count=15


    # radio.stopListening(tx_address)  # correct way to set TX addr
    radio.open_rx_pipe(1, rx_address)
    
    radio.openWritingPipe(tx_address)

    # radio.setAddressWidth(5)  # Set address width to 4 bytes
    
    radio.enableDynamicPayloads()  # Enable dynamic payloads


    # radio.payloadSize = struct.calcsize("<f")


# def send_integer(value: float):
#     header = struct.pack("B", 1)         # 1 = float
#     buffer = struct.pack("<f", value)
#     packet = header + buffer
#     radio.flush_tx()
#     success = radio.write(packet)
#     print("[TX] Sent float:", value if success else "Failed")

# def send_string(message: str):
#     header = struct.pack("B", 2)         # 2 = string
#     truncated = message[:31]             # Max 31 chars to fit with header in 32 bytes
#     buffer = struct.pack("31s", truncated.encode('utf-8'))
#     packet = header + buffer
#     radio.flush_tx()
#     success = radio.write(packet)
#     print("[TX] Sent string:", truncated if success else "Failed")

# def send_big_string(message: str):
#     chunk_size = 30  # Because 2 bytes are used for header and sequence
#     total_chunks = (len(message) + chunk_size - 1) // chunk_size

#     for seq in range(total_chunks):
#         chunk = message[seq * chunk_size : (seq + 1) * chunk_size]
#         header = struct.pack("BB", 3, seq)  # 3 = big string, seq number
#         data = chunk.encode('utf-8')
#         padded_data = data.ljust(chunk_size, b'\x00')  # pad to exact size
#         packet = header + padded_data

#         # radio.flush_tx()
#         success = radio.write(packet)
#         print(f"[TX] Sent chunk {seq + 1}/{total_chunks}: '{chunk}'" if success else "[TX] Chunk failed")

        # time.sleep(0.01)  # Small delay to let receiver keep up

    # data = struct.pack('100s', message.encode('utf-8'))
    # padded_data = data.ljust(100, b'\x00')  # Ensure it is exactly 100 bytes
    # # radio.flush_tx()
    # print(data)
    # success = radio.write(data)
    # print("[TX] Sent big string:", message if success else "Failed")


 

def transmit_loop():
    long_string = ("testing radio module connectivity and speed ")
    value = 0.0
    for i in range(1000):

        buffer = struct.pack("<f", value)
        #buffer = struct.pack("32s", long_string[:32].encode('utf-8'))
        radio.flush_tx()
        success = radio.write(buffer)
        if success:
            print(f"Sent: {value}")
        else:
            print("Transmission failed or timed out")
        print(radio.available())  # Clear the RX buffer
        print(radio.isChipConnected())  # Check if the chip is connected
        value += 0.01
#         # time.sleep(3)

if __name__ == "__main__":
    setup()
    transmit_loop()

    # for i in range(1000):
    #     send_integer(i * 0.1)
        # send_string(f"Message {i+1}")
        # time.sleep(0.1)

    # send_big_string("A" * 1024)  # Send a big string of 1000 'A's
