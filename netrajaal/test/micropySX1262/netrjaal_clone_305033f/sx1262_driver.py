from _sx126x import *
from sx126x import SX126X

_SX126X_PA_CONFIG_SX1262 = const(0x00)

class SX1262(SX126X):
    """Simplified SX1262 driver for high-speed LoRa communication"""
    
    TX_DONE = SX126X_IRQ_TX_DONE
    RX_DONE = SX126X_IRQ_RX_DONE
    ADDR_FILT_OFF = SX126X_GFSK_ADDRESS_FILT_OFF
    ADDR_FILT_NODE = SX126X_GFSK_ADDRESS_FILT_NODE
    ADDR_FILT_NODE_BROAD = SX126X_GFSK_ADDRESS_FILT_NODE_BROADCAST
    PREAMBLE_DETECT_OFF = SX126X_GFSK_PREAMBLE_DETECT_OFF
    PREAMBLE_DETECT_8 = SX126X_GFSK_PREAMBLE_DETECT_8
    PREAMBLE_DETECT_16 = SX126X_GFSK_PREAMBLE_DETECT_16
    PREAMBLE_DETECT_24 = SX126X_GFSK_PREAMBLE_DETECT_24
    PREAMBLE_DETECT_32 = SX126X_GFSK_PREAMBLE_DETECT_32
    STATUS = ERROR

    def __init__(self, spi_bus, clk, mosi, miso, cs, irq, rst, gpio, spi_baudrate=2000000, spi_polarity=0, spi_phase=0):
        super().__init__(spi_bus, clk, mosi, miso, cs, irq, rst, gpio, spi_baudrate, spi_polarity, spi_phase)
        self._callbackFunction = self._dummyFunction

    def begin(self, freq=434.0, bw=125.0, sf=9, cr=7, syncWord=SX126X_SYNC_WORD_PRIVATE,
              power=14, currentLimit=60.0, preambleLength=8, implicit=False, implicitLen=0xFF,
              crcOn=True, txIq=False, rxIq=False, tcxoVoltage=1.6, useRegulatorLDO=False,
              blocking=True):
        """Initialize LoRa mode"""
        state = super().begin(bw, sf, cr, syncWord, currentLimit, preambleLength, tcxoVoltage, useRegulatorLDO, txIq, rxIq)
        ASSERT(state)

        if not implicit:
            state = super().explicitHeader()
        else:
            state = super().implicitHeader(implicitLen)
        ASSERT(state)

        state = super().setCRC(crcOn)
        ASSERT(state)

        state = self.setFrequency(freq)
        ASSERT(state)

        state = self.setOutputPower(power)
        ASSERT(state)

        state = super().fixPaClamping()
        ASSERT(state)

        state = self.setBlockingCallback(blocking)
        return state

    def beginFSK(self, freq=434.0, br=48.0, freqDev=50.0, rxBw=156.2, power=14, currentLimit=60.0,
                 preambleLength=16, dataShaping=0.5, syncWord=[0x2D, 0x01], syncBitsLength=16,
                 addrFilter=SX126X_GFSK_ADDRESS_FILT_OFF, addr=0x00, crcLength=2, crcInitial=0x1D0F, crcPolynomial=0x1021,
                 crcInverted=True, whiteningOn=True, whiteningInitial=0x0100,
                 fixedPacketLength=False, packetLength=0xFF, preambleDetectorLength=SX126X_GFSK_PREAMBLE_DETECT_16,
                 tcxoVoltage=1.6, useRegulatorLDO=False, blocking=True):
        """Initialize FSK mode (not used for LoRa)"""
        state = super().beginFSK(br, freqDev, rxBw, currentLimit, preambleLength, dataShaping, preambleDetectorLength, tcxoVoltage, useRegulatorLDO)
        ASSERT(state)
        state = super().setSyncBits(syncWord, syncBitsLength)
        ASSERT(state)
        if addrFilter == SX126X_GFSK_ADDRESS_FILT_OFF:
            state = super().disableAddressFiltering()
        elif addrFilter == SX126X_GFSK_ADDRESS_FILT_NODE:
            state = super().setNodeAddress(addr)
        elif addrFilter == SX126X_GFSK_ADDRESS_FILT_NODE_BROADCAST:
            state = super().setBroadcastAddress(addr)
        else:
            state = ERR_UNKNOWN
        ASSERT(state)
        state = super().setCRC(crcLength, crcInitial, crcPolynomial, crcInverted)
        ASSERT(state)
        state = super().setWhitening(whiteningOn, whiteningInitial)
        ASSERT(state)
        if fixedPacketLength:
            state = super().fixedPacketLengthMode(packetLength)
        else:
            state = super().variablePacketLengthMode(packetLength)
        ASSERT(state)
        state = self.setFrequency(freq)
        ASSERT(state)
        state = self.setOutputPower(power)
        ASSERT(state)
        state = super().fixPaClamping()
        ASSERT(state)
        state = self.setBlockingCallback(blocking)
        return state

    def setFrequency(self, freq, calibrate=True):
        """Set frequency with automatic calibration"""
        if freq < 150.0 or freq > 960.0:
            return ERR_INVALID_FREQUENCY
        state = ERR_NONE
        if calibrate:
            data = bytearray(2)
            if freq > 900.0:
                data[0] = SX126X_CAL_IMG_902_MHZ_1
                data[1] = SX126X_CAL_IMG_902_MHZ_2
            elif freq > 850.0:
                data[0] = SX126X_CAL_IMG_863_MHZ_1
                data[1] = SX126X_CAL_IMG_863_MHZ_2
            elif freq > 770.0:
                data[0] = SX126X_CAL_IMG_779_MHZ_1
                data[1] = SX126X_CAL_IMG_779_MHZ_2
            elif freq > 460.0:
                data[0] = SX126X_CAL_IMG_470_MHZ_1
                data[1] = SX126X_CAL_IMG_470_MHZ_2
            else:
                data[0] = SX126X_CAL_IMG_430_MHZ_1
                data[1] = SX126X_CAL_IMG_430_MHZ_2
            state = super().calibrateImage(data)
            ASSERT(state)
        return super().setFrequencyRaw(freq)

    def setOutputPower(self, power):
        """Set output power"""
        if not ((power >= -9) and (power <= 22)):
            return ERR_INVALID_OUTPUT_POWER
        ocp = bytearray(1)
        ocp_mv = memoryview(ocp)
        state = super().readRegister(SX126X_REG_OCP_CONFIGURATION, ocp_mv, 1)
        ASSERT(state)
        state = super().setPaConfig(0x04, _SX126X_PA_CONFIG_SX1262)
        ASSERT(state)
        state = super().setTxParams(power)
        ASSERT(state)
        return super().writeRegister(SX126X_REG_OCP_CONFIGURATION, ocp, 1)

    def setBlockingCallback(self, blocking, callback=None):
        """Set blocking/non-blocking mode"""
        self.blocking = blocking
        if not self.blocking:
            # Non-blocking: start receive mode immediately
            state = super().startReceive()
            ASSERT(state)
            if callback != None:
                self._callbackFunction = callback
                super().setDio1Action(self._onIRQ)
            else:
                self._callbackFunction = self._dummyFunction
                super().clearDio1Action()
            return state
        else:
            # Blocking: put in standby
            state = super().standby()
            ASSERT(state)
            self._callbackFunction = self._dummyFunction
            super().clearDio1Action()
            return state

    def recv(self, len=0, timeout_en=False, timeout_ms=0):
        """Receive data - routes to blocking or non-blocking handler"""
        if not self.blocking:
            return self._readData(len)
        else:
            return self._receive(len, timeout_en, timeout_ms)

    def send(self, data):
        """Send data - routes to blocking or non-blocking handler"""
        if not self.blocking:
            return self._startTransmit(data)
        else:
            return self._transmit(data)

    def _receive(self, len_=0, timeout_en=False, timeout_ms=0):
        """Blocking receive"""
        length = len_ if len_ > 0 else SX126X_MAX_PACKET_LENGTH
        data = bytearray(length)
        data_mv = memoryview(data)
        try:
            state = super().receive(data_mv, length, timeout_en, timeout_ms)
        except AssertionError as e:
            state = list(ERROR.keys())[list(ERROR.values()).index(str(e))]
        if state == ERR_NONE or state == ERR_CRC_MISMATCH:
            if len_ == 0:
                length = super().getPacketLength(False)
                data = data[:length]
            return bytes(data), state
        return b'', state

    def _transmit(self, data):
        """Blocking transmit"""
        if not isinstance(data, (bytes, bytearray)):
            return 0, ERR_INVALID_PACKET_TYPE
        state = super().transmit(data, len(data))
        return len(data), state

    def _readData(self, len_=0):
        """Non-blocking receive - simplified version"""
        # Get packet length first
        try:
            length = super().getPacketLength()
            if length == 0:
                # No packet available
                return b'', ERR_RX_TIMEOUT
            if length > SX126X_MAX_PACKET_LENGTH:
                # Invalid length - restart receive
                super().startReceive()
                return b'', ERR_RX_TIMEOUT
        except:
            # Error getting length - restart receive
            super().startReceive()
            return b'', ERR_RX_TIMEOUT

        # Adjust length if needed
        if len_ > 0 and len_ < length:
            length = len_

        # Read the packet
        data = bytearray(length)
        data_mv = memoryview(data)
        try:
            state = super().readData(data_mv, length)
        except AssertionError as e:
            state = list(ERROR.keys())[list(ERROR.values()).index(str(e))]

        # Always restart receive mode after reading
        super().startReceive()

        if state == ERR_NONE or state == ERR_CRC_MISMATCH:
            return bytes(data), state
        return b'', state

    def _startTransmit(self, data):
        """Non-blocking transmit"""
        if not isinstance(data, (bytes, bytearray)):
            return 0, ERR_INVALID_PACKET_TYPE
        state = super().startTransmit(data, len(data))
        return len(data), state

    def _dummyFunction(self, *args):
        """Dummy callback function"""
        pass

    def _onIRQ(self, callback):
        """IRQ callback handler"""
        events = super().getIrqStatus()
        if events & SX126X_IRQ_TX_DONE:
            super().startReceive()
        self._callbackFunction(events)
