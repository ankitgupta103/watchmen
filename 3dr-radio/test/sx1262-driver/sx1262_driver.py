import machine 
import time 
import ustruct
from micropython import const



class sx1262:


    CMD_SET_SLEEP = const(0x84)
    CMD_SET_STANDBY = const(0x80)
    CMD_SET_TX = const(0x83)
    CMD_SET_RX = const(0x82)
    CMD_SET_RF_FREQUENCY = const(0x86)



    # IRQ Flags 
    IRQ_TX_DONE = const(0x0001)
    IRQ_RX_DONE = const(0x0002)
    IRQ_TIMEOUT = const(0x0200)
    IRQ_CRC_ERROR = const(0x0040)



    def __init__(self, spi_id=1, sck=10, mosi=11, miso=12, cs=3, reset=15, busy=2, dio1=20):

        self.spi = machine.SPI(spi_id, baudrate=8000000, polarity=0, phase=0,
                               sck=machine.Pin(sck), mosi=machine.Pin(mosi), miso=machine.Pin(miso))

        # Initialize GPIO pins
        self.cs = machine.pin(cs, machine.Pin.OUT, value=1)
        self.reset = machine.Pin(reset, machine.Pin.OUT, value=1)
        self.busy = machine.Pin(busy, machine.Pin.IN)
        self.dio1 = machine.Pin(dio1, machine.Pin.IN)

        # Buffer for fast operations
        self.tx_buffer = bytearray(255)
        self.rx_buffer = bytearray(255)
        self.last_rssi = 0
        self.last_snr = 0

        # Initialize the radio
        self._init_radio()



    def _init_radio(self):
        """Initializing the radio """
        self.reset_radio()



    def reset_radio(self):
        self.reset.value(0)
        time.sleep_ms(10)
        self.reset.value(1)
        time.sleep_ms(10)
        slef._wait_busy()

    def _wait_busy(self):
        """wait for the busy pin to clear"""
        timeout = 1000
        while self.busy.value() and timeout > 0:
            time.sleep_us(10)
            timeout -= 1
        if timeout == 0:
            raise RuntimeError("Radio busy timeout")