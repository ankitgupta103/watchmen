import machine
import time
from machine import Pin, UART

class SX126x:
    def __init__(self, uart_id=1, m0_pin='P6', m1_pin='P7', 
                 freq=868, addr=0, power=22, rssi=True, air_speed=2400):
        
        # Pin setup for M0 and M1 using OpenMV pin names
        self.M0 = Pin(m0_pin, Pin.OUT)
        self.M1 = Pin(m1_pin, Pin.OUT)
        
        # Configuration register template
        self.cfg_reg = [0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x12, 0x43, 0x00, 0x00]
        
        # Frequency settings
        self.start_freq = 850 if freq > 850 else 410
        self.offset_freq = freq - self.start_freq
        
        # Air speed dictionary
        self.lora_air_speed_dic = {
            1200: 0x01, 2400: 0x02, 4800: 0x03, 9600: 0x04,
            19200: 0x05, 38400: 0x06, 62500: 0x07
        }
        
        # Power dictionary
        self.lora_power_dic = {22: 0x00, 17: 0x01, 13: 0x02, 10: 0x03}
        
        # Buffer size dictionary
        self.lora_buffer_size_dic = {
            240: 0x00, 128: 0x40, 64: 0x80, 32: 0xC0
        }
        
        # UART baudrate constants - keeping at 9600
        self.SX126X_UART_BAUDRATE_9600 = 0x60
        
        # Initialize UART at 9600 for both configuration and data transfer
        # OpenMV RT1062 UART3 is commonly used (TX=P4, RX=P5)
        print("[INFO] Initializing UART at 9600 baud...")
        self.uart = UART(uart_id, baudrate=9600)
        
        # Configure the module
        self.configure(freq, addr, power, rssi, air_speed)
        
        # Set to normal mode (staying at 9600 baud)
        self.set_normal_mode()
        print("[INFO] SX126x initialization complete at 9600 baud")
    
    def set_config_mode(self):
        """Set module to configuration mode (M0=0, M1=1)"""
        self.M0.value(0)
        self.M1.value(1)
        time.sleep_ms(100)
    
    def set_normal_mode(self):
        """Set module to normal mode (M0=0, M1=0)"""
        self.M0.value(0)
        self.M1.value(0)
        time.sleep_ms(100)
    
    def configure(self, freq, addr, power, rssi, air_speed=2400, 
                 net_id=0, buffer_size=240, crypt=0):
        """Configure the LoRa module"""
        
        print(f"[INFO] Configuring: Freq={freq}MHz, Addr={addr}, Power={power}dBm")
        
        # Set configuration mode
        self.set_config_mode()
        
        # Prepare configuration
        low_addr = addr & 0xff
        high_addr = (addr >> 8) & 0xff
        net_id_temp = net_id & 0xff
        freq_temp = self.offset_freq
        
        air_speed_temp = self.lora_air_speed_dic.get(air_speed, 0x02)
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, 0x00)
        power_temp = self.lora_power_dic.get(power, 0x00)
        
        rssi_temp = 0x80 if rssi else 0x00
        
        # Build configuration register
        self.cfg_reg[3] = high_addr
        self.cfg_reg[4] = low_addr
        self.cfg_reg[5] = net_id_temp
        self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
        self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20  # Enable noise RSSI
        self.cfg_reg[8] = freq_temp
        self.cfg_reg[9] = 0x43 + rssi_temp  # Enable packet RSSI if requested
        self.cfg_reg[10] = 0x00  # Crypt high byte
        self.cfg_reg[11] = 0x00  # Crypt low byte
        
        # Send configuration
        success = False
        for attempt in range(3):
            print(f"[INFO] Configuration attempt {attempt + 1}")
            
            # Clear buffers
            while self.uart.any():
                self.uart.read()
            
            # Send configuration
            config_bytes = bytes(self.cfg_reg)
            self.uart.write(config_bytes)
            time.sleep_ms(200)
            
            # Check response
            if self.uart.any():
                time.sleep_ms(100)
                response = self.uart.read()
                if response and len(response) > 0 and response[0] == 0xC1:
                    print("[INFO] Configuration successful")
                    success = True
                    break
                else:
                    print(f"[WARN] Unexpected response: {response}")
            else:
                print("[WARN] No response from module")
        
        if not success:
            print("[ERROR] Configuration failed after 3 attempts")
        
        # Return to normal mode
        self.set_normal_mode()
        return success
    
    def parse_config_response(self, response_data):
        """Parse configuration response and display human-readable settings"""
        
        if not response_data or len(response_data) < 12:
            print(f"[ERROR] Invalid response length: {len(response_data) if response_data else 0}")
            return None
        
        if response_data[0] != 0xC1:
            print(f"[ERROR] Invalid response header: 0x{response_data[0]:02X} (expected 0xC1)")
            return None
        
        if response_data[2] != 0x09:
            print(f"[ERROR] Invalid response command: 0x{response_data[2]:02X} (expected 0x09)")
            return None
        
        print(f"[DEBUG] Raw response: {[hex(b) for b in response_data]}")
        
        # Parse the configuration data
        config = {
            'header': response_data[0],
            'model': response_data[1],
            'length': response_data[2],
            'high_addr': response_data[3],
            'low_addr': response_data[4],
            'net_id': response_data[5],
            'uart_air_speed': response_data[6],
            'sub_packet_settings': response_data[7],
            'frequency': response_data[8],
            'transmission_mode': response_data[9],
            'crypt_high': response_data[10],
            'crypt_low': response_data[11]
        }
        
        # Calculate derived values
        address = (config['high_addr'] << 8) | config['low_addr']
        frequency_mhz = config['frequency'] + self.start_freq
        
        # Parse UART baudrate (bits 7-5)
        uart_baud_code = config['uart_air_speed'] & 0xE0
        uart_baudrates = {
            0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
            0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200
        }
        uart_baud = uart_baudrates.get(uart_baud_code, "Unknown")
        
        # Parse air data rate (bits 2-0)
        air_speed_code = config['uart_air_speed'] & 0x07
        air_speeds = {
            0x00: 300, 0x01: 1200, 0x02: 2400, 0x03: 4800,
            0x04: 9600, 0x05: 19200, 0x06: 38400, 0x07: 62500
        }
        air_speed = air_speeds.get(air_speed_code, "Unknown")
        
        # Parse sub-packet settings
        buffer_size_code = config['sub_packet_settings'] & 0xC0
        buffer_sizes = {0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32}
        buffer_size = buffer_sizes.get(buffer_size_code, "Unknown")
        
        # Parse transmission power (bits 1-0)
        power_code = config['sub_packet_settings'] & 0x03
        power_levels = {0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10}
        power_dbm = power_levels.get(power_code, "Unknown")
        
        # Check noise RSSI enable (bit 5)
        noise_rssi_enabled = bool(config['sub_packet_settings'] & 0x20)
        
        # Parse transmission mode
        rssi_byte_enabled = bool(config['transmission_mode'] & 0x80)
        fixed_transmission = bool(config['transmission_mode'] & 0x40)
        relay_function = bool(config['transmission_mode'] & 0x20)
        lbt_enabled = bool(config['transmission_mode'] & 0x10)
        wor_transmitter = bool(config['transmission_mode'] & 0x08)
        wor_receiver = bool(config['transmission_mode'] & 0x04)
        
        # Encryption key
        encryption_key = (config['crypt_high'] << 8) | config['crypt_low']
        
        # Display parsed configuration
        print("\n" + "="*50)
        print("           LORA MODULE CONFIGURATION")
        print("="*50)
        print(f"Module Address     : {address} (High: {config['high_addr']}, Low: {config['low_addr']})")
        print(f"Network ID         : {config['net_id']}")
        print(f"Frequency          : {frequency_mhz}.125 MHz (Offset: {config['frequency']})")
        print(f"UART Baudrate      : {uart_baud} bps (Code: 0x{uart_baud_code:02X})")
        print(f"Air Data Rate      : {air_speed} bps (Code: 0x{air_speed_code:02X})")
        print(f"Sub-packet Size    : {buffer_size} bytes")
        print(f"TX Power           : {power_dbm} dBm")
        print(f"Encryption Key     : 0x{encryption_key:04X}")
        print("-" * 50)
        print("FEATURES:")
        print(f"  RSSI Byte Output : {'Enabled' if rssi_byte_enabled else 'Disabled'}")
        print(f"  Noise RSSI       : {'Enabled' if noise_rssi_enabled else 'Disabled'}")
        print(f"  Fixed Transmission: {'Enabled' if fixed_transmission else 'Disabled'}")
        print(f"  Relay Function   : {'Enabled' if relay_function else 'Disabled'}")
        print(f"  LBT (Listen Before Talk): {'Enabled' if lbt_enabled else 'Disabled'}")
        print(f"  WOR Transmitter  : {'Enabled' if wor_transmitter else 'Disabled'}")
        print(f"  WOR Receiver     : {'Enabled' if wor_receiver else 'Disabled'}")
        print("=" * 50)
        
        # Return parsed data for programmatic use
        return {
            'address': address,
            'network_id': config['net_id'],
            'frequency_mhz': frequency_mhz,
            'uart_baudrate': uart_baud,
            'air_data_rate': air_speed,
            'buffer_size': buffer_size,
            'tx_power_dbm': power_dbm,
            'encryption_key': encryption_key,
            'rssi_enabled': rssi_byte_enabled,
            'noise_rssi_enabled': noise_rssi_enabled,
            'fixed_transmission': fixed_transmission,
            'relay_enabled': relay_function,
            'lbt_enabled': lbt_enabled,
            'wor_transmitter': wor_transmitter,
            'wor_receiver': wor_receiver,
            'raw_config': config
        }
    
    def send(self, data):
        """Send data"""
        self.set_normal_mode()
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"[INFO] Sending: {data}")
        self.uart.write(data)
        time.sleep_ms(100)
    
    def receive(self, timeout_ms=1000):
        """Receive data with timeout"""
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.uart.any():
                time.sleep_ms(100)  # Allow full message to arrive
                data = self.uart.read()
                
                if data and len(data) > 0:
                    print(f"[INFO] Received {len(data)} bytes: {data}")
                    
                    # Try to decode as text (skip control bytes if present)
                    try:
                        # Simple decoding - adjust based on your data format
                        if len(data) > 3:
                            text_data = data[3:].decode('utf-8', errors='ignore')
                            print(f"[INFO] Message: {text_data}")
                        else:
                            text_data = data.decode('utf-8', errors='ignore')
                            print(f"[INFO] Message: {text_data}")
                    except:
                        print(f"[INFO] Raw data: {[hex(b) for b in data]}")
                    
                    return data
            
            time.sleep_ms(10)
        
        return None
    
    def get_settings(self):
        """Read current module settings"""
        print("[INFO] Reading module settings...")
        
        self.set_config_mode()
        
        # Clear buffer
        while self.uart.any():
            self.uart.read()
        
        # Send get settings command
        self.uart.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(500)
        
        if self.uart.any():
            response = self.uart.read()
            print(f"[DEBUG] Settings response: {[hex(b) for b in response]}")
            
            # Use the new parse function
            parsed_config = self.parse_config_response(response)
            
            if parsed_config:
                print("[INFO] Configuration read successfully!")
                return parsed_config
            else:
                print("[WARN] Failed to parse configuration response")
                return None
        else:
            print("[WARN] No response to settings query")
            return None
        
        self.set_normal_mode()

# Simple test functions
def test_basic_config():
    """Test basic configuration"""
    print("=== Basic Configuration Test ===")
    
    # Initialize LoRa module with OpenMV RT1062 pin names
    # Using UART3 which is commonly available on OpenMV
    lora = SX126x(uart_id=1, m0_pin='P6', m1_pin='P7',
                  freq=868, addr=100, power=22, rssi=True)
    
    # Read current settings
    lora.get_settings()
    
    return lora

def test_send_receive():
    """Test sending and receiving"""
    print("\n=== Send/Receive Test ===")
    
    # Initialize module
    lora1 = SX126x(uart_id=1, m0_pin='P6', m1_pin='P7',
                   freq=868, addr=100, power=22, rssi=True)
    
    # Send test message
    test_message = "Hello LoRa World!"
    print(f"Sending: {test_message}")
    lora1.send(test_message)
    
    # Wait and try to receive
    print("Listening for messages...")
    for i in range(10):
        received = lora1.receive(timeout_ms=1000)
        if received:
            break
        print(f"Attempt {i+1}: No message received")
        time.sleep(1)

def simple_sender():
    """Simple sender example"""
    print("=== Simple Sender ===")
    
    lora = SX126x(uart_id=3, m0_pin='P6', m1_pin='P7',
                  freq=868, addr=100, power=22, rssi=True)
    
    counter = 0
    while True:
        message = f"Message {counter}"
        print(f"Sending: {message}")
        lora.send(message)
        counter += 1
        time.sleep(5)

def simple_receiver():
    """Simple receiver example"""
    print("=== Simple Receiver ===")
    
    lora = SX126x(uart_id=3, m0_pin='P6', m1_pin='P7',
                  freq=868, addr=200, power=22, rssi=True)
    
    print("Listening for messages... (Ctrl+C to stop)")
    while True:
        received = lora.receive(timeout_ms=2000)
        if not received:
            print("No message received, continuing to listen...")

# Additional utility functions for configuration parsing
def test_config_parsing():
    """Test configuration response parsing with sample data"""
    print("=== Configuration Parsing Test ===")
    
    # Sample configuration response (you can replace with real data from your module)
    sample_response = bytes([
        0xC1,  # Header
        0x32,  # Model  
        0x09,  # Length
        0x00,  # High address
        0x64,  # Low address (100 decimal)
        0x00,  # Network ID
        0x62,  # UART baud + air speed
        0x00,  # Sub-packet settings + power
        0x12,  # Frequency offset
        0x43,  # Transmission mode
        0x00,  # Crypt high
        0x00   # Crypt low
    ])
    
    # Create a temporary instance for parsing
    lora = SX126x(uart_id=1, m0_pin='P6', m1_pin='P7', freq=868, addr=100)
    
    print("Parsing sample configuration response:")
    parsed = lora.parse_config_response(sample_response)
    
    if parsed:
        print("\nParsed data returned:")
        for key, value in parsed.items():
            if key != 'raw_config':
                print(f"  {key}: {value}")
    
    return parsed

def validate_configuration(expected_config, actual_response):
    """Validate that the module configuration matches expectations"""
    print("=== Configuration Validation ===")
    
    lora = SX126x(uart_id=3, m0_pin='P6', m1_pin='P7', freq=868, addr=100)
    parsed = lora.parse_config_response(actual_response)
    
    if not parsed:
        print("[ERROR] Could not parse configuration response")
        return False
    
    validation_passed = True
    
    for key, expected_value in expected_config.items():
        if key in parsed:
            actual_value = parsed[key]
            if actual_value == expected_value:
                print(f"✓ {key}: {actual_value} (matches expected)")
            else:
                print(f"✗ {key}: {actual_value} (expected {expected_value})")
                validation_passed = False
        else:
            print(f"⚠ {key}: not found in parsed config")
    
    return validation_passed
if __name__ == "__main__":
    print("SX126x LoRa Test for OpenMV RT1062")
    print("Choose test:")
    print("1. Basic configuration test")
    print("2. Send/Receive test") 
    print("3. Simple sender")
    print("4. Simple receiver")
    
    # Uncomment the test you want to run:
    test_basic_config()
    # test_send_receive()
    # simple_sender()
    # simple_receiver()