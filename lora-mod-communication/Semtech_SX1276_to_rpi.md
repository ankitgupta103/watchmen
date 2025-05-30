# Semtech SX1276 to communicate with another Raspberry Pi connected to another SX1276  (point-to-point LoRa communication)

## wire the SX1276 module to your Raspberry Pi using the SPI interface:

## Connections Between SX1276 and Raspberry Pi
SX1276 module has SPI exposed (which is standard) :

**SX1276 Pin                   	Raspberry Pi Pin	             GPIO Description**
VCC                            	3.3V (Pin 1)	                 Power supply  
GND	                            GND (Pin 6)	                     Ground  
SCK                          	GPIO11 (Pin 23)	                 SPI Clock  
MISO	                        GPIO9 (Pin 21)	                 Master In Slave Out  
MOSI	                        GPIO10 (Pin 19)	                 Master Out Slave In  
NSS	                            GPIO8 (Pin 24)	                 Chip Select (CS/SS)  
RESET	                        GPIO25 (Pin 22)	                 Reset (can use any GPIO)  
DIO0	                        GPIO4 (Pin 7)	                 Interrupt pin  



## If you're using SPI, enable SPI on Raspberry Pi using:
```bash
sudo raspi-config
# Go to Interfaces > SPI > Enable
```

## Example Python Library for LoRa (SX127x)
You can use pyLoRa or pySX127x.

Here’s a minimal connection script using pySX127x:

```bash
from SX127x.LoRa import *
from SX127x.board_config import BOARD

BOARD.setup()

class LoRaNode(LoRa):
    def __init__(self, verbose=False):
        super(LoRaNode, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)

    def start(self):
        print("Sending message...")
        self.write_payload([0x48, 0x65, 0x6C, 0x6C, 0x6F])  # "Hello"
        self.set_mode(MODE.TX)

lora = LoRaNode(verbose=False)
lora.set_freq(868.0)
lora.set_spreading_factor(7)
lora.set_tx_power(14)
lora.set_mode(MODE.STDBY)
lora.start()
```

## Install dependencies:
```bash
sudo apt-get install python3-dev python3-pip
pip3 install RPi.GPIO spidev
```

* Ensure both Raspberry Pis are using the same frequency, bandwidth, spreading factor, and sync word 
* Test with one as transmitter and another as receiver
* Use 3.3V logic levels only—do not use 5V, as the SX1276 is not 5V tolerant

