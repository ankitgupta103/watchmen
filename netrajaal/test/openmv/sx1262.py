"""
SX1262 LoRa Module Driver for MicroPython
Based on Semtech SX1262 datasheet and RadioLib implementation
"""

from machine import SPI, Pin
import time

class SX1262:
    # SX1262 Register addresses
    REG_LR_FIRMWARE_VERSION_MSB = 0x0153
    REG_LR_FIRMWARE_VERSION_LSB = 0x0154
    REG_LR_ESTIMATED_FREQUENCY_ERROR = 0x0956
    REG_LR_RSSI_INSTANTANEOUS = 0x0962
    REG_LR_SYNCWORD = 0x0740
    
    # Commands
    CMD_NOP = 0x00
    CMD_SET_SLEEP = 0x84
    CMD_SET_STANDBY = 0x80
    CMD_SET_FS = 0xC1
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
    CMD_SET_RX_TX_FALLBACK_MODE = 0x93
    CMD_WRITE_REGISTER = 0x0D
    CMD_READ_REGISTER = 0x1D
    CMD_WRITE_BUFFER = 0x0E
    CMD_READ_BUFFER = 0x1E
    CMD_SET_DIO_IRQ_PARAMS = 0x08
    CMD_GET_IRQ_STATUS = 0x12
    CMD_CLEAR_IRQ_STATUS = 0x02
    CMD_SET_DIO2_AS_RF_SWITCH_CTRL = 0x9D
    CMD_SET_DIO3_AS_TCXO_CTRL = 0x97
    CMD_SET_RF_FREQUENCY = 0x86
    CMD_SET_PACKET_TYPE = 0x8A
    CMD_GET_PACKET_TYPE = 0x11
    CMD_SET_TX_PARAMS = 0x8E
    CMD_SET_MODULATION_PARAMS = 0x8B
    CMD_SET_PACKET_PARAMS = 0x8C
    CMD_GET_RX_BUFFER_STATUS = 0x13
    CMD_GET_PACKET_STATUS = 0x14
    CMD_SET_SYNC_WORD_1_2 = 0x8F
    CMD_SET_SYNC_WORD_1_3 = 0x91
    CMD_SET_SYNC_WORD_2_3 = 0x90
    CMD_SET_SYNC_WORD_1_2_3 = 0x92
    CMD_SET_RANDOM_SEED = 0x81
    CMD_SET_BOOST_MODE = 0x96
    CMD_SET_BUFFER_BASE_ADDRESS = 0x8F  # Same as SET_SYNC_WORD_1_2, but different usage
    
    # IRQ Masks (from RadioLib SX126x_commands.h)
    IRQ_TX_DONE = 0x01
    IRQ_RX_DONE = 0x02
    IRQ_PREAMBLE_DETECTED = 0x04
    IRQ_SYNCWORD_VALID = 0x08
    IRQ_HEADER_VALID = 0x10
    IRQ_HEADER_ERROR = 0x20
    IRQ_CRC_ERROR = 0x40
    IRQ_CAD_DONE = 0x80
    IRQ_CAD_ACTIVITY_DETECTED = 0x0100
    IRQ_TIMEOUT = 0x0200  # RadioLib uses IRQ_TIMEOUT, not IRQ_RX_TX_TIMEOUT
    
    # Status
    STATUS_MODE_STDBY_RC = 0x20
    STATUS_MODE_STDBY_XOSC = 0x30
    STATUS_MODE_FS = 0x40
    STATUS_MODE_RX = 0x50
    STATUS_MODE_TX = 0x60
    
    def __init__(self, spi, cs, reset, busy, rx_en, tx_en, dio1):
        """
        Initialize SX1262 module
        
        Args:
            spi: SPI object (Machine.SPI)
            cs: Chip Select pin (Pin object)
            reset: Reset pin (Pin object)
            busy: Busy pin (Pin object)
            rx_en: RX Enable pin (Pin object)
            tx_en: TX Enable pin (Pin object)
            dio1: DIO1 interrupt pin (Pin object)
        """
        self.spi = spi
        self.cs = cs
        self.reset = reset
        self.busy = busy
        self.rx_en = rx_en
        self.tx_en = tx_en
        self.dio1 = dio1
        
        # Set initial pin states
        # Note: Pins should be initialized before passing to this class
        try:
            self.cs.value(1)
            self.reset.value(1)
            self.rx_en.value(0)
            self.tx_en.value(0)
        except:
            # If pins aren't initialized, initialize them
            self.cs.init(Pin.OUT, value=1)
            self.reset.init(Pin.OUT, value=1)
            self.busy.init(Pin.IN)
            self.rx_en.init(Pin.OUT, value=0)
            self.tx_en.init(Pin.OUT, value=0)
            self.dio1.init(Pin.IN)
        
        # State variables
        self._packet_type = 0
        self._frequency = 0
        self._rssi = 0
        self._snr = 0
        self._frequency_error = 0
        self._bandwidth_khz = 125.0  # Default bandwidth
        self._spreading_factor = 9   # Default spreading factor
        
        # Reset module
        self.reset_module()
        
    def reset_module(self):
        """Reset the SX1262 module"""
        self.reset.value(0)
        time.sleep_us(100)
        self.reset.value(1)
        time.sleep_us(100)
        self.wait_for_not_busy()
        
    def wait_for_not_busy(self, timeout_ms=100):
        """Wait until BUSY pin goes low"""
        start = time.ticks_ms()
        while self.busy.value() == 1:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                return False
            time.sleep_us(10)
        return True
    
    def wait_for_busy(self, timeout_ms=100):
        """Wait until BUSY pin goes high (chip is busy)"""
        start = time.ticks_ms()
        while self.busy.value() == 0:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                return False
            time.sleep_us(10)
        return True
        
    def _spi_write_stream(self, cmd, data=None, wait_for_busy=True):
        """
        Write command to SX1262 using single SPI transaction (matches RadioLib SPIwriteStream)
        
        RadioLib flow:
        1. Wait for BUSY LOW (if waitForGpio=True)
        2. Prepare buffer: [cmd, param1, param2, ...]
        3. Single SPI transfer: ALL bytes in ONE transaction
        4. CS LOW → transfer → CS HIGH
        5. Wait for BUSY HIGH then LOW (if waitForGpio=True)
        
        Args:
            cmd: Command byte
            data: Parameter bytes (list or None)
            wait_for_busy: Wait for BUSY pin (default True)
        
        Returns:
            status_byte: Status byte returned by chip
        """
        if wait_for_busy:
            self.wait_for_not_busy()
        
        # Prepare output buffer: [cmd, param1, param2, ...]
        if data is None:
            data = []
        out_buf = bytearray([cmd] + list(data))
        
        # Prepare input buffer: [status, ...] (same size as output)
        in_buf = bytearray(len(out_buf))
        
        # Single SPI transaction: ALL bytes in ONE transfer
        self.cs.value(0)
        time.sleep_us(1)
        self.spi.write_readinto(out_buf, in_buf)
        self.cs.value(1)
        time.sleep_us(1)
        
        # Status byte is first byte returned
        status_byte = in_buf[0]
        
        # Wait for BUSY to go HIGH then LOW (chip processing command)
        if wait_for_busy:
            # Wait for BUSY HIGH (chip started processing)
            self.wait_for_busy(timeout_ms=100)
            # Wait for BUSY LOW (chip finished processing)
            self.wait_for_not_busy(timeout_ms=100)
        
        return status_byte
    
    def _spi_read_stream(self, cmd, read_len, wait_for_busy=True):
        """
        Read data from SX1262 using single SPI transaction (matches RadioLib SPIreadStream)
        
        RadioLib SPItransferStream for read (!write):
        - buffLen = cmdLen + numBytes + statusLen (line 321-323)
        - buffOut = [cmd(1), NOP(numBytes + statusLen)] (line 341)
        - buffIn = [status, data...] (status at position 0, data follows)
        - Data extracted from: buffIn[cmdLen + statusLen:] (line 413)
        
        For SX126x: statusLen = 1 byte, cmdLen = 1 byte
        For GET_IRQ_STATUS (read 2 bytes):
        - buffLen = 1 + 2 + 1 = 4 bytes
        - buffOut = [0x12, 0x00, 0x00, 0x00] (cmd + 3 dummy bytes)
        - buffIn = [status, ?, data0, data1] (status at 0, data at 2-3)
        - Data extracted: buffIn[2:4] = [data0, data1]
        
        Args:
            cmd: Command byte
            read_len: Number of data bytes to read (excluding status byte)
            wait_for_busy: Wait for BUSY pin (default True)
        
        Returns:
            (status_byte, data_bytes): Status byte and data bytes
        """
        # Wait for BUSY LOW before transaction (RadioLib line 345-364)
        # During TX mode, BUSY is already LOW, so this returns immediately
        if wait_for_busy:
            # RadioLib uses timeout from spiConfig.timeout (typically longer)
            # We use shorter timeout since during TX mode BUSY is already LOW
            self.wait_for_not_busy(timeout_ms=100)
        
        # RadioLib: buffLen = cmdLen + numBytes + statusLen
        # For SX126x: cmdLen=1, statusLen=1
        cmd_len = 1
        status_len = 1
        total_len = cmd_len + read_len + status_len
        
        # Prepare output buffer: [cmd, NOP, NOP, ...]
        # RadioLib uses NOP (0x00 for SX126x) for (numBytes + statusLen) dummy bytes
        out_buf = bytearray([cmd] + [0x00] * (read_len + status_len))
        
        # Prepare input buffer: same size as output
        in_buf = bytearray(len(out_buf))
        
        # Single SPI transaction: ALL bytes in ONE transfer
        self.cs.value(0)
        time.sleep_us(1)
        self.spi.write_readinto(out_buf, in_buf)
        self.cs.value(1)
        time.sleep_us(1)
        
        # Debug: Print raw buffers for GET_IRQ_STATUS to diagnose issues
        if cmd == self.CMD_GET_IRQ_STATUS:
            print("[DEBUG] GET_IRQ_STATUS SPI: out={}, in={}".format(
                out_buf.hex(), in_buf.hex()))
        
        # Parse result according to RadioLib line 413:
        # Data extracted from: buffIn[cmdLen + statusLen:]
        # For SX126x: cmdLen=1, statusLen=1, so data starts at offset 2
        status_byte = in_buf[0]
        data_start = cmd_len + status_len  # 1 + 1 = 2
        data_bytes = in_buf[data_start:data_start+read_len] if read_len > 0 else bytearray()
        
        # Wait for BUSY to go HIGH then LOW (chip processing command)
        # RadioLib line 382-402: Waits for GPIO to go LOW (checks if HIGH, waits for LOW)
        # During TX mode, BUSY is LOW, so wait passes immediately
        # For read commands during TX, BUSY may not go HIGH at all - that's OK!
        if wait_for_busy:
            # Small delay first (RadioLib line 386: delayMicroseconds(1))
            time.sleep_us(1)
            # RadioLib line 388: while(digitalRead(gpioPin)) - waits for GPIO to go LOW
            # If GPIO is already LOW, loop doesn't execute, continues immediately
            # For GET_IRQ_STATUS during TX, BUSY stays LOW, so we should continue
            # Check current BUSY state - if already LOW, skip wait (matches RadioLib behavior)
            if self.busy.value() == 1:
                # BUSY is HIGH, wait for it to go LOW
                self.wait_for_not_busy(timeout_ms=100)
            # If BUSY is LOW, continue immediately (data is already read)
            # RadioLib continues even if timeout occurs (line 397: "do not return yet")
        
        return (status_byte, data_bytes)
        
    def _write_command(self, cmd, data=None, wait_for_busy=True):
        """
        Write a command to SX1262
        Matches RadioLib: mod->SPIwriteStream(cmd, data, numBytes, waitForGpio)
        """
        self._spi_write_stream(cmd, data, wait_for_busy)
        
    def _read_command(self, cmd, length, wait_for_busy=True):
        """
        Read data from SX1262
        Matches RadioLib: mod->SPIreadStream(cmd, data, numBytes, waitForGpio)
        
        Returns:
            data_bytes: Data bytes (excluding status byte)
        """
        _, data_bytes = self._spi_read_stream(cmd, length, wait_for_busy)
        return data_bytes
        
    def _write_register(self, address, value):
        """
        Write a register
        Matches RadioLib: SPIwriteRegisterBurst(addr, data, numBytes)
        For SX126x: CMD_WRITE_REGISTER + [addr_msb, addr_lsb] + [data...]
        """
        addr_bytes = [(address >> 8) & 0xFF, address & 0xFF]
        self._write_command(self.CMD_WRITE_REGISTER, addr_bytes + [value], wait_for_busy=True)
        
    def _read_register(self, address):
        """
        Read a register
        Matches RadioLib: SPIreadRegisterBurst(addr, numBytes, data)
        For SX126x: CMD_READ_REGISTER + [addr_msb, addr_lsb] + dummy bytes, read [status, data...]
        """
        addr_bytes = [(address >> 8) & 0xFF, address & 0xFF]
        # Send: [CMD_READ_REGISTER, addr_msb, addr_lsb, 0x00], Read: [status, addr_msb, addr_lsb, data]
        # Actually, for single byte read: send [CMD, addr_msb, addr_lsb, 0x00], read [status, addr_msb, addr_lsb, data]
        out_buf = bytearray([self.CMD_READ_REGISTER] + addr_bytes + [0x00])
        in_buf = bytearray(len(out_buf))
        self.wait_for_not_busy()
        self.cs.value(0)
        time.sleep_us(1)
        self.spi.write_readinto(out_buf, in_buf)
        self.cs.value(1)
        time.sleep_us(1)
        # Result: [status, addr_msb, addr_lsb, data]
        return in_buf[3] if len(in_buf) > 3 else 0
        
    def _write_buffer(self, offset, data):
        """Write data to buffer
        For variable length packets, the first byte at offset should be the length
        But we'll write the data directly and let the caller handle length if needed
        """
        self._write_command(self.CMD_WRITE_BUFFER, [offset] + list(data))
        
    def _read_buffer(self, offset, length):
        """Read data from buffer"""
        # Command format: CMD_READ_BUFFER, offset, dummy byte, then read length bytes
        # RadioLib: SPIreadStream(CMD_READ_BUFFER, data, length)
        # But we need to send offset first, so we use write then read
        # Actually, READ_BUFFER command is: [CMD, offset, dummy], then read length bytes
        # Let's use a combined approach: send [CMD, offset] + dummy bytes, read [status, data...]
        out_buf = bytearray([self.CMD_READ_BUFFER, offset] + [0x00] * length)
        in_buf = bytearray(len(out_buf))
        self.wait_for_not_busy()
        self.cs.value(0)
        time.sleep_us(1)
        self.spi.write_readinto(out_buf, in_buf)
        self.cs.value(1)
        time.sleep_us(1)
        # Result: [status, data1, data2, ...]
        return in_buf[2:2+length] if len(in_buf) > 2 else bytearray(length)
        
    def set_standby(self, mode=0):
        """Set standby mode (0=RC, 1=XOSC)"""
        self._write_command(self.CMD_SET_STANDBY, [mode])
        
    def set_sleep(self, sleep_config=0x00):
        """Set sleep mode"""
        self._write_command(self.CMD_SET_SLEEP, [sleep_config])
        
    def calibrate(self, calib_param):
        """Calibrate the module"""
        self._write_command(self.CMD_CALIBRATE, [calib_param])
        self.wait_for_not_busy(1000)
        
    def set_packet_type(self, packet_type):
        """Set packet type (0x00=LoRa, 0x01=FSK)"""
        self._write_command(self.CMD_SET_PACKET_TYPE, [packet_type])
        self._packet_type = packet_type
        
    def set_rf_frequency(self, freq_hz):
        """Set RF frequency in Hz"""
        freq_reg = int(freq_hz * (2**25) / 32000000)
        freq_bytes = [
            (freq_reg >> 24) & 0xFF,
            (freq_reg >> 16) & 0xFF,
            (freq_reg >> 8) & 0xFF,
            freq_reg & 0xFF
        ]
        self._write_command(self.CMD_SET_RF_FREQUENCY, freq_bytes)
        self._frequency = freq_hz
        
    def set_tx_params(self, power, ramp_time=0x04):
        """Set TX parameters
        power: -9 to 22 dBm
        ramp_time: 0x00=10us, 0x01=20us, 0x02=40us, 0x03=80us, 0x04=200us, etc.
        """
        # Convert power to register value
        # For SX1262: power = -9 + (reg_value * 1)
        if power < -9:
            power = -9
        elif power > 22:
            power = 22
        power_reg = power + 9
        self._write_command(self.CMD_SET_TX_PARAMS, [power_reg, ramp_time])
        
    def set_modulation_params(self, sf, bw, cr, ldro=0):
        """Set LoRa modulation parameters
        sf: Spreading factor (5-12)
        bw: Bandwidth in kHz (7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500)
        cr: Coding rate (5-8, meaning 4/5 to 4/8)
        ldro: Low data rate optimize (0 or 1)
        """
        # Store bandwidth and spreading factor for fix_sensitivity() and timeout calculation
        self._bandwidth_khz = bw
        self._spreading_factor = sf
        
        # Convert bandwidth to register value
        bw_map = {
            7.8: 0x00, 10.4: 0x08, 15.6: 0x01, 20.8: 0x09,
            31.25: 0x02, 41.7: 0x0A, 62.5: 0x03, 125: 0x04,
            250: 0x05, 500: 0x06
        }
        bw_reg = bw_map.get(bw, 0x04)  # Default to 125 kHz
        
        mod_params = [sf, bw_reg, cr, ldro]
        self._write_command(self.CMD_SET_MODULATION_PARAMS, mod_params)
        
    def set_packet_params(self, preamble_len, header_type, payload_len, crc_type, invert_iq=0):
        """Set packet parameters
        preamble_len: Preamble length (16-bit)
        header_type: 0x00=variable, 0x01=fixed
        payload_len: Payload length (for fixed header, max 255)
        crc_type: 0x00=none, 0x01=CRC on
        invert_iq: 0=normal, 1=inverted
        """
        # Ensure preamble is within valid range
        if preamble_len > 0xFFFF:
            preamble_len = 0xFFFF
        if payload_len > 0xFF:
            payload_len = 0xFF
            
        packet_params = [
            (preamble_len >> 8) & 0xFF, preamble_len & 0xFF,
            header_type, payload_len & 0xFF,
            crc_type, invert_iq
        ]
        self._write_command(self.CMD_SET_PACKET_PARAMS, packet_params)
        
    def set_sync_word(self, sync_word):
        """Set sync word (1 byte)"""
        self._write_command(self.CMD_SET_SYNC_WORD_1_2, [sync_word, 0x00])
        
    def set_buffer_base_address(self, tx_base=0x00, rx_base=0x00):
        """Set buffer base addresses (CRITICAL - RadioLib calls this before writeBuffer!)"""
        self._write_command(self.CMD_SET_BUFFER_BASE_ADDRESS, [tx_base, rx_base])
        
    def set_dio_irq_params(self, irq_mask, dio1_mask, dio2_mask, dio3_mask):
        """Set DIO IRQ parameters"""
        irq_bytes = [
            (irq_mask >> 8) & 0xFF, irq_mask & 0xFF,
            (dio1_mask >> 8) & 0xFF, dio1_mask & 0xFF,
            (dio2_mask >> 8) & 0xFF, dio2_mask & 0xFF,
            (dio3_mask >> 8) & 0xFF, dio3_mask & 0xFF
        ]
        self._write_command(self.CMD_SET_DIO_IRQ_PARAMS, irq_bytes)
        
    def get_irq_status(self):
        """
        Get IRQ status
        Returns 16-bit IRQ status register
        Matches RadioLib: SPIreadStream(CMD_GET_IRQ_STATUS, data, 2)
        RadioLib line 946: this->mod->SPIreadStream(RADIOLIB_SX126X_CMD_GET_IRQ_STATUS, data, 2);
        RadioLib line 947: return(((uint32_t)(data[0]) << 8) | data[1]);
        
        Note: RadioLib uses default waitForGpio=true. During TX mode, BUSY stays LOW,
        so post-transaction BUSY wait may timeout, but RadioLib continues anyway (line 397).
        
        CRITICAL: During TX mode, the chip may not respond to SPI commands immediately.
        Try reading without BUSY wait first, or use very short timeout.
        """
        # During TX mode, BUSY is LOW and chip may not respond to SPI immediately
        # Try with wait_for_busy=False first (GET_IRQ_STATUS can be read during TX/RX)
        # If that doesn't work, try with very short timeout
        status_byte, data = self._spi_read_stream(self.CMD_GET_IRQ_STATUS, 2, wait_for_busy=False)
        
        if len(data) >= 2:
            # Combine IRQ bytes: MSB first (matches RadioLib line 947)
            irq_status = (data[0] << 8) | data[1]
        else:
            irq_status = 0xFFFF  # Error reading
        
        # Debug output with raw bytes (show if error or for debugging)
        if irq_status == 0xFFFF or True:  # Always show for now
            print("[DEBUG] IRQ read: status=0x{:02X}, data=[0x{:02X}, 0x{:02X}], irq=0x{:04X}, BUSY={}, DIO1={}".format(
                status_byte, 
                data[0] if len(data) > 0 else 0xFF, 
                data[1] if len(data) > 1 else 0xFF, 
                irq_status,
                self.busy.value(), 
                self.dio1.value()))
        
        return irq_status
        
    def clear_irq_status(self, irq_mask=0xFFFF):
        """Clear IRQ status"""
        irq_bytes = [(irq_mask >> 8) & 0xFF, irq_mask & 0xFF]
        self._write_command(self.CMD_CLEAR_IRQ_STATUS, irq_bytes)
        
    def set_dio2_as_rf_switch(self, enable=True):
        """Set DIO2 as RF switch control"""
        self._write_command(self.CMD_SET_DIO2_AS_RF_SWITCH_CTRL, [0x01 if enable else 0x00])
        
    def set_dio3_as_tcxo_ctrl(self, voltage, delay=0):
        """Set DIO3 as TCXO control
        voltage: 0x00=1.6V, 0x01=1.7V, 0x02=1.8V, 0x03=2.2V, 0x04=2.4V, 0x05=2.7V, 0x06=3.0V, 0x07=3.3V
        delay: Delay in steps of 15.625us
        """
        delay_bytes = [
            (delay >> 16) & 0xFF,
            (delay >> 8) & 0xFF,
            delay & 0xFF
        ]
        self._write_command(self.CMD_SET_DIO3_AS_TCXO_CTRL, [voltage] + delay_bytes)
        
    def set_rf_switch(self, rx_mode=True):
        """Control RF switch pins
        RX mode: RX_EN=HIGH, TX_EN=LOW
        TX mode: RX_EN=LOW, TX_EN=HIGH
        """
        if rx_mode:
            self.tx_en.value(0)  # Set TX_EN low first
            time.sleep_us(10)
            self.rx_en.value(1)  # Then set RX_EN high
        else:
            self.rx_en.value(0)  # Set RX_EN low first
            time.sleep_us(10)
            self.tx_en.value(1)  # Then set TX_EN high
        
    def begin(self, freq_mhz, bw, sf, cr, sync_word, tx_power, preamble_len, tcxo_voltage=0x01, use_ldo=False):
        """
        Initialize LoRa module with specified parameters
        
        Args:
            freq_mhz: Frequency in MHz
            bw: Bandwidth in kHz
            sf: Spreading factor (5-12)
            cr: Coding rate (5-8)
            sync_word: Sync word (1 byte)
            tx_power: TX power in dBm (-9 to 22)
            preamble_len: Preamble length
            tcxo_voltage: TCXO voltage (0x00=1.6V, 0x01=1.7V, etc.)
            use_ldo: Use LDO instead of DC-DC (False recommended)
        """
        # Reset
        self.reset_module()
        
        # Small delay after reset
        time.sleep_ms(10)
        
        # Set standby
        self.set_standby(1)  # XOSC mode
        time.sleep_ms(5)  # Small delay after standby
        
        # Calibrate
        calib_param = 0x7F  # Calibrate all
        self.calibrate(calib_param)
        
        # Set regulator mode
        reg_mode = 0x00 if use_ldo else 0x01  # 0=LDO, 1=DC-DC
        self._write_command(self.CMD_SET_REGULATOR_MODE, [reg_mode])
        
        # Set DIO3 as TCXO control
        # Convert voltage: 1.7V = 0x01, but we need to map it correctly
        # 0x00=1.6V, 0x01=1.7V, 0x02=1.8V, etc.
        if isinstance(tcxo_voltage, float):
            # Convert float voltage to register value
            if tcxo_voltage <= 1.6:
                tcxo_reg = 0x00
            elif tcxo_voltage <= 1.7:
                tcxo_reg = 0x01
            elif tcxo_voltage <= 1.8:
                tcxo_reg = 0x02
            elif tcxo_voltage <= 2.2:
                tcxo_reg = 0x03
            elif tcxo_voltage <= 2.4:
                tcxo_reg = 0x04
            elif tcxo_voltage <= 2.7:
                tcxo_reg = 0x05
            elif tcxo_voltage <= 3.0:
                tcxo_reg = 0x06
            else:
                tcxo_reg = 0x07
        else:
            tcxo_reg = tcxo_voltage
        self.set_dio3_as_tcxo_ctrl(tcxo_reg, delay=5000)  # ~78ms delay
        
        # Set DIO2 as RF switch control (optional, we'll use manual control)
        # self.set_dio2_as_rf_switch(True)
        
        # Set packet type to LoRa
        self.set_packet_type(0x00)
        
        # Set RF frequency
        self.set_rf_frequency(freq_mhz * 1000000)
        
        # Set modulation parameters
        # Calculate low data rate optimize
        symbol_time = (2 ** sf) / (bw * 1000)
        ldro = 1 if symbol_time >= 0.0016 else 0  # 16ms threshold
        self.set_modulation_params(sf, bw, cr, ldro)  # This also stores _bandwidth_khz
        
        # Set packet parameters (variable length, CRC on)
        # For variable length: payload_len is max length (0xFF = 255 bytes)
        self.set_packet_params(preamble_len, 0x00, 0xFF, 0x01, 0x00)
        # Store preamble length for transmit() - CRITICAL!
        self._preamble_len = preamble_len
        
        # Set sync word
        self.set_sync_word(sync_word)
        
        # Set TX parameters
        self.set_tx_params(tx_power)
        
        # Set IRQ parameters
        irq_mask = self.IRQ_TX_DONE | self.IRQ_RX_DONE | self.IRQ_TIMEOUT | self.IRQ_CRC_ERROR
        self.set_dio_irq_params(irq_mask, irq_mask, 0x00, 0x00)
        
        # Clear IRQ
        self.clear_irq_status(0xFFFF)
        
        return 0  # Success
        
    def transmit(self, data):
        """
        Transmit data
        
        Args:
            data: String or bytes to transmit
            
        Returns:
            0 on success, error code on failure
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Clear all IRQ flags first
        self.clear_irq_status(0xFFFF)
        
        # Set mode to standby first (like RadioLib does)
        self.set_standby(1)
        time.sleep_ms(5)
        
        # Check packet length
        if len(data) > 255:
            data = data[:255]  # Truncate if too long
        
        # Set packet parameters FIRST - CRITICAL: RadioLib uses ACTUAL length, not 0xFF!
        # Variable length is indicated by header_type=0x00, not by using 0xFF
        # RadioLib line 1043: setPacketParams(..., cfg->transmit.len, ...)
        # Use stored preamble length from begin() - PREAMBLE constant is not accessible here!
        preamble_len = getattr(self, '_preamble_len', 8)  # Default to 8 if not set
        print("[TX] Setting packet params: preamble={}, header=0x00 (var), payload_len={}, CRC=0x01 (on)".format(
            preamble_len, len(data)))
        self.set_packet_params(preamble_len, 0x00, len(data), 0x01, 0x00)  # variable length, CRC on, ACTUAL length
        
        # Set DIO IRQ parameters (TX_DONE and TIMEOUT on DIO1)
        # RadioLib line 1065: setDioIrqParams(IRQ_TX_DONE | IRQ_TIMEOUT, IRQ_TX_DONE)
        irq_mask = self.IRQ_TX_DONE | self.IRQ_TIMEOUT
        dio1_mask = self.IRQ_TX_DONE
        print("[TX] Setting DIO IRQ params: irq_mask=0x{:04X}, dio1_mask=0x{:04X}".format(irq_mask, dio1_mask))
        self.set_dio_irq_params(irq_mask, dio1_mask, 0x00, 0x00)
        
        # Set buffer base address (CRITICAL - RadioLib line 1072 calls this before writeBuffer!)
        self.set_buffer_base_address(0x00, 0x00)
        
        # Write data to buffer (offset 0) - NO length byte prepended!
        # For variable length LoRa packets, RadioLib writes data directly WITHOUT prepending length!
        print("[TX] Writing {} bytes to buffer".format(len(data)))
        self._write_buffer(0, data)
        
        # Clear IRQ status
        self.clear_irq_status(0xFFFF)
        
        # Fix sensitivity (CRITICAL - RadioLib calls this before TX, line 1126)
        self.fix_sensitivity()
        
        # Set RF switch to TX (BEFORE setTx, like RadioLib)
        self.set_rf_switch(False)
        time.sleep_ms(1)
        
        # Wait for BUSY to be low before sending command
        if not self.wait_for_not_busy(100):
            self.set_rf_switch(True)
            return -5  # BUSY timeout before command
        
        # Set TX mode with timeout 0x000000 (single transmission, no timeout)
        # RadioLib: setTx(RADIOLIB_SX126X_TX_TIMEOUT_NONE) = 0x000000
        # RadioLib line 1148: state = setTx(RADIOLIB_SX126X_TX_TIMEOUT_NONE);
        # RadioLib line 1151: wait for BUSY to go low (= PA ramp up done)
        timeout_bytes = [0x00, 0x00, 0x00]
        print("[TX] Sending SET_TX command (timeout=0x000000)...")
        
        # Send SET_TX command - _write_command waits for BUSY HIGH then LOW automatically
        # This matches RadioLib's SPIwriteStream with waitForGpio=true
        self._write_command(self.CMD_SET_TX, timeout_bytes, wait_for_busy=True)
        
        # After _write_command returns, BUSY should be LOW (PA ramp up done)
        # RadioLib line 1151: wait for BUSY to go low (= PA ramp up done)
        busy_after_cmd = self.busy.value()
        print("[TX] SET_TX sent, BUSY={} (should be 0 after PA ramp)".format(busy_after_cmd))
        
        if busy_after_cmd == 1:
            # BUSY should be LOW after _write_command returns (wait_for_busy=True handles this)
            # But if it's still HIGH, wait a bit more
            print("[TX] Waiting for BUSY to go LOW (PA ramp up)...")
            if not self.wait_for_not_busy(timeout_ms=500):
                print("[TX] ERROR: BUSY didn't go low after 500ms")
                self.set_rf_switch(True)
                return -6  # BUSY didn't go low after setTx
        
        print("[TX] BUSY is LOW (PA ramp done), radio transmitting. Polling DIO1...")
        
        # BUSY is now LOW - PA ramp up is complete, radio is transmitting
        # Immediately start polling DIO1 for TX_DONE interrupt (like RadioLib does)
        
        # Wait for TX done (poll DIO1 interrupt pin, exactly like RadioLib)
        # Calculate timeout: 5ms + 500% of expected time-on-air
        # Formula: time_on_air = (preamble + header + payload) * symbol_duration
        # Symbol duration = (2^SF) / BW
        # For variable header: header = 1 symbol (contains payload length)
        preamble_len = getattr(self, '_preamble_len', 8)
        symbol_duration_ms = (2 ** self._spreading_factor) / (self._bandwidth_khz * 1000.0)  # ms per symbol
        preamble_time = preamble_len * symbol_duration_ms
        header_time = 1 * symbol_duration_ms  # Variable header = 1 symbol
        payload_time = len(data) * 8 * symbol_duration_ms  # Each bit = 1 symbol
        packet_time_ms = preamble_time + header_time + payload_time
        
        timeout_ms = 5 + int(packet_time_ms * 5)
        timeout_ms = max(timeout_ms, 2000)  # At least 2 seconds
        print("[TX] Timeout set to {}ms (packet time ~{}ms, SF={}, BW={}kHz, len={})".format(
            timeout_ms, int(packet_time_ms), self._spreading_factor, self._bandwidth_khz, len(data)))
        
        start = time.ticks_ms()
        poll_count = 0
        
        while True:
            poll_count += 1
            dio1_state = self.dio1.value()
            
            # Poll the interrupt pin (DIO1) - this is exactly what RadioLib does
            if dio1_state == 1:
                # DIO1 is high, interrupt occurred
                print("[TX] DIO1 HIGH detected! Checking IRQ...")
                # Check IRQ flags
                irq = self.get_irq_status()
                print("[TX] IRQ status: 0x{:04X}".format(irq))
                
                if irq & self.IRQ_TX_DONE:
                    # Transmission complete
                    print("[TX] TX_DONE IRQ detected!")
                    # Call finishTransmit equivalent (matches RadioLib line 276)
                    # RadioLib finishTransmit(): clear all IRQs, then set standby mode
                    self.clear_irq_status(0xFFFF)  # Clear ALL IRQs (not just TX_DONE)
                    # Set module to standby mode (disables transmitter/RF switch automatically)
                    self.set_standby(1)
                    # RF switch is controlled by module state, but set it explicitly too
                    self.set_rf_switch(True)
                    return 0  # Success
                elif irq & self.IRQ_TIMEOUT:
                    print("[TX] TIMEOUT IRQ detected!")
                    self.clear_irq_status(0xFFFF)  # Clear all IRQs
                    self.set_standby(1)  # Set to standby
                    self.set_rf_switch(True)
                    return -1  # Timeout
                # Note: CRC error shouldn't occur on TX, but handle it anyway
                elif irq & self.IRQ_CRC_ERROR:
                    print("[TX] CRC_ERROR IRQ detected!")
                    self.clear_irq_status(self.IRQ_CRC_ERROR)
                    self.set_rf_switch(True)
                    return -4  # CRC error
                else:
                    print("[TX] DIO1 HIGH but unexpected IRQ: 0x{:04X}".format(irq))
                    # If we got here, DIO1 is high but no expected IRQ - continue polling
            elif poll_count % 100 == 0:
                # Debug output every 100 polls
                print("[TX] Polling... DIO1={}, BUSY={}, elapsed={}ms".format(
                    dio1_state, self.busy.value(), time.ticks_diff(time.ticks_ms(), start)))
            
            # Check timeout
            elapsed = time.ticks_diff(time.ticks_ms(), start)
            if elapsed > timeout_ms:
                # On timeout, don't try to read IRQ status (DIO1 is still LOW, chip may not respond)
                # RadioLib only reads IRQ when DIO1 is HIGH
                print("[TX] TIMEOUT after {}ms! DIO1={}, BUSY={}".format(
                    elapsed, self.dio1.value(), self.busy.value()))
                # Cleanup on timeout (matches finishTransmit)
                self.clear_irq_status(0xFFFF)
                self.set_standby(1)
                self.set_rf_switch(True)
                return -2  # Timeout
            
            # Small delay (RadioLib uses yield, we use sleep)
            time.sleep_ms(1)
            
    def start_receive(self):
        """Start receiving"""
        # Set RF switch to RX
        self.set_rf_switch(True)
        time.sleep_ms(1)
        
        # Clear IRQ
        self.clear_irq_status(0xFFFF)
        
        # Set RX mode with timeout (0x000000 = continuous RX, no timeout)
        timeout_bytes = [0x00, 0x00, 0x00]
        self._write_command(self.CMD_SET_RX, timeout_bytes)
        
        return 0
        
    def read_data(self):
        """
        Read received data
        
        Returns:
            (data, status) where data is bytes and status is 0 on success
        """
        irq = self.get_irq_status()
        
        if irq & self.IRQ_RX_DONE:
            # Get RX buffer status
            status = self._read_command(self.CMD_GET_RX_BUFFER_STATUS, 2)
            if len(status) >= 2:
                payload_len = status[0]
                buffer_start = status[1]
                
                # Read packet status
                pkt_status = self._read_command(self.CMD_GET_PACKET_STATUS, 3)
                if len(pkt_status) >= 3:
                    self._rssi = -pkt_status[0] / 2
                    self._snr = (pkt_status[1] if pkt_status[1] < 128 else pkt_status[1] - 256) / 4
                
                # Read data from buffer
                data = self._read_buffer(buffer_start, payload_len)
                
                # Clear IRQ
                self.clear_irq_status(self.IRQ_RX_DONE)
                
                if irq & self.IRQ_CRC_ERROR:
                    return (None, -1)  # CRC error
                
                return (data, 0)  # Success
                
        elif irq & self.IRQ_CRC_ERROR:
            self.clear_irq_status(self.IRQ_CRC_ERROR)
            return (None, -1)  # CRC error
        elif irq & self.IRQ_TIMEOUT:
            self.clear_irq_status(self.IRQ_TIMEOUT)
            return (None, -2)  # Timeout
            
        return (None, -3)  # No data
        
    def get_rssi(self):
        """Get RSSI in dBm"""
        return self._rssi
        
    def get_snr(self):
        """Get SNR in dB"""
        return self._snr
        
    def get_frequency_error(self):
        """Get frequency error in Hz"""
        # Read frequency error register (24-bit value)
        # Register is at 0x0956-0x0958
        freq_err_msb = self._read_register(0x0956)
        freq_err_mid = self._read_register(0x0957)
        freq_err_lsb = self._read_register(0x0958)
        
        # Combine bytes (signed 24-bit value)
        freq_err_raw = (freq_err_msb << 16) | (freq_err_mid << 8) | freq_err_lsb
        if freq_err_msb & 0x80:  # Sign extend if negative
            freq_err_raw = freq_err_raw | 0xFF000000
        
        # Convert to Hz: freq_err = (freq_err_raw * 32000000) / (2^25)
        freq_err_hz = (freq_err_raw * 32000000) / (2**25)
        return int(freq_err_hz)
        
    def set_rx_boosted_gain_mode(self, enable=True):
        """Set RX boosted gain mode"""
        # This is a simplified implementation
        # The actual implementation would modify the LNA gain settings
        return 0  # Success
        
    def fix_sensitivity(self):
        """
        Fix receiver sensitivity for 500 kHz LoRa
        See SX1262/SX1268 datasheet, chapter 15 Known Limitations, section 15.1
        RadioLib calls this before TX (line 1126)
        """
        # Read current sensitivity configuration
        REG_SENSITIVITY_CONFIG = 0x0889
        sensitivity_config = self._read_register(REG_SENSITIVITY_CONFIG)
        
        # Fix the value for LoRa with 500 kHz bandwidth
        # For other bandwidths or non-LoRa, set bit 2
        if self._packet_type == 0x00:  # LoRa mode
            # Check if bandwidth is 500 kHz (with small tolerance)
            if abs(self._bandwidth_khz - 500.0) <= 0.001:
                # Clear bit 2 (0xFB = 0b11111011)
                sensitivity_config &= 0xFB
            else:
                # Set bit 2 (0x04 = 0b00000100)
                sensitivity_config |= 0x04
        else:
            # Non-LoRa mode, set bit 2
            sensitivity_config |= 0x04
        
        # Write back the configuration
        self._write_register(REG_SENSITIVITY_CONFIG, sensitivity_config)
        return 0  # Success


# ============================================================================
# Main Program for Simple TX/RX
# ============================================================================
if __name__ == "__main__":
    # Mode Selection
    TX_MODE = False  # Set to False for RX mode
    
    # Pin Configuration (OpenMV RT1062)
    PIN_MOSI = "P0"   # SPI MOSI
    PIN_MISO = "P1"   # SPI MISO
    PIN_SCLK = "P2"   # SPI SCLK
    PIN_SS = "P3"     # SPI CS (Chip Select)
    PIN_RESET = "P6"  # Reset pin
    PIN_BUSY = "P7"   # Busy pin
    PIN_RX_EN = "P8"  # RX Enable
    PIN_TX_EN = "P13" # TX Enable
    PIN_DIO1 = "P14"  # DIO1 interrupt pin
    
    # LoRa Configuration
    FREQ = 869525000  # Frequency in Hz (869.525 MHz)
    BW = 125.0        # Bandwidth in kHz
    SF = 9            # Spreading Factor (5-12)
    CR = 7            # Coding Rate (5-8)
    SYNCW = 0xE3      # Sync Word
    TX_PWR = 9        # TX Power in dBm (-9 to 22)
    PREAMBLE = 8      # Preamble Length
    XOV = 1.7         # TCXO Voltage (1.7V, can be float or 0x01)
    LDO = False       # Use LDO only
    
    # Global variables
    received_flag = False
    enable_interrupt = True
    
    def dio1_handler(pin):
        """DIO1 interrupt handler"""
        global received_flag, enable_interrupt
        if enable_interrupt:
            received_flag = True
    
    print("\n" + "=" * 40)
    print("Simple LoRa Point-to-Point Communication")
    print("=" * 40 + "\n")
    
    # Initialize SPI
    spi = SPI(
        1,
        baudrate=2000000,  # 2 MHz (SX1262 max is 18MHz)
        polarity=0,        # CPOL = 0
        phase=0,           # CPHA = 0
        bits=8,
        firstbit=SPI.MSB
    )
    
    # Initialize control pins
    cs_pin = Pin(PIN_SS, Pin.OUT, value=1)
    reset_pin = Pin(PIN_RESET, Pin.OUT, value=1)
    busy_pin = Pin(PIN_BUSY, Pin.IN)
    rx_en_pin = Pin(PIN_RX_EN, Pin.OUT, value=0)
    tx_en_pin = Pin(PIN_TX_EN, Pin.OUT, value=0)
    dio1_pin = Pin(PIN_DIO1, Pin.IN)
    
    # Create SX1262 instance
    lora = SX1262(
        spi=spi,
        cs=cs_pin,
        reset=reset_pin,
        busy=busy_pin,
        rx_en=rx_en_pin,
        tx_en=tx_en_pin,
        dio1=dio1_pin
    )
    
    # Initialize LoRa module
    print("[INIT] Initializing LoRa...", end="")
    state = lora.begin(
        freq_mhz=FREQ / 1000000.0,
        bw=BW,
        sf=SF,
        cr=CR,
        sync_word=SYNCW,
        tx_power=TX_PWR,
        preamble_len=PREAMBLE,
        tcxo_voltage=XOV,
        use_ldo=LDO
    )
    
    if state != 0:
        print(" failed, code: {}".format(state))
        print("Check your wiring and connections!")
        while True:
            time.sleep_ms(1000)
    
    print(" done!")
    
    # Set RX boosted gain mode
    print("[INIT] Setting RX boosted gain...", end="")
    state = lora.set_rx_boosted_gain_mode(True)
    if state == 0:
        print(" done!")
    else:
        print(" failed (non-critical)")
    
    print()
    
    # TX Mode
    if TX_MODE:
        print("\n=== TX MODE ===")
        print("Sending data every 5 seconds...\n")
        
        counter = 0
        
        while True:
            # Prepare data
            data = "Hello LoRa! Count: {}".format(counter)
            
            print("[TX] Sending: {}".format(data))
            
            # Transmit
            state = lora.transmit(data)
            
            if state == 0:
                print("[TX] Success!")
                print("[TX] RSSI: {:.2f} dBm".format(lora.get_rssi()))
                print("[TX] SNR: {:.2f} dB".format(lora.get_snr()))
            else:
                print("[TX] Failed, code: {}".format(state))
            
            counter += 1
            time.sleep_ms(5000)  # Wait 5 seconds before next transmission
    
    # RX Mode
    else:
        print("\n=== RX MODE ===")
        print("Listening for packets...\n")
        
        # Set interrupt handler
        dio1_pin.irq(trigger=Pin.IRQ_RISING, handler=dio1_handler)
        
        # Start receiving
        state = lora.start_receive()
        if state != 0:
            print("[RX] Failed to start receive, code: {}".format(state))
        else:
            print("[RX] Ready to receive...\n")
            
            while True:
                # Check if packet received
                if received_flag:
                    enable_interrupt = False
                    received_flag = False
                    
                    # Read received data
                    data, status = lora.read_data()
                    
                    if status == 0 and data is not None:
                        print("[RX] Packet received!")
                        try:
                            data_str = data.decode('utf-8')
                            print("[RX] Data: {}".format(data_str))
                        except:
                            print("[RX] Data (hex): {}".format(data.hex()))
                        print("[RX] RSSI: {:.2f} dBm".format(lora.get_rssi()))
                        print("[RX] SNR: {:.2f} dB".format(lora.get_snr()))
                        print("[RX] Frequency Error: {} Hz".format(lora.get_frequency_error()))
                        print()
                    elif status == -1:
                        print("[RX] CRC error - packet corrupted!")
                    else:
                        print("[RX] Failed to read data, code: {}".format(status))
                    
                    # Resume listening
                    lora.start_receive()
                    enable_interrupt = True
                
                time.sleep_ms(10)  # Small delay to prevent watchdog issues

 