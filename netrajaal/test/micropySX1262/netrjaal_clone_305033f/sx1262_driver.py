from _sx126x import *
from sx126x import SX126X

_SX126X_PA_CONFIG_SX1262 = const(0x00)

class SX1262(SX126X):
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
                 tcxoVoltage=1.6, useRegulatorLDO=False,
                 blocking=True):
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

    def setTxIq(self, txIq):
        self._txIq = txIq

    def setRxIq(self, rxIq):
        self._rxIq = rxIq
        if not self.blocking:
            ASSERT(super().startReceive())

    def setPreambleDetectorLength(self, preambleDetectorLength):
        self._preambleDetectorLength = preambleDetectorLength
        if not self.blocking:
            ASSERT(super().startReceive())

    def setBlockingCallback(self, blocking, callback=None):
        self.blocking = blocking
        if not self.blocking:
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
            state = super().standby()
            ASSERT(state)
            self._callbackFunction = self._dummyFunction
            super().clearDio1Action()
            return state

    def recv(self, len=0, timeout_en=False, timeout_ms=0):
        if not self.blocking:
            return self._readData(len)
        else:
            return self._receive(len, timeout_en, timeout_ms)

    def send(self, data):
        if not self.blocking:
            return self._startTransmit(data)
        else:
            return self._transmit(data)

    def _events(self):
        return super().getIrqStatus()

    def _receive(self, len_=0, timeout_en=False, timeout_ms=0):
        state = ERR_NONE
        
        length = len_
        
        if len_ == 0:
            length = SX126X_MAX_PACKET_LENGTH

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

        else:
            return b'', state

        return  bytes(data), state

    def _transmit(self, data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            pass
        else:
            return 0, ERR_INVALID_PACKET_TYPE

        state = super().transmit(data, len(data))
        return len(data), state

    def _readData(self, len_=0):
        state = ERR_NONE

        try:
            length = super().getPacketLength()
            if length == 0 or length > SX126X_MAX_PACKET_LENGTH:
                # No valid packet or invalid length, restart receive
                super().startReceive()
                return b'', ERR_RX_TIMEOUT
        except Exception as e:
            # getPacketLength failed, restart receive
            try:
                super().startReceive()
            except:
                pass
            return b'', ERR_RX_TIMEOUT

        if len_ < length and len_ != 0:
            length = len_

        data = bytearray(length)
        data_mv = memoryview(data)

        try:
            state = super().readData(data_mv, length)
        except AssertionError as e:
            state = list(ERROR.keys())[list(ERROR.values()).index(str(e))]

        ASSERT(super().startReceive())

        if state == ERR_NONE or state == ERR_CRC_MISMATCH:
            return bytes(data), state

        else:
            return b'', state

    def _startTransmit(self, data):
        if isinstance(data, bytes) or isinstance(data, bytearray):
            pass
        else:
            return 0, ERR_INVALID_PACKET_TYPE

        state = super().startTransmit(data, len(data))
        return len(data), state

    def _dummyFunction(self, *args):
        pass

    def _onIRQ(self, callback):
        events = self._events()
        if events & SX126X_IRQ_TX_DONE:
            super().startReceive()
        self._callbackFunction(events)


# Wrapper class for Netrajaal Project compatibility
# Maintains compatibility with old UART-based sx126x driver interface
try:
    from logger import logger
    import time
    
    # High-speed LoRa configuration for maximum data rate
    # SF5, BW500kHz, CR5 (4/5) provides ~37-40 kbps practical data rate
    LORA_SF = 5
    LORA_BW = 500.0
    LORA_CR = 5
    LORA_SYNC_WORD = SX126X_SYNC_WORD_PRIVATE
    LORA_PREAMBLE_LENGTH = 8
    LORA_CRC_ON = True
    LORA_IMPLICIT = False
    
    # SPI Pin Configuration for OpenMV RT1062
    SPI_BUS = 1
    P0_MOSI = 'P0'
    P1_MISO = 'P1'
    P2_SCLK = 'P2'
    P3_CS = 'P3'
    P6_RST = 'P6'
    P7_BUSY = 'P7'
    P13_DIO1 = 'P13'
    
    # SPI Configuration
    SPI_BAUDRATE = 2000000
    SPI_POLARITY = 0
    SPI_PHASE = 0
    
    # Timing constants
    TX_DELAY_MS = 5
    
    # Frequency ranges for offset calculation
    FREQ_RANGE_400MHZ_START = 410
    FREQ_RANGE_900MHZ_START = 850
    
    class sx126x:
        """
        Wrapper class for SX1262 SPI driver that maintains compatibility
        with the old UART-based sx126x driver interface.
        """
        
        def __init__(
            self,
            uart_num=1,
            freq=868,
            addr=0,
            power=22,
            rssi=False,
            air_speed=2400,
            net_id=0,
            buffer_size=240,
            crypt=0,
            relay=False,
            lbt=False,
            wor=False,
            m0_pin="P6",
            m1_pin="P7",
        ):
            self.addr = addr
            self.freq = freq
            self.power = power
            self.rssi = rssi
            self.is_connected = False
            
            # Calculate frequency offset for compatibility
            if freq > FREQ_RANGE_900MHZ_START:
                self.offset_freq = freq - FREQ_RANGE_900MHZ_START
            elif freq > FREQ_RANGE_400MHZ_START:
                self.offset_freq = freq - FREQ_RANGE_400MHZ_START
            else:
                raise ValueError(f"Frequency {freq} MHz out of valid range (410-493 or 850-930)")
            
            logger.info(f"Initializing SX1262 SPI driver... freq={freq}MHz, addr={addr}")
            
            try:
                self.sx1262 = SX1262(
                    spi_bus=SPI_BUS,
                    clk=P2_SCLK,
                    mosi=P0_MOSI,
                    miso=P1_MISO,
                    cs=P3_CS,
                    irq=P13_DIO1,
                    rst=P6_RST,
                    gpio=P7_BUSY,
                    spi_baudrate=SPI_BAUDRATE,
                    spi_polarity=SPI_POLARITY,
                    spi_phase=SPI_PHASE
                )
                
                logger.info(f"Configuring LoRa mode: SF{LORA_SF}, BW{LORA_BW}kHz, CR{LORA_CR} (4/{LORA_CR})")
                status = self.sx1262.begin(
                    freq=freq,
                    bw=LORA_BW,
                    sf=LORA_SF,
                    cr=LORA_CR,
                    syncWord=LORA_SYNC_WORD,
                    power=power,
                    currentLimit=140.0,
                    preambleLength=LORA_PREAMBLE_LENGTH,
                    implicit=LORA_IMPLICIT,
                    implicitLen=0xFF,
                    crcOn=LORA_CRC_ON,
                    txIq=False,
                    rxIq=False,
                    tcxoVoltage=1.6,
                    useRegulatorLDO=False,
                    blocking=False
                )
                
                if status != ERR_NONE:
                    logger.error(f"SX1262 initialization failed with status: {status}")
                    self.is_connected = False
                    raise Exception(f"SX1262 initialization failed: {status}")
                
                self.is_connected = True
                
                # Start receive mode - critical for receiving packets
                # Add small delay to ensure module is ready
                time.sleep_ms(10)
                try:
                    state = self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                    if state != ERR_NONE:
                        logger.warning(f"startReceive returned status: {state}, retrying...")
                        # Retry starting receive mode
                        time.sleep_ms(20)
                        state = self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                        if state != ERR_NONE:
                            logger.error(f"startReceive failed after retry: {state}")
                        else:
                            logger.info(f"SX1262 initialized successfully! LoRa mode: SF{LORA_SF}, BW{LORA_BW}kHz, CR{LORA_CR}, receive mode active")
                    else:
                        logger.info(f"SX1262 initialized successfully! LoRa mode: SF{LORA_SF}, BW{LORA_BW}kHz, CR{LORA_CR}, receive mode active")
                except Exception as e2:
                    logger.error(f"Failed to start receive mode: {e2}")
                    # Try one more time
                    try:
                        time.sleep_ms(50)
                        state = self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                        if state == ERR_NONE:
                            logger.info(f"Receive mode started after retry")
                        else:
                            logger.error(f"Receive mode start failed after retry, status: {state}")
                    except Exception as e3:
                        logger.error(f"Receive mode start failed after retry: {e3}")
                
                # Initialize receive check counter
                self._receive_check_counter = 0
                
            except Exception as e:
                logger.error(f"SX1262 initialization error: {e}")
                self.is_connected = False
                raise
        
        def send(self, target_addr, message):
            """Send a message to a target node address."""
            if not self.is_connected:
                logger.warning(f"Module not connected, send may fail")
                return
            
            # Build message packet with addressing header
            # Format: [target_high][target_low][target_freq][own_high][own_low][own_freq][message]
            data = (
                bytes([target_addr >> 8])
                + bytes([target_addr & 0xFF])
                + bytes([self.offset_freq])
                + bytes([self.addr >> 8])
                + bytes([self.addr & 0xFF])
                + bytes([self.offset_freq])
                + message
            )
            
            try:
                bytes_sent, status = self.sx1262.send(data)
                if status != ERR_NONE:
                    logger.warning(f"Send failed with status: {status}")
                    # Restart receive mode even on failure
                    try:
                        self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                    except:
                        pass
                else:
                    # Wait for transmission to complete (TX_DONE interrupt)
                    # For SF5/BW500kHz, transmission is very fast (~2-3ms for 200 bytes)
                    max_wait = 50  # Maximum wait time in ms (reduced for fast LoRa)
                    wait_count = 0
                    tx_complete = False
                    while wait_count < max_wait:
                        irq_status = self.sx1262.getIrqStatus()
                        if irq_status & SX126X_IRQ_TX_DONE:
                            # Clear TX_DONE interrupt
                            self.sx1262.clearIrqStatus(SX126X_IRQ_TX_DONE)
                            tx_complete = True
                            break
                        time.sleep_ms(1)
                        wait_count += 1
                    
                    if not tx_complete:
                        logger.warning(f"TX_DONE not received within {max_wait}ms, clearing IRQ and continuing")
                        # Clear any pending TX interrupts
                        self.sx1262.clearIrqStatus(SX126X_IRQ_TX_DONE)
                    
                    # Restart receive mode after transmission (critical!)
                    try:
                        state = self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                        if state != ERR_NONE:
                            logger.warning(f"Failed to restart receive after send, status: {state}")
                    except Exception as e:
                        logger.warning(f"Failed to restart receive after send: {e}")
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                # Restart receive mode on error
                try:
                    self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                except:
                    pass
        
        def receive(self):
            """Receive a message from the LoRa module (non-blocking)."""
            if not self.is_connected:
                return None, None
            
            try:
                # Periodically ensure receive mode is active (every 100 calls)
                self._receive_check_counter += 1
                if self._receive_check_counter >= 100:
                    self._receive_check_counter = 0
                    # Ensure receive mode is still active
                    try:
                        self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                    except:
                        pass
                
                # Check IRQ status to see if RX_DONE is set
                irq_status = self.sx1262.getIrqStatus()
                
                # Check for RX_DONE interrupt (packet received)
                if irq_status & SX126X_IRQ_RX_DONE:
                    # Read packet - _readData() will handle packet length and restart receive
                    data, status = self.sx1262.recv(len=0, timeout_en=False, timeout_ms=0)
                    
                    # Note: readData() already clears IRQ internally, but we clear again to be sure
                    # Clear all IRQ flags after reading to ensure clean state
                    self.sx1262.clearIrqStatus(
                        SX126X_IRQ_RX_DONE | SX126X_IRQ_TX_DONE | SX126X_IRQ_RX_TIMEOUT | 
                        SX126X_IRQ_CRC_ERR | SX126X_IRQ_HEADER_ERR
                    )
                    
                    if status == ERR_NONE or status == ERR_CRC_MISMATCH:
                        if data and len(data) >= 7:
                            # Extract message payload (skip first 6 bytes: addressing header)
                            msg = data[6:]
                            
                            if len(msg) == 0:
                                return None, None
                            
                            # Get RSSI if enabled
                            rssi_value = None
                            if self.rssi:
                                try:
                                    rssi_value = self.sx1262.getRSSI()
                                except:
                                    pass
                            
                            return msg, rssi_value
                    else:
                        # Packet read failed, ensure receive mode is restarted
                        try:
                            self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                        except:
                            pass
                
                # Check for RX_TIMEOUT - restart receive mode (normal in continuous receive)
                elif irq_status & SX126X_IRQ_RX_TIMEOUT:
                    self.sx1262.clearIrqStatus(SX126X_IRQ_RX_TIMEOUT)
                    # Restart receive mode to continue listening
                    try:
                        self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                    except:
                        pass
                
                # Check for CRC error - still read and restart
                elif irq_status & SX126X_IRQ_CRC_ERR:
                    # Read the packet even with CRC error (might be useful for debugging)
                    data, status = self.sx1262.recv(len=0, timeout_en=False, timeout_ms=0)
                    self.sx1262.clearIrqStatus(SX126X_IRQ_CRC_ERR | SX126X_IRQ_RX_DONE)
                    # Restart receive mode
                    try:
                        self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                    except:
                        pass
                
                # No relevant IRQ set - return None (normal polling case)
                # Receive mode should already be active from initialization
                return None, None
                    
            except Exception as e:
                logger.debug(f"Receive error: {e}")
                # Ensure receive mode is restarted on error
                try:
                    self.sx1262.startReceive(SX126X_RX_TIMEOUT_INF)
                except:
                    pass
                return None, None

except ImportError:
    # logger not available, wrapper class not defined
    pass
