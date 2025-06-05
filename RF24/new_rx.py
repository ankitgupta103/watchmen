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

