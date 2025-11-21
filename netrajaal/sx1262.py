"""
SX126x LoRa Module Driver for OpenMV RT1062

This module provides a Python driver for the E22/E32 LoRa modules based on the 
Semtech SX126x chipset. It handles configuration, transmission, and reception 
of data over LoRa mesh networks.

Hardware Requirements:
    - OpenMV RT1062 board
    - waveshare sx1262 lora HAT 
    - UART connection (default: UART 1)
    - GPIO pins for M0 and M1 mode control (default: P6, P7)

Features:
    - Automatic configuration mode switching (M0/M1 pins)
    - Configurable frequency, power, air data rate
    - RSSI reporting
    - Address-based routing
    - Encryption support
    - Buffer size management

Author: Watchmen Project
"""

try:
    from machine import Pin, UART
except ImportError:
    print("ERROR: machine module not found. not running on openmv OpenMV.")
    raise

import time
from logger import logger

# =============================================================================
# Configuration Constants
# =============================================================================

# Module Configuration Headers
# 0xC0: Settings persist after power-off (EEPROM)
# 0xC2: Settings lost after power-off (RAM only, default)
CFG_HEADER_PERSISTENT = 0xC0
CFG_HEADER_VOLATILE = 0xC2

# Default configuration header (volatile - resets on power cycle)
DEFAULT_CFG_HEADER = CFG_HEADER_VOLATILE

# Response headers
RESPONSE_SUCCESS = 0xC1
RESPONSE_FAILURE = 0xC0

# Register offsets in configuration array (12 bytes total)
REG_ADDR_HEADER = 0    # Configuration header
REG_ADDR_LEN_H = 1     # Length high byte
REG_ADDR_LEN_L = 2     # Length low byte
REG_ADDR_ADDR_H = 3    # Node address high byte
REG_ADDR_ADDR_L = 4    # Node address low byte
REG_ADDR_NET_ID = 5    # Network ID
REG_ADDR_UART_AIR = 6  # UART baud rate + Air data rate
REG_ADDR_BUFFER_PWR = 7 # Buffer size + TX power + RSSI noise enable
REG_ADDR_FREQ_OFFSET = 8 # Frequency offset
REG_ADDR_MODE_RSSI = 9  # Operating mode + Packet RSSI enable
REG_ADDR_CRYPT_H = 10   # Encryption key high byte
REG_ADDR_CRYPT_L = 11   # Encryption key low byte

# Frequency ranges for different modules
FREQ_RANGE_400MHZ_START = 410  # E22-400T22S: 410-493 MHz
FREQ_RANGE_400MHZ_END = 493
FREQ_RANGE_900MHZ_START = 850  # E22-900T22S: 850-930 MHz
FREQ_RANGE_900MHZ_END = 930

# Configuration retry settings
CFG_RETRY_ATTEMPTS = 3
CFG_RETRY_DELAY_MS = 500
CFG_WRITE_DELAY_MS = 300
CFG_RESPONSE_WAIT_MS = 200

# UART settings
UART_CONFIG_BAUD = 9600    # Initial baud rate for configuration
UART_NORMAL_BAUD = 115200  # Target baud rate for normal operation
UART_TIMEOUT_MS = 2000     # UART timeout in milliseconds

# Mode switching delays
MODE_SWITCH_DELAY_MS = 100   # Delay when switching M0/M1 modes
UART_INIT_DELAY_MS = 500     # Delay after UART initialization
UART_STABILIZE_DELAY_MS = 30 # Delay for UART to stabilize

# Message transmission delays
TX_DELAY_MS = 150            # Delay after sending message
RX_DELAY_MS = 150            # Delay before reading received message

# RSSI command
RSSI_CMD_BYTES = bytes([0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02])
RSSI_RESPONSE_HEADER = bytes([0xC1, 0x00, 0x02])
RSSI_WAIT_MS = 500

# =============================================================================
# SX126x LoRa Module Driver Class
# =============================================================================

class sx126x:
    """
    Driver class for SX126x-based LoRa modules (E22/E32 series).
    
    This class handles all communication with the LoRa module including:
    - Configuration mode entry/exit via M0/M1 GPIO pins
    - Module parameter configuration (frequency, power, address, etc.)
    - Data transmission and reception
    - RSSI measurement
    
    Attributes:
        M0_PIN (str): GPIO pin name for M0 mode control (default: 'P6')
        M1_PIN (str): GPIO pin name for M1 mode control (default: 'P7')
        uart_num (int): UART number (default: 1)
        addr (int): Module address (0-65535)
        freq (int): Operating frequency in MHz
        power (int): TX power in dBm (10, 13, 17, or 22)
        rssi (bool): Enable RSSI reporting
        config_success (bool): Configuration status flag
        target_baud (int): Target UART baud rate (default: 115200)
    """
    
    # Default GPIO pins for OpenMV RT1062
    M0_PIN = 'P6'
    M1_PIN = 'P7'
    
    # UART baud rate constants (register values)
    SX126X_UART_BAUDRATE_1200 = 0x00
    SX126X_UART_BAUDRATE_2400 = 0x20
    SX126X_UART_BAUDRATE_4800 = 0x40
    SX126X_UART_BAUDRATE_9600 = 0x60
    SX126X_UART_BAUDRATE_19200 = 0x80
    SX126X_UART_BAUDRATE_38400 = 0xA0
    SX126X_UART_BAUDRATE_57600 = 0xC0
    SX126X_UART_BAUDRATE_115200 = 0xE0
    
    # Package/buffer size constants (register values)
    SX126X_PACKAGE_SIZE_240_BYTE = 0x00
    SX126X_PACKAGE_SIZE_128_BYTE = 0x40
    SX126X_PACKAGE_SIZE_64_BYTE = 0x80
    SX126X_PACKAGE_SIZE_32_BYTE = 0xC0
    
    # TX power constants (register values)
    SX126X_Power_22dBm = 0x00
    SX126X_Power_17dBm = 0x01
    SX126X_Power_13dBm = 0x02
    SX126X_Power_10dBm = 0x03
    
    # Air data rate lookup dictionary (bps -> register value)
    lora_air_speed_dic = {
        1200: 0x01,
        2400: 0x02,
        4800: 0x03,
        9600: 0x04,
        19200: 0x05,
        38400: 0x06,
        62500: 0x07
    }
    
    # TX power lookup dictionary (dBm -> register value)
    lora_power_dic = {
        22: 0x00,
        17: 0x01,
        13: 0x02,
        10: 0x03
    }
    
    # Buffer size lookup dictionary (bytes -> register value)
    lora_buffer_size_dic = {
        240: SX126X_PACKAGE_SIZE_240_BYTE,
        128: SX126X_PACKAGE_SIZE_128_BYTE,
        64: SX126X_PACKAGE_SIZE_64_BYTE,
        32: SX126X_PACKAGE_SIZE_32_BYTE
    }
    
    def __init__(self, uart_num=1, freq=868, addr=0, power=22, rssi=True, 
                 air_speed=2400, net_id=0, buffer_size=240, crypt=0,
                 relay=False, lbt=False, wor=False, m0_pin='P6', m1_pin='P7'):
        """
        Initialize SX126x LoRa module.
        
        The initialization process:
        1. Initializes GPIO pins (M0, M1) for mode control
        2. Enters configuration mode
        3. Opens UART at 9600 baud for configuration
        4. Configures module parameters
        5. Switches to target baud rate (115200)
        6. Returns to normal operation mode
        
        Args:
            uart_num (int): UART number (default: 1)
            freq (int): Operating frequency in MHz (default: 868)
                       400 MHz range: 410-493 MHz
                       900 MHz range: 850-930 MHz
            addr (int): Module node address 0-65535 (default: 0)
            power (int): TX power in dBm: 10, 13, 17, or 22 (default: 22)
            rssi (bool): Enable RSSI reporting in received packets (default: True)
            air_speed (int): Air data rate in bps: 1200-62500 (default: 2400)
            net_id (int): Network ID 0-255 (default: 0)
            buffer_size (int): Packet buffer size: 32, 64, 128, or 240 (default: 240)
            crypt (int): Encryption key 0-65535 (default: 0, disabled)
            relay (bool): Enable relay mode (default: False)
            lbt (bool): Enable Listen Before Talk (default: False)
            wor (bool): Enable Wake On Radio (default: False)
            m0_pin (str): GPIO pin name for M0 (default: 'P6')
            m1_pin (str): GPIO pin name for M1 (default: 'P7')
            
        Raises:
            Exception: If GPIO or UART initialization fails
        """
        # Store configuration parameters
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.uart_num = uart_num
        self.power = power
        self.config_success = False
        self.target_baud = UART_NORMAL_BAUD
        
        # Calculate frequency offset based on module type
        if freq > FREQ_RANGE_900MHZ_START:
            self.start_freq = FREQ_RANGE_900MHZ_START
            self.offset_freq = freq - FREQ_RANGE_900MHZ_START
        elif freq > FREQ_RANGE_400MHZ_START:
            self.start_freq = FREQ_RANGE_400MHZ_START
            self.offset_freq = freq - FREQ_RANGE_400MHZ_START
        else:
            raise ValueError(f"Frequency {freq} MHz out of valid range (410-493 or 850-930)")
        
        logger.info(f"Initializing with UART {uart_num}, M0={m0_pin}, M1={m1_pin}")
        
        # Initialize GPIO pins for mode control (M0, M1)
        try:
            self.M0 = Pin(m0_pin, Pin.OUT)
            self.M1 = Pin(m1_pin, Pin.OUT)
            logger.info(f"GPIO pins initialized successfully")
        except Exception as e:
            logger.error(f"GPIO initialization failed: {e}")
            raise
        
        # Enter configuration mode: M0=LOW, M1=HIGH
        # In configuration mode, module accepts AT commands over UART
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        # log(f"M0=LOW, M1=HIGH (configuration mode)")
        
        # Initialize UART at configuration baud rate (9600)
        # Configuration must be done at 9600 baud initially
        try:
            self.ser = UART(uart_num, UART_CONFIG_BAUD, timeout=UART_TIMEOUT_MS)
            logger.info(f"UART {uart_num} initialized at {UART_CONFIG_BAUD} baud")
        except Exception as e:
            logger.error(f"UART initialization failed: {e}")
            raise
        
        # Give module time to stabilize after UART initialization
        time.sleep_ms(UART_INIT_DELAY_MS)
        
        # Initialize configuration register array
        # Format: [Header, Len_H, Len_L, Addr_H, Addr_L, NetID, UART+Air, Buffer+Power, Freq, Mode+RSSI, Crypt_H, Crypt_L]
        self.cfg_reg = [DEFAULT_CFG_HEADER, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x12, 0x43, 0x00, 0x00]
        
        # Configure module with specified parameters
        self.set(freq, addr, power, rssi, air_speed, net_id, buffer_size, crypt, relay, lbt, wor)
        
        # Reopen UART at target baud rate (115200)
        # log(f"[INFO] Reopening UART with target baud rate")
        self.ser.deinit()  # Close current UART
        time.sleep_ms(300)  # Wait for UART to close properly
        
        # Critical: Module must be back in configuration mode for baud rate verification
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        # log(f"M0=LOW, M1=HIGH (configuration mode)")
        time.sleep_ms(UART_INIT_DELAY_MS)
        
        # Reinitialize UART at target baud rate
        try:
            self.ser = UART(uart_num, self.target_baud, timeout=UART_TIMEOUT_MS)
            # logger.debug(f"UART {uart_num} reopened at {self.target_baud} baud")
        except Exception as e:
            logger.error(f"UART reinitialization failed: {e}")
            raise
        
        # Clear any stale data from input buffer
        while self.ser.any():
            self.ser.read()
        
        time.sleep_ms(UART_STABILIZE_DELAY_MS)  # Allow UART to stabilize
        
        # Note: get_settings() can be called here to verify configuration,
        # but currently disabled due to potential issues with baud rate switching
        # self.get_settings()
        
        # Exit configuration mode: M0=LOW, M1=LOW (normal operation mode)
        self.M0.value(0)  # LOW
        self.M1.value(0)  # LOW
        # log(f"M0=LOW, M1=LOW (normal mode)")
        time.sleep_ms(MODE_SWITCH_DELAY_MS)  # Allow time for mode switch
    
    def set(self, freq, addr, power, rssi, air_speed=2400,
            net_id=0, buffer_size=240, crypt=0,
            relay=False, lbt=False, wor=False):
        """
        Configure LoRa module parameters.
        
        This method builds the 12-byte configuration register and sends it
        to the module. The configuration is written via UART while the module
        is in configuration mode (M0=LOW, M1=HIGH).
        
        Configuration Register Layout (12 bytes):
        [0]  Header (0xC0 for persistent, 0xC2 for volatile)
        [1]  Length high byte (always 0x00)
        [2]  Length low byte (always 0x09 for 9 parameters)
        [3]  Node address high byte
        [4]  Node address low byte
        [5]  Network ID
        [6]  UART baud rate (upper 3 bits) + Air data rate (lower 3 bits)
        [7]  Buffer size (upper 2 bits) + TX power (bits 1-2) + RSSI noise enable (bit 5)
        [8]  Frequency offset (0-18 for 900MHz, 0-83 for 400MHz)
        [9]  Operating mode (0x43 for fixed point, 0x03 for relay) + Packet RSSI enable (bit 7)
        [10] Encryption key high byte
        [11] Encryption key low byte
        
        Args:
            freq (int): Operating frequency in MHz
            addr (int): Node address 0-65535
            power (int): TX power: 10, 13, 17, or 22 dBm
            rssi (bool): Enable packet RSSI reporting
            air_speed (int): Air data rate: 1200-62500 bps
            net_id (int): Network ID 0-255
            buffer_size (int): Buffer size: 32, 64, 128, or 240 bytes
            crypt (int): Encryption key 0-65535 (0 = disabled)
            relay (bool): Enable relay mode
            lbt (bool): Enable Listen Before Talk (not implemented)
            wor (bool): Enable Wake On Radio (not implemented)
            
        Note:
            Configuration is sent with retry logic (up to 3 attempts).
            Module must respond with 0xC1 header to indicate success.
        """
        self.send_to = addr
        self.addr = addr
        
        # Ensure module is in configuration mode
        # M0=LOW, M1=HIGH places module in configuration/AT command mode
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        time.sleep_ms(MODE_SWITCH_DELAY_MS)
        
        # Extract bytes for multi-byte parameters
        low_addr = addr & 0xFF          # Lower 8 bits of address
        high_addr = (addr >> 8) & 0xFF  # Upper 8 bits of address
        net_id_temp = net_id & 0xFF
        
        # Calculate frequency offset from base frequency
        if freq > FREQ_RANGE_900MHZ_START:
            freq_temp = freq - FREQ_RANGE_900MHZ_START
            self.start_freq = FREQ_RANGE_900MHZ_START
            self.offset_freq = freq_temp
        elif freq > FREQ_RANGE_400MHZ_START:
            freq_temp = freq - FREQ_RANGE_400MHZ_START
            self.start_freq = FREQ_RANGE_400MHZ_START
            self.offset_freq = freq_temp
        else:
            raise ValueError(f"Frequency {freq} MHz out of valid range")
        
        # Look up register values from dictionaries
        air_speed_temp = self.lora_air_speed_dic.get(air_speed, None)
        if air_speed_temp is None:
            raise ValueError(f"Invalid air speed: {air_speed}. Valid: {list(self.lora_air_speed_dic.keys())}")
        
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, None)
        if buffer_size_temp is None:
            raise ValueError(f"Invalid buffer size: {buffer_size}. Valid: {list(self.lora_buffer_size_dic.keys())}")
        
        power_temp = self.lora_power_dic.get(power, None)
        if power_temp is None:
            raise ValueError(f"Invalid power: {power} dBm. Valid: {list(self.lora_power_dic.keys())}")
        
        # Configure RSSI reporting
        # Bit 7 of register 9 enables packet RSSI in received messages
        if rssi:
            rssi_temp = 0x80  # Enable packet RSSI reporting
        else:
            rssi_temp = 0x00  # Disable packet RSSI reporting
        
        # Extract encryption key bytes
        l_crypt = crypt & 0xFF          # Lower 8 bits of encryption key
        h_crypt = (crypt >> 8) & 0xFF   # Upper 8 bits of encryption key
        
        # Build configuration register array based on mode
        if not relay:
            # Fixed point mode (normal operation)
            # Register 6: UART baud (115200=0xE0) + Air data rate (0x01-0x07)
            # Register 7: Buffer size (0x00/0x40/0x80/0xC0) + Power (0x00-0x03) + RSSI noise enable (0x20)
            # Register 9: Fixed point mode (0x43) + Packet RSSI enable (0x80 if enabled)
            self.cfg_reg[REG_ADDR_ADDR_H] = high_addr
            self.cfg_reg[REG_ADDR_ADDR_L] = low_addr
            self.cfg_reg[REG_ADDR_NET_ID] = net_id_temp
            self.cfg_reg[REG_ADDR_UART_AIR] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
            # 0x20 enables noise RSSI reading (background signal strength)
            self.cfg_reg[REG_ADDR_BUFFER_PWR] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[REG_ADDR_FREQ_OFFSET] = freq_temp
            # 0x43 = Fixed point mode (0x40) + Reserved bit (0x03)
            # Adding rssi_temp (0x80) enables packet RSSI in received data
            self.cfg_reg[REG_ADDR_MODE_RSSI] = 0x43 + rssi_temp
            self.cfg_reg[REG_ADDR_CRYPT_H] = h_crypt
            self.cfg_reg[REG_ADDR_CRYPT_L] = l_crypt
        else:
            # Relay mode (forwards messages)
            # Uses fixed addresses 0x0102, 0x0203, 0x0304
            self.cfg_reg[REG_ADDR_ADDR_H] = 0x01
            self.cfg_reg[REG_ADDR_ADDR_L] = 0x02
            self.cfg_reg[REG_ADDR_NET_ID] = 0x03
            self.cfg_reg[REG_ADDR_UART_AIR] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
            self.cfg_reg[REG_ADDR_BUFFER_PWR] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[REG_ADDR_FREQ_OFFSET] = freq_temp
            # 0x03 = Relay mode
            self.cfg_reg[REG_ADDR_MODE_RSSI] = 0x03 + rssi_temp
            self.cfg_reg[REG_ADDR_CRYPT_H] = h_crypt
            self.cfg_reg[REG_ADDR_CRYPT_L] = l_crypt
        
        # Clear input buffer before sending configuration
        while self.ser.any():
            self.ser.read()
        
        # Parse and display configuration being sent
        sent_config = self._parse_config_bytes(self.cfg_reg)
        if sent_config:
            self._display_config_table("CONFIGURATION TO BE SENT", sent_config)
        else:
            logger.debug(f"Sending configuration: {[hex(x) for x in self.cfg_reg]}")
        
        # Send configuration with retry logic
        # Module should respond with 0xC1 header to confirm success
        for attempt in range(CFG_RETRY_ATTEMPTS):
            logger.info(f"Configuration attempt {attempt + 1}")
            
            # Send 12-byte configuration register
            self.ser.write(bytes(self.cfg_reg))
            time.sleep_ms(CFG_WRITE_DELAY_MS)  # Allow time for module to process
            
            # Check for response
            if self.ser.any():
                time.sleep_ms(CFG_RESPONSE_WAIT_MS)  # Wait for complete response
                r_buff = self.ser.read()
                
                # Validate response: first byte should be 0xC1 (success)
                if r_buff and len(r_buff) > 0 and r_buff[0] == RESPONSE_SUCCESS:
                    # Parse and display received configuration
                    received_config = self._parse_config_bytes(r_buff)
                    if received_config:
                        self._display_config_table("CONFIGURATION RECEIVED (CONFIRMED)", received_config)
                    else:
                        logger.debug(f"Received response: {[hex(x) for x in r_buff]}")
                    
                    # Verify configuration matches (compare parameter values)
                    if received_config and sent_config:
                        config_match = True
                        mismatches = []
                        
                        # Compare key parameters (ignore header as it may differ)
                        if received_config['node_addr'] != sent_config['node_addr']:
                            config_match = False
                            mismatches.append(f"Node Address: sent={sent_config['node_addr']}, received={received_config['node_addr']}")
                        if received_config['frequency'] != sent_config['frequency']:
                            config_match = False
                            mismatches.append(f"Frequency: sent={sent_config['frequency']}, received={received_config['frequency']}")
                        if received_config['uart_baud'] != sent_config['uart_baud']:
                            config_match = False
                            mismatches.append(f"UART Baud: sent={sent_config['uart_baud']}, received={received_config['uart_baud']}")
                        if received_config['air_speed'] != sent_config['air_speed']:
                            config_match = False
                            mismatches.append(f"Air Speed: sent={sent_config['air_speed']}, received={received_config['air_speed']}")
                        if received_config['power'] != sent_config['power']:
                            config_match = False
                            mismatches.append(f"TX Power: sent={sent_config['power']}, received={received_config['power']}")
                        
                        if config_match:
                            logger.info(f"=" * 60)
                            logger.info(f"  CONFIGURATION SUCCESSFUL")
                            logger.info(f"  All parameters match sent configuration")
                            logger.info(f"=" * 60 + "\n")
                        else:
                            logger.warning(f"=" * 60)
                            logger.warning(f"  CONFIGURATION PARTIALLY SUCCESSFUL")
                            logger.warning(f"  Some parameters don't match:")
                            for mismatch in mismatches:
                                logger.warning(f"    - {mismatch}")
                            logger.warning(f"=" * 60)
                    else:
                        logger.info(f"=" * 60)
                        logger.info(f"  CONFIGURATION SUCCESSFUL")
                        logger.info(f"  Module acknowledged configuration")
                        logger.info(f"=" * 60)
                    
                    self.config_success = True
                    break
                else:
                    logger.warning(f"Configuration failed, unexpected response: {[hex(x) for x in r_buff] if r_buff else 'None'}")
            else:
                logger.warning(f"No response from module")
            
            # Clear input buffer before retry
            while self.ser.any():
                self.ser.read()
            time.sleep_ms(CFG_RETRY_DELAY_MS)
            
            # Final attempt failed
            if attempt == CFG_RETRY_ATTEMPTS - 1:
                logger.error(f"=" * 60)
                logger.error(f"  ✗ CONFIGURATION FAILED")
                logger.error(f"  Attempted {CFG_RETRY_ATTEMPTS} times with no valid response")
                logger.error(f"  Troubleshooting:")
                logger.error(f"    - Check UART connections (TX/RX swapped?)")
                logger.error(f"    - Verify M0/M1 pin connections")
                logger.error(f"    - Ensure power supply is 3.3V and stable")
                logger.error(f"    - Check baud rate compatibility")
                logger.error(f"=" * 60)
                self.config_success = False
        
        # Exit configuration mode: return to normal operation
        self.M0.value(0)  # LOW
        self.M1.value(0)  # LOW
        time.sleep_ms(MODE_SWITCH_DELAY_MS)
    
    def _parse_config_bytes(self, cfg_bytes):
        """
        Parse configuration bytes and return human-readable parameter dictionary.
        
        Args:
            cfg_bytes (list or bytes): 12-byte configuration register array
            
        Returns:
            dict: Dictionary with parsed configuration parameters
        """
        # Convert to list if bytes object
        if isinstance(cfg_bytes, bytes):
            cfg_bytes = list(cfg_bytes)
        
        if len(cfg_bytes) < 12:
            return None
        
        # Parse bytes
        high_addr = cfg_bytes[REG_ADDR_ADDR_H]
        low_addr = cfg_bytes[REG_ADDR_ADDR_L]
        net_id = cfg_bytes[REG_ADDR_NET_ID]
        uart_speed_reg = cfg_bytes[REG_ADDR_UART_AIR]
        power_buffer_reg = cfg_bytes[REG_ADDR_BUFFER_PWR]
        freq_offset = cfg_bytes[REG_ADDR_FREQ_OFFSET]
        mode_rssi_reg = cfg_bytes[REG_ADDR_MODE_RSSI]
        h_crypt = cfg_bytes[REG_ADDR_CRYPT_H]
        l_crypt = cfg_bytes[REG_ADDR_CRYPT_L]
        
        # Calculate derived values
        node_addr = (high_addr << 8) + low_addr
        frequency = freq_offset + self.start_freq
        
        # Decode UART baud rate (upper 3 bits of register 6)
        uart_rates = {
            0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
            0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200
        }
        uart_baud = uart_rates.get(uart_speed_reg & 0xE0, "Unknown")
        
        # Decode air data rate (lower 3 bits of register 6)
        air_speeds = {0x01: 1200, 0x02: 2400, 0x03: 4800, 0x04: 9600,
                      0x05: 19200, 0x06: 38400, 0x07: 62500}
        air_speed = air_speeds.get(uart_speed_reg & 0x07, "Unknown")
        
        # Decode buffer size (upper 2 bits of register 7)
        buffer_sizes = {0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32}
        buffer_size = buffer_sizes.get(power_buffer_reg & 0xC0, "Unknown")
        
        # Decode TX power (lower 2 bits of register 7)
        power_levels = {0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10}
        power = power_levels.get(power_buffer_reg & 0x03, "Unknown")
        
        # Decode encryption key
        crypt_key = (h_crypt << 8) + l_crypt
        
        # Decode flags
        rssi_enabled = bool(mode_rssi_reg & 0x80)
        noise_rssi_enabled = bool(power_buffer_reg & 0x20)
        cfg_header = cfg_bytes[REG_ADDR_HEADER]
        cfg_persistent = "Persistent (0xC0)" if cfg_header == CFG_HEADER_PERSISTENT else "Volatile (0xC2)"
        
        # Determine operating mode from register 9
        mode_val = mode_rssi_reg & 0x7F  # Mask out RSSI bit
        if mode_val == 0x43:
            op_mode = "Fixed Point"
        elif mode_val == 0x03:
            op_mode = "Relay Mode"
        else:
            op_mode = f"Unknown (0x{mode_val:02X})"
        
        return {
            'header': cfg_persistent,
            'node_addr': node_addr,
            'net_id': net_id,
            'frequency': frequency,
            'uart_baud': uart_baud,
            'air_speed': air_speed,
            'power': power,
            'buffer_size': buffer_size,
            'crypt_key': crypt_key,
            'rssi_enabled': rssi_enabled,
            'noise_rssi_enabled': noise_rssi_enabled,
            'op_mode': op_mode,
            'raw_bytes': cfg_bytes
        }
    
    def _display_config_table(self, title, config_dict):
        """
        Display configuration parameters in a formatted table.
        
        Args:
            title (str): Table title
            config_dict (dict): Dictionary returned by _parse_config_bytes()
        """
        if not config_dict:
            logger.warning(f"{title}: Invalid configuration")
            return
        
        logger.info(f"=" * 60)
        logger.info(f"  {title}")
        logger.info(f"=" * 60)
        logger.info(f"  Configuration Header : {config_dict['header']}")
        logger.info(f"  Node Address         : {config_dict['node_addr']} (0x{config_dict['node_addr']:04X})")
        logger.info(f"  Network ID           : {config_dict['net_id']}")
        logger.info(f"  Frequency            : {config_dict['frequency']}.125 MHz")
        logger.info(f"  UART Baud Rate       : {config_dict['uart_baud']} bps")
        logger.info(f"  Air Data Rate        : {config_dict['air_speed']} bps")
        logger.info(f"  TX Power             : {config_dict['power']} dBm")
        logger.info(f"  Buffer Size          : {config_dict['buffer_size']} bytes")
        logger.info(f"  Operating Mode       : {config_dict['op_mode']}")
        logger.info(f"  Encryption Key       : {config_dict['crypt_key']} (0x{config_dict['crypt_key']:04X})")
        logger.info(f"  Packet RSSI          : {'Enabled' if config_dict['rssi_enabled'] else 'Disabled'}")
        logger.info(f"  Noise RSSI           : {'Enabled' if config_dict['noise_rssi_enabled'] else 'Disabled'}")
        logger.info(f"  Raw Bytes            : {[hex(x) for x in config_dict['raw_bytes']]}")
        logger.info(f"=" * 60)
    
    def get_settings(self):
        """
        Read and display current module settings.
        
        This method enters configuration mode, sends a read command (0xC1 0x00 0x09),
        parses the 12-byte response, and displays all configuration parameters.
        
        The response format matches the configuration register layout:
        [0]  Response header (0xC1)
        [1]  Length high byte (0x00)
        [2]  Length low byte (0x09)
        [3-11] Configuration parameters (same as write format)
        
        Note:
            Currently disabled after baud rate switch due to potential issues.
            Can be enabled for debugging purposes.
        """
        # Enter configuration mode
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        time.sleep_ms(MODE_SWITCH_DELAY_MS)
        
        # Clear input buffer
        while self.ser.any():
            self.ser.read()
        
        # Send read settings command: 0xC1 0x00 0x09
        # 0xC1 = Read command, 0x00 0x09 = Read 9 parameters
        self.ser.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(CFG_RESPONSE_WAIT_MS)
        
        # Check for response
        if not self.ser.any():
            logger.warning(f"No response from module")
            self.M1.value(0)  # Exit config mode
            return
        
        response = self.ser.read()
        
        # Validate response header and length
        if not response or len(response) < 12 or response[0] != RESPONSE_SUCCESS or response[2] != 0x09:
            logger.warning(f"Invalid response: {[hex(x) for x in response] if response else 'None'}")
            self.M1.value(0)  # Exit config mode
            return
        
        # Parse response bytes
        high_addr = response[REG_ADDR_ADDR_H]
        low_addr = response[REG_ADDR_ADDR_L]
        net_id = response[REG_ADDR_NET_ID]
        uart_speed_reg = response[REG_ADDR_UART_AIR]
        power_buffer_reg = response[REG_ADDR_BUFFER_PWR]
        freq_offset = response[REG_ADDR_FREQ_OFFSET]
        mode_rssi_reg = response[REG_ADDR_MODE_RSSI]
        h_crypt = response[REG_ADDR_CRYPT_H]
        l_crypt = response[REG_ADDR_CRYPT_L]
        
        # Decode values
        node_addr = (high_addr << 8) + low_addr
        frequency = freq_offset + self.start_freq
        
        # Decode UART baud rate (upper 3 bits of register 6)
        uart_rates = {
            0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
            0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200
        }
        uart_baud = uart_rates.get(uart_speed_reg & 0xE0, "Unknown")
        
        # Decode air data rate (lower 3 bits of register 6)
        air_speeds = {0x01: 1200, 0x02: 2400, 0x03: 4800, 0x04: 9600,
                      0x05: 19200, 0x06: 38400, 0x07: 62500}
        air_speed = air_speeds.get(uart_speed_reg & 0x07, "Unknown")
        
        # Decode buffer size (upper 2 bits of register 7)
        buffer_sizes = {0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32}
        buffer_size = buffer_sizes.get(power_buffer_reg & 0xC0, "Unknown")
        
        # Decode TX power (lower 2 bits of register 7)
        power_levels = {0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10}
        power = power_levels.get(power_buffer_reg & 0x03, "Unknown")
        
        # Decode encryption key
        crypt_key = (h_crypt << 8) + l_crypt
        
        # Decode flags
        rssi_enabled = bool(mode_rssi_reg & 0x80)  # Bit 7 of register 9
        noise_rssi_enabled = bool(power_buffer_reg & 0x20)  # Bit 5 of register 7
        
        # Display parsed settings
        logger.info(f"=" * 40)
        logger.info(f"      LoRa Module Settings")
        logger.info(f"=" * 40)
        logger.info(f"Node Address    : {node_addr} (0x{node_addr:04X})")
        logger.info(f"Network ID      : {net_id}")
        logger.info(f"Frequency       : {frequency}.125 MHz")
        logger.info(f"UART Baud Rate  : {uart_baud} bps")
        logger.info(f"Air Data Rate   : {air_speed} bps")
        logger.info(f"TX Power        : {power} dBm")
        logger.info(f"Buffer Size     : {buffer_size} bytes")
        logger.info(f"Encryption Key  : {crypt_key} (0x{crypt_key:04X})")
        logger.info(f"Packet RSSI     : {'Enabled' if rssi_enabled else 'Disabled'}")
        logger.info(f"Noise RSSI      : {'Enabled' if noise_rssi_enabled else 'Disabled'}")
        logger.info(f"=" * 40)
        
        # Return to normal mode
        self.M1.value(0)  # LOW
    
    def send(self, target_addr, message):
        """
        Send a message to a target node address.
        
        Message Format (7 bytes header + payload + newline):
        [0-1]  Target address (2 bytes: high, low)
        [2]    Target frequency offset
        [3-4]  Source (own) address (2 bytes: high, low)
        [5]    Source frequency offset
        [6+]   Message payload
        [last] Newline character (0x0A)
        
        The module uses this addressing to route messages in a mesh network.
        Each node only processes messages where the target address matches its
        own address, or where target address is 0xFFFF (broadcast).
        
        Args:
            target_addr (int): Destination node address (0-65535, 65535=broadcast)
            message (bytes): Message payload to send
            
        Note:
            - Module must be in normal mode (M0=LOW, M1=LOW)
            - Adds small delay after transmission for module processing
            - Messages exceeding buffer_size will be truncated
        """
        # Warn if module wasn't properly configured
        if not hasattr(self, 'config_success') or not self.config_success:
            logger.warning(f"Module not properly configured, send may fail")
        
        # Calculate frequency offset for target
        offset_frequency = self.freq - (FREQ_RANGE_900MHZ_START if self.freq > FREQ_RANGE_900MHZ_START else FREQ_RANGE_400MHZ_START)
        
        # Build message packet with addressing header
        # Format: [target_high][target_low][target_freq][own_high][own_low][own_freq][message][\n]
        data = bytes([target_addr >> 8]) + \
               bytes([target_addr & 0xFF]) + \
               bytes([offset_frequency]) + \
               bytes([self.addr >> 8]) + \
               bytes([self.addr & 0xFF]) + \
               bytes([self.offset_freq]) + \
               message + b'\n'
        
        # Send message over UART
        self.ser.write(data)
        time.sleep_ms(TX_DELAY_MS)  # Allow module time to process transmission
    
    def receive(self):
        """
        Receive a message from the LoRa module.
        
        This method checks if data is available in the UART receive buffer,
        reads a complete line (ending with newline), and extracts the message
        payload (skipping the addressing header).
        
        Message Format (received):
        [0-1]  Sender address (2 bytes: high, low)
        [2]    Frequency offset
        [3+]   Message payload
        [last-1] RSSI value (if RSSI enabled, only present if rssi=True)
        [last] Newline character (0x0A, stripped)
        
        If RSSI is enabled, the last byte before newline contains RSSI value.
        
        Returns:
            tuple: (message_payload, rssi_value) where:
                - message_payload (bytes): Message payload (excluding addressing header and RSSI)
                - rssi_value (int or None): RSSI in dBm if enabled, None otherwise
            Returns (None, None) if no data available
            
        Note:
            - Module must be in normal mode (M0=LOW, M1=LOW)
            - Minimum message size is 6 bytes (3 header + 3 payload + newline)
            - If RSSI enabled: minimum is 7 bytes (3 header + 3 payload + 1 RSSI + newline)
            - Reads complete line to avoid partial messages
            - RSSI value is decoded as: rssi_dbm = -(256 - rssi_byte)
        """
        if self.ser.any():
            time.sleep_ms(RX_DELAY_MS)  # Wait for complete message
            r_buff = self.ser.readline()
            
            # Validate message has minimum required length
            # Handle newline: readline() may or may not strip it depending on MicroPython version
            # Strip newline manually if present (0x0A)
            if r_buff and len(r_buff) > 0 and r_buff[-1] == 0x0A:
                r_buff = r_buff[:-1]
            
            # Without RSSI: sender_addr(2) + freq(1) + payload(1) = 4 bytes minimum
            # With RSSI: sender_addr(2) + freq(1) + payload(1) + RSSI(1) = 5 bytes minimum
            if r_buff and len(r_buff) >= 5:
                # Check if RSSI is enabled - if so, the last byte is RSSI
                if self.rssi:
                    # RSSI enabled: format is [header(3)][payload][RSSI(1)]
                    # Minimum length with RSSI: 3 (header) + 1 (payload) + 1 (RSSI) = 5 bytes
                    # Extract RSSI value (last byte)
                    rssi_byte = r_buff[-1]
                    # Extract message payload (skip first 3 bytes, exclude RSSI)
                    msg = r_buff[3:-1]
                    # Decode RSSI: actual_RSSI = -(256 - value) dBm
                    rssi_dbm = -(256 - rssi_byte)
                    
                    # Check if message starts with frequency offset byte (indicates extraction issue)
                    if len(msg) > 0 and hasattr(self, 'offset_freq') and msg[0] == self.offset_freq:
                        # Message starts with frequency offset - this shouldn't happen
                        # This suggests an extra byte is being included in the payload
                        # Try extracting message starting from byte 4 instead of 3 (skip one more byte)
                        if len(r_buff) >= 6:
                            # Skip one more byte (the frequency byte that's incorrectly in payload)
                            msg = r_buff[4:-1]
                            logger.debug(f"[RSSI] Adjusted extraction - skipped extra frequency byte")
                    
                    return (msg, rssi_dbm)
                else:
                    # RSSI disabled: format is [header(3)][payload]
                    # Extract message payload (skip first 3 bytes)
                    msg = r_buff[3:]
                    return (msg, None)
            elif r_buff and len(r_buff) >= 4:
                # Very short message without RSSI (minimum length: 4 bytes)
                # Format: [header(3)][payload(1)]
                if not self.rssi:
                    msg = r_buff[3:]
                    return (msg, None)
        
        return (None, None)
    
    def get_channel_rssi(self):
        """
        Read channel RSSI (Received Signal Strength Indicator).
        
        This command reads the background noise level on the current channel,
        which is useful for assessing channel conditions before transmission.
        
        Command Format: 0xC0 0xC1 0xC2 0xC3 0x00 0x02
        Response Format: 0xC1 0x00 0x02 [RSSI_value]
        
        The RSSI value is encoded as: actual_RSSI = -(256 - value) dBm
        
        Returns:
            None (logs RSSI value instead)
            
        Note:
            - Module must be in normal mode
            - RSSI reading may take up to 500ms
            - Background noise RSSI is different from packet RSSI
        """
        # Ensure normal mode
        self.M1.value(0)  # LOW
        self.M0.value(0)  # LOW
        time.sleep_ms(MODE_SWITCH_DELAY_MS)
        
        # Clear input buffer
        while self.ser.any():
            self.ser.read()
        
        # Send RSSI read command
        self.ser.write(RSSI_CMD_BYTES)
        time.sleep_ms(RSSI_WAIT_MS)  # Wait for module to measure and respond
        
        # Read response
        if self.ser.any():
            time.sleep_ms(CFG_RESPONSE_WAIT_MS)
            re_temp = self.ser.read()
            
            # Validate response format
            if re_temp and len(re_temp) >= 4 and \
               re_temp[0] == RSSI_RESPONSE_HEADER[0] and \
               re_temp[1] == RSSI_RESPONSE_HEADER[1] and \
               re_temp[2] == RSSI_RESPONSE_HEADER[2]:
                # Decode RSSI value: -(256 - value) dBm
                rssi_value = -(256 - re_temp[3])
                logger.info(f"Current noise RSSI: {rssi_value}dBm")
            else:
                logger.warning(f"Failed to receive RSSI value")
        else:
            logger.warning(f"No RSSI response received")
