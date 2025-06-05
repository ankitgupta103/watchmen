import time
import struct
from pyrf24 import RF24, RF24_PA_HIGH, RF24_250KBPS

radio = RF24(22, 0)  # CE=GPIO22, CSN=SPI0 CE0 => /dev/spidev0.0

tx_address = b"1Node"
rx_address = b"2Node"

def setup():
    if not radio.begin():
        raise RuntimeError("nRF24L01+ hardware not responding")

    radio.setPALevel(RF24_PA_HIGH)
    radio.setDataRate(RF24_250KBPS)
    radio.setChannel(76)
    radio.setAutoAck(True)
    radio.setRetries(15, 100)

    radio.stopListening()
    radio.open_rx_pipe(1, rx_address)
    radio.openWritingPipe(tx_address)
    radio.setAddressWidth(5)
    radio.enableDynamicPayloads()

def send_integer(value: float):
    header = struct.pack("B", 1)         # 1 = float
    buffer = struct.pack("<f", value)
    packet = header + buffer
    radio.flush_tx()
    success = radio.write(packet)
    print("[TX] Sent float:", value if success else "Failed")

def send_string(message: str):
    header = struct.pack("B", 2)         # 2 = string
    truncated = message[:31]             # Max 31 chars to fit with header in 32 bytes
    buffer = struct.pack("31s", truncated.encode('utf-8'))
    packet = header + buffer
    radio.flush_tx()
    success = radio.write(packet)
    print("[TX] Sent string:", truncated if success else "Failed")


if __name__ == "__main__":
    setup()
    for i in range(5):
        send_integer(i * 1.23)
        time.sleep(1)
        send_string(f"Hello {i}")
        time.sleep(1)
