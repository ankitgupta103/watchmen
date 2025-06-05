from pyrf24 import RF24

radio = RF24(22, 0)  # CE=GPIO22, CSN=SPI CE0 (spidev0.0)

if not radio.begin():
    print("Radio hardware not responding")
else:
    radio.print_details()
