"""
SX1262 LoRa Radio Driver for OpenMV RT1062 (MicroPython)
Point-to-Point (P2P) Communication Only - No LoRaWAN

Hardware Configuration:
- SPI Bus: P0=MOSI, P1=MISO, P2=SCK, P3=SS/CS
- GPIO: P7=BUSY, P13=RESET, P6=DIO1 (IRQ)
"""

from machine import SPI, Pin
import time

# ============================================================================
# SX1262 Command Opcodes (from datasheet)
# ============================================================================

# Operating Mode Commands
CMD_SET_SLEEP = 0x84
CMD_SET_STANDBY = 0x80
CMD_SET_TX = 0x83
CMD_SET_RX = 0x82
CMD_STOP_TIMER_ON_PREAMBLE = 0x9F
CMD_SET_RX_DUTY_CYCLE = 0x94
CMD_SET_CAD = 0xC5
CMD_SET_TX_CONTINUOUS_WAVE = 0xD1
CMD_SET_TX_INFINITE_PREAMBLE = 0xD2
CMD_SET_REGULATOR_MODE = 0x96
CMD_CALIBRATE = 0x89
CMD_CALIBRATE_IMAGE = 0x98
CMD_SET_PA_CONFIG = 0x95
CMD_SET_TX_PARAMS = 0x8E
CMD_SET_RX_TX_FALLBACK_MODE = 0x93

# Register and Buffer Access
CMD_WRITE_REGISTER = 0x0D
CMD_READ_REGISTER = 0x1D
CMD_WRITE_BUFFER = 0x0E
CMD_READ_BUFFER = 0x1E

# Status and Information
CMD_SET_DIO3_AS_TCXO_CTRL = 0x97
CMD_SET_DIO2_AS_RF_SWITCH_CTRL = 0x9D
CMD_GET_STATUS = 0xC0
CMD_GET_RSSI_INST = 0x15
CMD_GET_RX_BUFFER_STATUS = 0x13
CMD_GET_PACKET_STATUS = 0x14
CMD_GET_DEVICE_ERRORS = 0x17
CMD_CLEAR_DEVICE_ERRORS = 0x07
CMD_GET_STATS = 0x10
CMD_RESET_STATS = 0x00

# DIO and IRQ Control
CMD_SET_DIO_IRQ_PARAMS = 0x08
CMD_GET_IRQ_STATUS = 0x12
CMD_CLEAR_IRQ_STATUS = 0x02

# RF and Modulation
CMD_SET_RF_FREQUENCY = 0x86
CMD_SET_PACKET_TYPE = 0x8A
CMD_SET_MODULATION_PARAMS = 0x8B
CMD_SET_PACKET_PARAMS = 0x8C
CMD_SET_CAD_PARAMS = 0x88
CMD_SET_BUFFER_BASE_ADDRESS = 0x8F
CMD_SET_LORA_SYMB_NUM_TIMEOUT = 0x0A

# ============================================================================
# SX1262 Register Addresses
# ============================================================================

REG_LR_WHITEPUBLICKEY_BASE = 0x06B8
REG_LR_CRCPOLYBASE = 0x06B9
REG_LR_CRCINITBASE = 0x06BB
REG_LR_CRCSEEDBASE = 0x06BC
REG_LR_PACKETPARAMS = 0x0704
REG_LR_PAYLOADLENGTH = 0x0702
REG_LR_SYNCWORD = 0x0740
REG_LR_SYNCWORDBASE = 0x0740

# ============================================================================
# SX1262 Constants
# ============================================================================

# Standby Modes
STDBY_RC = 0x00  # RC oscillator
STDBY_XOSC = 0x01  # Crystal oscillator

# Packet Types
PACKET_TYPE_GFSK = 0x00
PACKET_TYPE_LORA = 0x01

# IRQ Masks
IRQ_TX_DONE = 0x01
IRQ_RX_DONE = 0x02
IRQ_PREAMBLE_DETECTED = 0x04
IRQ_SYNCWORD_VALID = 0x08
IRQ_HEADER_VALID = 0x10
IRQ_HEADER_ERROR = 0x20
IRQ_CRC_ERROR = 0x40
IRQ_RX_TX_TIMEOUT = 0x80
IRQ_RANGING_SLAVE_RESPONSE_DONE = 0x100
IRQ_RANGING_SLAVE_REQUEST_DISCARDED = 0x200
IRQ_RANGING_MASTER_RESULT_VALID = 0x400
IRQ_RANGING_MASTER_RESULT_TIMEOUT = 0x800
IRQ_RANGING_SLAVE_REQUEST_VALID = 0x1000
IRQ_CAD_DONE = 0x2000
IRQ_CAD_DETECTED = 0x4000
IRQ_RX_PREAMBLE_DETECTED = 0x8000

# LoRa Spreading Factors
SF_5 = 0x05
SF_6 = 0x06
SF_7 = 0x07
SF_8 = 0x08
SF_9 = 0x09
SF_10 = 0x0A
SF_11 = 0x0B
SF_12 = 0x0C

# LoRa Bandwidth
BW_7_8 = 0x00
BW_10_4 = 0x01
BW_15_6 = 0x02
BW_20_8 = 0x03
BW_31_25 = 0x04
BW_41_7 = 0x05
BW_62_5 = 0x06
BW_125 = 0x07
BW_250 = 0x08
BW_500 = 0x09

# LoRa Coding Rate
CR_4_5 = 0x01
CR_4_6 = 0x02
CR_4_7 = 0x03
CR_4_8 = 0x04

# ============================================================================
# SX1262 Driver Class
# ============================================================================

class SX1262:
    """
    SX1262 LoRa Radio Driver
    
    Provides point-to-point LoRa communication without LoRaWAN.
    Handles SPI communication, BUSY pin, and basic TX/RX operations.
    """
    
    def __init__(self, spi, cs, busy, reset, dio1=None, freq=868000000):
        """
        Initialize SX1262 driver
        
        Args:
            spi: SPI bus instance (already configured)
            cs: Chip Select pin (Pin object)
            busy: BUSY pin (Pin object, input)
            reset: RESET pin (Pin object, output)
            dio1: DIO1/IRQ pin (Pin object, input, optional)
            freq: RF frequency in Hz (default: 868 MHz)
        """
        self.spi = spi
        self.cs = cs
        self.busy = busy
        self.reset = reset
        self.dio1 = dio1
        self.freq = freq
        
        # Configure pins
        self.cs.init(Pin.OUT, value=1)  # CS high (inactive)
        self.busy.init(Pin.IN)
        self.reset.init(Pin.OUT, value=1)  # Reset high (normal)
        if self.dio1:
            self.dio1.init(Pin.IN)
        
        # Reset sequence
        self._reset()
        
        # Wake up from sleep
        self._wakeup()
        
        # Verify communication (status should be readable)
        # Note: Status 0 might be valid, so we just check that we can read it
        try:
            status = self.get_status()
            # Status byte format: bit 7-6 = chip mode, should not be 0xFF if communication works
            if status == 0xFF:
                raise RuntimeError("SX1262 communication failed - check SPI connections")
        except Exception as e:
            raise RuntimeError(f"SX1262 initialization failed: {e}")
    
    def _wait_on_busy(self):
        """
        Wait until BUSY pin goes low (chip ready for SPI communication)
        SX1262 sets BUSY high during command processing
        
        If BUSY times out, try to recover by forcing reset or standby
        """
        timeout = 1000  # Maximum wait time in ms
        start = time.ticks_ms()
        while self.busy.value() == 1:
            elapsed = time.ticks_diff(time.ticks_ms(), start)
            if elapsed > timeout:
                # BUSY timeout - try to recover
                print(f"[WARN] BUSY timeout ({elapsed}ms), attempting recovery...")
                # Try sending a simple command to wake chip
                try:
                    # Force CS low/high to reset SPI state
                    self.cs.value(0)
                    time.sleep_us(10)
                    self.cs.value(1)
                    time.sleep_ms(10)
                    # Try standby command to reset state
                    if self.busy.value() == 0:
                        return  # Recovery successful
                    # If still HIGH, try reset
                    print("[WARN] Attempting hardware reset...")
                    self._reset()
                    return  # Reset complete, BUSY should be LOW now
                except:
                    pass
                raise RuntimeError("SX1262 BUSY timeout - chip may be stuck")
            time.sleep_us(10)  # Small delay to avoid tight loop
    
    def _wait_on_busy_extended(self, timeout_ms=5000):
        """
        Wait until BUSY pin goes low with extended timeout
        
        Args:
            timeout_ms: Maximum wait time in milliseconds (default: 5000ms for SetTx operations)
        
        Used for operations that take longer (SetTx, SetRx, calibration)
        
        Note: After SetTx/SetRx, chip may need a moment to start processing.
        We wait briefly, then check BUSY state.
        """
        # Small delay to allow chip to start processing command
        # Some commands (like SetTx) may not assert BUSY immediately
        time.sleep_us(100)  # 100us delay
        
        # Check BUSY state
        if self.busy.value() == 0:
            # BUSY is LOW - command may have completed very quickly
            # This is OK for some commands
            return
        
        # BUSY is HIGH - wait for it to go LOW
        start = time.ticks_ms()
        while self.busy.value() == 1:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                raise RuntimeError(f"SX1262 BUSY timeout after {timeout_ms}ms - chip may be stuck")
            time.sleep_us(10)  # Small delay to avoid tight loop
    
    def _reset(self):
        """
        Hardware reset sequence for SX1262
        Pull RESET low for >100us, then release
        """
        self.reset.value(0)
        time.sleep_ms(10)  # Hold reset low
        self.reset.value(1)  # Release reset
        time.sleep_ms(10)  # Wait for chip to stabilize
        self._wait_on_busy()  # Wait for chip to be ready
    
    def _wakeup(self):
        """
        Wake up SX1262 from sleep mode
        Sends GET_STATUS command to wake chip
        """
        self._wait_on_busy()
        self.cs.value(0)  # CS low (active)
        self.spi.write(bytes([CMD_GET_STATUS, 0x00]))
        self.cs.value(1)  # CS high (inactive)
        self._wait_on_busy()
    
    def _write_command(self, cmd, data=None):
        """
        Write command to SX1262 via SPI
        
        Args:
            cmd: Command opcode
            data: Optional data bytes to send after command
        """
        self._wait_on_busy()
        
        self.cs.value(0)  # CS low (active)
        
        if data:
            self.spi.write(bytes([cmd] + list(data)))
        else:
            self.spi.write(bytes([cmd]))
        
        self.cs.value(1)  # CS high (inactive)
        
        # Wait for command to complete (except for SET_SLEEP)
        if cmd != CMD_SET_SLEEP:
            self._wait_on_busy()
    
    def _read_command(self, cmd, length=1):
        """
        Read data from SX1262 via SPI
        
        Args:
            cmd: Command opcode
            length: Number of bytes to read
            
        Returns:
            bytes: Response data
        """
        self._wait_on_busy()
        
        self.cs.value(0)  # CS low (active)
        
        # Send command
        self.spi.write(bytes([cmd]))
        
        # Read response by writing dummy bytes
        dummy = bytes([0x00] * length)
        response = bytearray(length)
        self.spi.write_readinto(dummy, response)
        
        self.cs.value(1)  # CS high (inactive)
        self._wait_on_busy()
        
        return bytes(response)
    
    def _write_register(self, address, value):
        """
        Write to SX1262 register
        
        Args:
            address: 16-bit register address
            value: 8-bit value or list of bytes
        """
        if isinstance(value, int):
            value = [value]
        
        addr_bytes = [(address >> 8) & 0xFF, address & 0xFF]
        self._write_command(CMD_WRITE_REGISTER, addr_bytes + value)
    
    def _read_register(self, address, length=1):
        """
        Read from SX1262 register
        
        Args:
            address: 16-bit register address
            length: Number of bytes to read
            
        Returns:
            bytes: Register value(s)
        """
        self._wait_on_busy()
        
        self.cs.value(0)
        # Send command
        self.spi.write(bytes([CMD_READ_REGISTER]))
        # Send address (MSB, LSB)
        addr_bytes = [(address >> 8) & 0xFF, address & 0xFF]
        self.spi.write(bytes(addr_bytes))
        # Send dummy byte, then read data
        response = bytearray(length)
        dummy = bytes([0x00] * length)
        self.spi.write_readinto(dummy, response)
        
        self.cs.value(1)
        self._wait_on_busy()
        
        return bytes(response)
    
    # ========================================================================
    # Public API Methods
    # ========================================================================
    
    def get_status(self):
        """
        Get chip status
        
        Returns:
            int: Status byte
        
        Status byte format (from SX1262 datasheet):
        - Bits [7:4]: Command Status
        - Bits [3:1]: Chip Mode
        - Bit [0]: Reserved
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command, then send dummy byte and read status
        # SX1262: send command, then send 0x00 and read status byte
        self.spi.write(bytes([CMD_GET_STATUS]))
        status_byte = bytearray(1)
        self.spi.write_readinto(bytes([0x00]), status_byte)
        self.cs.value(1)
        self._wait_on_busy()
        return status_byte[0]
    
    def get_chip_mode(self):
        """
        Get chip operating mode from status byte
        
        Returns:
            int: Chip mode
            - 0: STDBY_RC
            - 1: STDBY_XOSC
            - 2: FS (Frequency Synthesis)
            - 3: RX
            - 4: TX
        
        Note: Chip mode is in bits [3:1] of status byte, not [7:6]
        Correct decoding: (status >> 1) & 0x07
        """
        status = self.get_status()
        # Chip mode is in bits [3:1] of status byte
        chip_mode = (status >> 1) & 0x07
        return chip_mode
    
    def set_standby(self, mode=STDBY_RC):
        """
        Set chip to standby mode
        
        Args:
            mode: STDBY_RC (0x00) or STDBY_XOSC (0x01)
        
        Note: After TCXO is configured, the chip may prefer XOSC mode.
        Mode switching should work, but requires proper timing.
        """
        self._wait_on_busy()  # Ensure chip is ready
        self._write_command(CMD_SET_STANDBY, [mode])
        self._wait_on_busy()  # Wait for mode transition
        
        # Add delay for mode stabilization
        # RC mode: ~1ms, XOSC mode: ~5ms (TCXO wakeup)
        if mode == STDBY_XOSC:
            time.sleep_ms(5)  # Allow TCXO to stabilize if configured
        else:
            time.sleep_ms(2)  # Allow RC oscillator to stabilize
        
        self._wait_on_busy()  # Final check
    
    def set_sleep(self):
        """Put chip to sleep mode (lowest power)"""
        self._write_command(CMD_SET_SLEEP, [0x00])  # 0x00 = no RTC retention
    
    def set_dio3_as_tcxo_ctrl(self, voltage=0x00, wakeup_time_ms=5):
        """
        Configure DIO3 as TCXO control
        
        Args:
            voltage: TCXO voltage (0x00 = 1.6V, 0x01 = 1.7V, 0x02 = 1.8V, 0x03 = 2.2V, 0x04 = 2.4V, 0x05 = 2.7V, 0x06 = 3.0V, 0x07 = 3.3V)
            wakeup_time_ms: TCXO wakeup time in milliseconds (typical: 5ms)
        
        Note: Required for stable frequency reference during TX/RX operations.
        Without this configuration, the chip may fail to enter TX mode (error 0x0020).
        """
        # Convert wakeup time to SX1262 time base (time_ms << 6)
        # Time base unit: 15.625 µs, so time_ms * 64 = time base value
        time_base = int(wakeup_time_ms * 64)
        time_bytes = [
            (time_base >> 8) & 0xFF,
            time_base & 0xFF
        ]
        self._write_command(CMD_SET_DIO3_AS_TCXO_CTRL, [voltage] + time_bytes)
    
    def set_dio2_as_rf_switch_ctrl(self, enable=True):
        """
        Configure DIO2 as RF switch control
        
        Args:
            enable: True to enable RF switch control, False to disable
        
        Note: Required for proper TX/RX antenna switching.
        Without this configuration, the chip cannot switch to TX path (error 0x0020).
        """
        enable_byte = 0x01 if enable else 0x00
        self._write_command(CMD_SET_DIO2_AS_RF_SWITCH_CTRL, [enable_byte])
    
    def calibrate_image(self, freq1=863000000, freq2=870000000):
        """
        Calibrate image rejection for specific frequency band
        
        Args:
            freq1: First calibration frequency in Hz (default: 863MHz for EU868)
            freq2: Second calibration frequency in Hz (default: 870MHz for EU868)
        
        Note: REQUIRED after SetRfFrequency and before TX operations.
        Without this, the chip cannot lock to target frequency and SetTx() will timeout.
        CalibrateImage must be called after frequency is set.
        
        For 868MHz band, calibrates at two frequencies in the band for optimal performance.
        """
        # Convert frequencies to SX1262 register format
        # Formula: Freq = (frequency_in_hz * 2^25) / 32000000
        def freq_to_reg(freq):
            return int((freq * (2**25)) / 32000000)
        
        freq1_reg = freq_to_reg(freq1)
        freq2_reg = freq_to_reg(freq2)
        
        # Format: [freq1_msb, freq1_lsb, freq2_msb, freq2_lsb]
        # SX1262 expects 16-bit frequency values (MSB, LSB)
        calib_bytes = [
            (freq1_reg >> 8) & 0xFF,
            freq1_reg & 0xFF,
            (freq2_reg >> 8) & 0xFF,
            freq2_reg & 0xFF
        ]
        
        # CalibrateImage can take longer than normal commands
        # Use extended timeout to prevent BUSY timeout
        self._wait_on_busy()
        self.cs.value(0)
        self.spi.write(bytes([CMD_CALIBRATE_IMAGE] + calib_bytes))
        self.cs.value(1)
        # Use extended timeout for CalibrateImage (can take up to 2-3 seconds)
        # If it times out, don't fail - some modules handle this differently
        try:
            self._wait_on_busy_extended(timeout_ms=3000)
            time.sleep_ms(10)  # Allow image calibration to complete
        except RuntimeError as e:
            # If CalibrateImage times out, force recovery
            print(f"[WARN] CalibrateImage timeout, recovering...")
            # Force chip back to known state
            try:
                # Try to reset BUSY by sending standby command
                self.cs.value(0)
                time.sleep_us(10)
                self.cs.value(1)
                time.sleep_ms(10)
                # If still stuck, try reset
                if self.busy.value() == 1:
                    self._reset()
                else:
                    self.clear_device_errors()
            except:
                # If recovery fails, do hardware reset
                self._reset()
    
    def set_packet_type(self, packet_type=PACKET_TYPE_LORA):
        """
        Set packet type (LoRa or GFSK)
        
        Args:
            packet_type: PACKET_TYPE_LORA (0x01) or PACKET_TYPE_GFSK (0x00)
        """
        self._write_command(CMD_SET_PACKET_TYPE, [packet_type])
    
    def set_rf_frequency(self, frequency):
        """
        Set RF frequency
        
        Args:
            frequency: Frequency in Hz (e.g., 868000000 for 868 MHz)
        """
        # Convert Hz to SX1262 frequency register value
        # Formula: Freq = (frequency_in_hz * 2^25) / 32000000
        freq_reg = int((frequency * (2**25)) / 32000000)
        freq_bytes = [
            (freq_reg >> 24) & 0xFF,
            (freq_reg >> 16) & 0xFF,
            (freq_reg >> 8) & 0xFF,
            freq_reg & 0xFF
        ]
        self._write_command(CMD_SET_RF_FREQUENCY, freq_bytes)
        self.freq = frequency
    
    def set_modulation_params(self, sf, bw, cr, ldro=0):
        """
        Set LoRa modulation parameters
        
        Args:
            sf: Spreading factor (SF_5 to SF_12)
            bw: Bandwidth (BW_7_8 to BW_500)
            cr: Coding rate (CR_4_5 to CR_4_8)
            ldro: Low Data Rate Optimize (0 or 1)
        """
        self._write_command(CMD_SET_MODULATION_PARAMS, [sf, bw, cr, ldro])
    
    def set_packet_params(self, preamble_length, header_type, payload_length, crc_type, invert_iq=0):
        """
        Set LoRa packet parameters
        
        Args:
            preamble_length: Preamble length (typically 12)
            header_type: 0=explicit, 1=implicit
            payload_length: Payload length in bytes (0 for variable length)
            crc_type: 0=no CRC, 1=CRC enabled
            invert_iq: 0=normal, 1=inverted (for P2P, use 0)
        """
        params = [
            (preamble_length >> 8) & 0xFF,
            preamble_length & 0xFF,
            header_type,
            payload_length,
            crc_type,
            invert_iq
        ]
        self._write_command(CMD_SET_PACKET_PARAMS, params)
    
    def set_tx_params(self, power, ramp_time=0x04):
        """
        Set TX power and ramp time
        
        Args:
            power: TX power in dBm (-9 to +22 for SX1262)
            ramp_time: Ramp time (0x04 = 40us typical)
        """
        # Clamp power to valid range
        if power > 22:
            power = 22
        if power < -9:
            power = -9
        
        # SX1262 power register mapping (non-linear)
        # Correct mapping from datasheet
        power_map = {
            22: 0x00, 20: 0x01, 18: 0x02, 16: 0x03,
            14: 0x04, 13: 0x05, 12: 0x06, 10: 0x07,
            9: 0x08, 8: 0x09, 7: 0x0A, 6: 0x0B,
            5: 0x0C, 4: 0x0D, 3: 0x0E, 2: 0x0F
        }
        power_reg = power_map.get(power, 0x04)  # Default to 14dBm if not in map
        
        # PA config: [paDutyCycle, hpMax, deviceSel, paLut]
        # For SX1262, 868MHz, 14dBm: [0x04, 0x00, 0x01, 0x01]
        # For higher power (up to 22dBm): [0x04, 0x07, 0x00, 0x01]
        if power >= 14:
            # Use HP mode for higher power
            self._write_command(CMD_SET_PA_CONFIG, [0x04, 0x07, 0x00, 0x01])
        else:
            # Use standard mode for lower power
            self._write_command(CMD_SET_PA_CONFIG, [0x04, 0x00, 0x01, 0x01])
        
        self._write_command(CMD_SET_TX_PARAMS, [power_reg, ramp_time])
    
    def write_buffer(self, offset, data):
        """
        Write data to TX FIFO buffer
        
        Args:
            offset: Buffer offset (typically 0)
            data: Bytes to write
        """
        if isinstance(data, str):
            data = data.encode()
        if isinstance(data, int):
            data = bytes([data])
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        
        self._wait_on_busy()
        self.cs.value(0)
        self.spi.write(bytes([CMD_WRITE_BUFFER, offset]))
        self.spi.write(data)
        self.cs.value(1)
        self._wait_on_busy()
    
    def read_buffer(self, offset, length):
        """
        Read data from RX FIFO buffer
        
        Args:
            offset: Buffer offset
            length: Number of bytes to read
            
        Returns:
            bytes: Read data
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command
        self.spi.write(bytes([CMD_READ_BUFFER]))
        # Send offset
        self.spi.write(bytes([offset]))
        # Send dummy byte, then read data
        response = bytearray(length)
        dummy = bytes([0x00] * length)
        self.spi.write_readinto(dummy, response)
        
        self.cs.value(1)
        self._wait_on_busy()
        
        return bytes(response)
    
    def set_tx(self, timeout=0):
        """
        Start TX operation
        
        Args:
            timeout: Timeout in symbols (0 = no timeout)
        
        Note: SetTx() can take longer than normal commands due to:
        - TCXO wakeup time
        - Frequency lock
        - PA ramp-up
        Uses extended BUSY timeout (5000ms) to accommodate these delays.
        
        Important: After SetTx() command:
        - BUSY may go HIGH immediately (chip processing command)
        - BUSY may stay LOW if command completes very quickly (TX already started)
        - We wait for BUSY to go LOW, indicating command processing is complete
        - If BUSY is already LOW, the wait completes immediately
        """
        timeout_bytes = [
            (timeout >> 16) & 0xFF,
            (timeout >> 8) & 0xFF,
            timeout & 0xFF
        ]
        # Wait for BUSY before command (chip must be ready)
        self._wait_on_busy()
        
        # Send command
        self.cs.value(0)
        self.spi.write(bytes([CMD_SET_TX] + timeout_bytes))
        self.cs.value(1)
        
        # After SetTx command:
        # - Chip may assert BUSY HIGH immediately (processing command)
        # - Chip may keep BUSY LOW (command processed very quickly)
        # - We wait briefly, then check BUSY state
        # - If BUSY is LOW, command completed quickly (OK)
        # - If BUSY is HIGH, wait for it to go LOW
        time.sleep_us(200)  # Brief delay to allow chip to start processing
        
        # Check BUSY - if LOW, command completed quickly, proceed
        # If HIGH, wait for it to go LOW (command processing)
        if self.busy.value() == 1:
            # BUSY is HIGH - wait for command processing to complete
            self._wait_on_busy_extended(timeout_ms=5000)
        # If BUSY is LOW, command completed quickly - proceed
    
    def set_rx(self, timeout=0xFFFFFF):
        """
        Start RX operation
        
        Args:
            timeout: Timeout in symbols (0xFFFFFF = continuous RX)
        
        Note: SetRx() can take longer than normal commands.
        Uses extended BUSY timeout (3000ms) to accommodate delays.
        """
        timeout_bytes = [
            (timeout >> 16) & 0xFF,
            (timeout >> 8) & 0xFF,
            timeout & 0xFF
        ]
        # Wait for BUSY before command
        self._wait_on_busy()
        
        # Send command
        self.cs.value(0)
        self.spi.write(bytes([CMD_SET_RX] + timeout_bytes))
        self.cs.value(1)
        
        # Use extended timeout for SetRx (allows for TCXO + calibration delays)
        self._wait_on_busy_extended(timeout_ms=3000)
    
    def get_irq_status(self):
        """
        Get IRQ status flags
        
        Returns:
            int: IRQ status (16-bit, lower 2 bytes)
        
        Note: GET_IRQ_STATUS response format (3 bytes):
        - Byte 0: Chip status
        - Byte 1: IRQ status MSB
        - Byte 2: IRQ status LSB
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command, then read 3 bytes (status + IRQ MSB + IRQ LSB)
        # SX1262: send command, then send dummy bytes and read response
        self.spi.write(bytes([CMD_GET_IRQ_STATUS]))
        response = bytearray(3)
        # Send 3 dummy bytes and read 3 response bytes
        self.spi.write_readinto(bytes([0x00, 0x00, 0x00]), response)
        
        self.cs.value(1)
        self._wait_on_busy()
        
        # Response format: [status, irq_msb, irq_lsb]
        irq_status = (response[1] << 8) | response[2]
        return irq_status
    
    def clear_irq_status(self, irq_mask=0xFFFF):
        """
        Clear IRQ status flags
        
        Args:
            irq_mask: IRQ flags to clear (0xFFFF = all)
        """
        mask_bytes = [
            (irq_mask >> 8) & 0xFF,
            irq_mask & 0xFF
        ]
        self._write_command(CMD_CLEAR_IRQ_STATUS, mask_bytes)
    
    def get_device_errors(self):
        """
        Get device error flags
        
        Returns:
            int: Error status (16-bit)
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command, then read 3 bytes (status + error MSB + error LSB)
        self.spi.write(bytes([CMD_GET_DEVICE_ERRORS]))
        response = bytearray(3)
        # Send 3 dummy bytes and read 3 response bytes
        self.spi.write_readinto(bytes([0x00, 0x00, 0x00]), response)
        self.cs.value(1)
        self._wait_on_busy()
        # Response format: [status, error_msb, error_lsb]
        error_status = (response[1] << 8) | response[2]
        return error_status
    
    def clear_device_errors(self):
        """
        Clear device error flags
        """
        self._write_command(CMD_CLEAR_DEVICE_ERRORS, [0x00, 0x00])
    
    def set_dio_irq_params(self, irq_mask, dio1_mask, dio2_mask, dio3_mask):
        """
        Configure DIO IRQ parameters
        
        Args:
            irq_mask: IRQ mask to enable
            dio1_mask: DIO1 IRQ mask
            dio2_mask: DIO2 IRQ mask
            dio3_mask: DIO3 IRQ mask
        """
        params = [
            (irq_mask >> 8) & 0xFF,
            irq_mask & 0xFF,
            (dio1_mask >> 8) & 0xFF,
            dio1_mask & 0xFF,
            (dio2_mask >> 8) & 0xFF,
            dio2_mask & 0xFF,
            (dio3_mask >> 8) & 0xFF,
            dio3_mask & 0xFF
        ]
        self._write_command(CMD_SET_DIO_IRQ_PARAMS, params)
    
    def get_rx_buffer_status(self):
        """
        Get RX buffer status
        
        Returns:
            tuple: (payload_length, rx_start_buffer_pointer)
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command, then read 3 bytes (status + payload_len + rx_start)
        self.spi.write(bytes([CMD_GET_RX_BUFFER_STATUS]))
        response = bytearray(3)
        self.spi.write_readinto(bytes([0x00, 0x00, 0x00]), response)
        
        self.cs.value(1)
        self._wait_on_busy()
        
        # Response format: [status, payload_length, rx_start]
        payload_length = response[1]
        rx_start = response[2]
        return (payload_length, rx_start)
    
    def get_packet_status(self):
        """
        Get packet status (RSSI, SNR)
        
        Returns:
            tuple: (rssi_pkt, snr_pkt, signal_rssi_pkt)
        """
        self._wait_on_busy()
        self.cs.value(0)
        # Send command, then read 4 bytes (status + rssi + snr + signal_rssi)
        self.spi.write(bytes([CMD_GET_PACKET_STATUS]))
        response = bytearray(4)
        self.spi.write_readinto(bytes([0x00, 0x00, 0x00, 0x00]), response)
        
        self.cs.value(1)
        self._wait_on_busy()
        
        # Response format: [status, rssi_pkt, snr_pkt, signal_rssi_pkt]
        rssi_pkt = response[1]
        snr_pkt = response[2] if response[2] < 128 else response[2] - 256
        signal_rssi_pkt = response[3]
        
        return (rssi_pkt, snr_pkt, signal_rssi_pkt)
    
    # ========================================================================
    # High-Level TX/RX Methods
    # ========================================================================
    
    def configure(self, frequency=868000000, sf=SF_7, bw=BW_125, cr=CR_4_5, 
                  tx_power=14, preamble_length=12, payload_length=0):
        """
        Configure radio for TX/RX
        
        Args:
            frequency: RF frequency in Hz
            sf: Spreading factor
            bw: Bandwidth
            cr: Coding rate
            tx_power: TX power in dBm
            preamble_length: Preamble length
            payload_length: Payload length (0 = variable)
        """
        # Set to standby
        self.set_standby(STDBY_RC)
        
        # Set regulator mode to DC-DC (better for TX, provides stable power)
        self._write_command(CMD_SET_REGULATOR_MODE, [0x01])  # 0x01 = DC-DC enabled
        
        # Configure DIO3 as TCXO control (REQUIRED for TX mode)
        # TCXO provides stable frequency reference - without this, chip cannot enter TX (error 0x0020)
        # Voltage: 0x00 = 1.6V, 0x01 = 1.7V (typical for 868MHz modules)
        # Wakeup time: 5ms typical (converted to SX1262 time base)
        self.set_dio3_as_tcxo_ctrl(voltage=0x01, wakeup_time_ms=5)  # 1.7V, 5ms
        
        # Configure DIO2 as RF switch control (REQUIRED for TX/RX switching)
        # RF switch controls antenna path - without this, chip cannot switch to TX path (error 0x0020)
        self.set_dio2_as_rf_switch_ctrl(enable=True)
        
        # Set RF frequency BEFORE calibration (required for CalibrateImage)
        # Frequency must be set before image calibration
        self.set_rf_frequency(frequency)
        
        # Calibrate radio (required after reset for stable operation)
        # Calibrate all: RC64K, RC13M, PLL, ADC, Image
        calib_params = 0x7F
        # Calibrate can take longer - use extended timeout
        self._wait_on_busy()
        self.cs.value(0)
        self.spi.write(bytes([CMD_CALIBRATE, calib_params]))
        self.cs.value(1)
        self._wait_on_busy_extended(timeout_ms=2000)  # Calibration can take 1-2 seconds
        time.sleep_ms(10)  # Allow calibration to complete
        
        # Calibrate image rejection for frequency band
        # Note: Some modules may not require this or may handle it differently
        # If it fails, continue anyway
        try:
            self.calibrate_image(freq1=863000000, freq2=870000000)  # EU868 band
        except RuntimeError:
            # If CalibrateImage fails, continue - some modules may not need it
            print("[WARN] CalibrateImage failed, continuing...")
            # Ensure chip is in known state
            self.set_standby(STDBY_RC)
            time.sleep_ms(10)
        
        # Clear any device errors that may have occurred during initialization
        self.clear_device_errors()
        
        # Ensure chip is in STDBY_RC mode (not XOSC) after configuration
        # This ensures clean state for mode switching
        self.set_standby(STDBY_RC)
        time.sleep_ms(5)
        self._wait_on_busy()  # Ensure transition completes
        
        # Set packet type to LoRa
        self.set_packet_type(PACKET_TYPE_LORA)
        
        # Set modulation parameters
        # Low Data Rate Optimize: enable if symbol time > 16ms
        symbol_time = (2 ** sf) / (bw * 1000)  # ms
        ldro = 1 if symbol_time > 16 else 0
        self.set_modulation_params(sf, bw, cr, ldro)
        
        # Set packet parameters
        header_type = 0 if payload_length == 0 else 1  # 0=explicit (variable), 1=implicit (fixed)
        self.set_packet_params(preamble_length, header_type, payload_length, 1, 0)
        
        # Set buffer base addresses (TX=0x00, RX=0x00)
        # Ensures FIFO writes go to correct location
        self._write_command(CMD_SET_BUFFER_BASE_ADDRESS, [0x00, 0x00])
        
        # Set TX parameters
        self.set_tx_params(tx_power)
        
        # Configure IRQ: TX_DONE and RX_DONE
        self.set_dio_irq_params(
            IRQ_TX_DONE | IRQ_RX_DONE | IRQ_RX_TX_TIMEOUT | IRQ_CRC_ERROR,
            IRQ_TX_DONE | IRQ_RX_DONE,  # DIO1
            0,  # DIO2
            0   # DIO3
        )
        
        # CRITICAL: Ensure chip ends in STDBY_RC mode after configuration
        # Some calibration steps might leave chip in XOSC mode
        # Return to RC mode to ensure clean state for mode switching
        self.set_standby(STDBY_RC)
        time.sleep_ms(5)  # Allow mode transition
        self._wait_on_busy()  # Ensure transition completes
    
    def send(self, data, timeout_ms=5000):
        """
        Send data packet
        
        Args:
            data: Data to send (bytes, bytearray, or string)
            timeout_ms: Timeout in milliseconds
            
        Returns:
            bool: True if TX successful, False on timeout
        
        Note: After TCXO configuration, chip may be in STDBY_XOSC mode,
        which is acceptable and actually preferred for TX operations.
        """
        # CRITICAL: Wait for chip to be ready FIRST (wait for any pending operations)
        # This prevents BUSY timeout if chip is still transitioning from previous operation
        # (e.g., from FS state after previous TX_DONE)
        self._wait_on_busy()
        
        # Switch to XOSC standby before TX (REQUIRED for stable TX)
        # RC oscillator is not stable enough - XOSC provides stable reference
        # This prevents BUSY timeout during SetTx()
        self.set_standby(STDBY_XOSC)
        
        # Clear device errors (stale errors can prevent command execution)
        self.clear_device_errors()
        
        # Clear IRQ flags
        self.clear_irq_status(0xFFFF)
        
        # Write data to FIFO
        if isinstance(data, str):
            data = data.encode()
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        
        self.write_buffer(0, data)
        
        # Set payload length (for variable length, must set explicitly)
        # CRITICAL: Payload length must be set AFTER buffer write and BEFORE SetTx
        if len(data) > 0:
            self._write_register(REG_LR_PAYLOADLENGTH, len(data))
            # Small delay to ensure register write completes
            time.sleep_ms(1)
        
        # Ensure chip is ready before SetTx (wait for any pending register writes)
        self._wait_on_busy()
        
        # Start TX
        self.set_tx(0)  # No timeout
        
        # Note: We do NOT check chip mode here because:
        # 1. TX may complete very quickly (< 30ms for short packets)
        # 2. Chip automatically returns to standby after TX_DONE
        # 3. TX success is determined by TX_DONE IRQ, not chip mode
        # 4. Checking chip mode after SetTx() may show STDBY if TX already completed
        
        # Wait for TX_DONE IRQ
        start = time.ticks_ms()
        poll_count = 0
        while True:
            irq = self.get_irq_status()
            poll_count += 1
            
            if irq & IRQ_TX_DONE:
                # TX successful
                self.clear_irq_status(IRQ_TX_DONE)
                # Return to RC standby for power saving (XOSC was only needed for TX)
                # CRITICAL: After TX_DONE, chip transitions: TX → FS → STDBY
                # FS (Frequency Synthesis) state can take time and BUSY may be HIGH
                # We must wait for this transition to complete before next command
                self.set_standby(STDBY_RC)
                self._wait_on_busy()  # Wait for standby transition to complete
                # Additional delay to ensure chip is fully settled in STDBY
                # This prevents BUSY timeout on next SetTx() if chip is still in FS
                time.sleep_ms(10)  # Allow FS → STDBY transition to complete (increased for reliability)
                # Final BUSY check to ensure chip is fully ready
                self._wait_on_busy()
                return True
            
            if irq & IRQ_RX_TX_TIMEOUT:
                # Hardware timeout - read device errors for debugging
                errors = self.get_device_errors()
                if errors != 0:
                    print(f"[TX] Hardware timeout, device errors: 0x{errors:04X}")
                self.clear_irq_status(IRQ_RX_TX_TIMEOUT)
                # Return to RC standby
                self.set_standby(STDBY_RC)
                return False
            
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                # Software timeout - read device errors and IRQ status for debugging
                errors = self.get_device_errors()
                final_irq = self.get_irq_status()
                print(f"[TX] Software timeout after {poll_count} polls")
                print(f"[TX] Final IRQ status: 0x{final_irq:04X}")
                if errors != 0:
                    print(f"[TX] Device errors: 0x{errors:04X}")
                # Return to RC standby
                self.set_standby(STDBY_RC)
                return False
            
            time.sleep_ms(10)
    
    def receive(self, timeout_ms=5000):
        """
        Receive data packet
        
        Args:
            timeout_ms: Timeout in milliseconds (0 = wait forever)
            
        Returns:
            tuple: (data, rssi, snr) or (None, None, None) on timeout/error
        
        Note: After TCXO configuration, chip may be in STDBY_XOSC mode,
        which is acceptable and actually preferred for RX operations.
        """
        # CRITICAL: Wait for chip to be ready FIRST (wait for any pending operations)
        # This prevents BUSY timeout if chip is still transitioning from previous operation
        self._wait_on_busy()
        
        # Switch to XOSC standby before RX (REQUIRED for stable RX)
        # RC oscillator is not stable enough - XOSC provides stable reference
        self.set_standby(STDBY_XOSC)
        
        # Clear device errors (stale errors can prevent command execution)
        self.clear_device_errors()
        
        # Clear IRQ flags
        self.clear_irq_status(0xFFFF)
        
        # Start RX
        if timeout_ms == 0:
            self.set_rx(0xFFFFFF)  # Continuous RX
        else:
            # Convert timeout to symbols (approximate)
            # Symbol time = (2^SF) / BW
            # For SF7, BW125: symbol_time = 128/125000 = 1.024ms
            # Use a safe timeout value
            timeout_sym = 0xFFFFFF  # Use continuous for now
            self.set_rx(timeout_sym)
        
        # Wait for RX_DONE IRQ
        start = time.ticks_ms()
        while True:
            irq = self.get_irq_status()
            if irq & IRQ_RX_DONE:
                # Get buffer status
                payload_len, rx_start = self.get_rx_buffer_status()
                
                # Read payload
                if payload_len > 0:
                    data = self.read_buffer(rx_start, payload_len)
                else:
                    data = None
                
                # Get packet status (RSSI, SNR)
                rssi_pkt, snr_pkt, _ = self.get_packet_status()
                
                # Convert RSSI (formula from datasheet)
                rssi = -rssi_pkt / 2.0
                snr = snr_pkt / 4.0
                
                # Clear IRQ
                self.clear_irq_status(IRQ_RX_DONE)
                # Return to RC standby for power saving
                # CRITICAL: After RX_DONE, chip transitions: RX → FS → STDBY
                # FS (Frequency Synthesis) state can take time and BUSY may be HIGH
                # We must wait for this transition to complete
                self.set_standby(STDBY_RC)
                self._wait_on_busy()  # Wait for SetStandby command to complete
                # Small delay to allow FS → STDBY transition to complete
                time.sleep_ms(5)  # Allow state transition (reduced from 10ms for faster operation)
                
                return (data, rssi, snr)
            
            if irq & IRQ_CRC_ERROR:
                self.clear_irq_status(IRQ_CRC_ERROR)
                # Return to RC standby
                self.set_standby(STDBY_RC)
                self._wait_on_busy()
                time.sleep_ms(5)  # Allow state transition
                return (None, None, None)
            
            if irq & IRQ_RX_TX_TIMEOUT:
                self.clear_irq_status(IRQ_RX_TX_TIMEOUT)
                # Return to RC standby
                self.set_standby(STDBY_RC)
                self._wait_on_busy()
                time.sleep_ms(5)  # Allow state transition
                return (None, None, None)
            
            if timeout_ms > 0 and time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                # Return to RC standby
                self.set_standby(STDBY_RC)
                self._wait_on_busy()
                time.sleep_ms(5)  # Allow state transition
                return (None, None, None)
            
            time.sleep_ms(10)

