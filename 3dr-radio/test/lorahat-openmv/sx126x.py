import machine
import time
from machine import Pin, UART

class SX126X:
    """
    SX126X LoRa module driver for OpenMV RT1062
    M0 connected to Pin P6, M1 connected to Pin P7
    UART connected to appropriate UART pins on OpenMV
    """
    
    def __init__(self, uart_id=3, freq=868, addr=65535, power=22, rssi=True, air_speed=2400):
        """
        Initialize SX126X LoRa module
        
        Args:
            uart_id: UART interface number (default 3 for OpenMV RT1062)
            freq: Frequency in MHz (410-493 or 850-930)
            addr: Node address (0-65535)
            power: Transmission power in dBm (10, 13, 17, 22)
            rssi: Enable RSSI reporting
            air_speed: Air data rate (1200, 2400, 4800, 9600, 19200, 38400, 62500)
        """
        # GPIO pins for mode control (using OpenMV pin naming)
        self.M0 = Pin('P6', Pin.OUT)  # Pin P6 on OpenMV RT1062
        self.M1 = Pin('P7', Pin.OUT)  # Pin P7 on OpenMV RT1062
        
        # Configuration parameters
        self.freq = freq
        self.addr = addr
        self.power = power
        self.rssi = rssi
        self.air_speed = air_speed
        
        # Frequency ranges
        if freq >= 850:
            self.start_freq = 850
            self.freq_offset = freq - 850
        else:
            self.start_freq = 410
            self.freq_offset = freq - 410
        
        # Lookup tables
        self.uart_baud_dict = {
            1200: 0x00, 2400: 0x20, 4800: 0x40, 9600: 0x60,
            19200: 0x80, 38400: 0xA0, 57600: 0xC0, 115200: 0xE0
        }
        
        self.air_speed_dict = {
            1200: 0x01, 2400: 0x02, 4800: 0x03, 9600: 0x04,
            19200: 0x05, 38400: 0x06, 62500: 0x07
        }
        
        self.power_dict = {22: 0x00, 17: 0x01, 13: 0x02, 10: 0x03}
        
        self.buffer_size_dict = {240: 0x00, 128: 0x40, 64: 0x80, 32: 0xC0}
        
        # Initialize UART at 9600 for all communication
        print("[INFO] Initializing UART at 9600 baud...")
        self.uart = UART(uart_id, baudrate=9600, bits=8, parity=None, stop=1, timeout=1000)
        
        # Configure the module
        self.configure_module()
        
        # Set to normal mode
        self.set_normal_mode()
        
    def set_config_mode(self):
        """Set module to configuration mode (M0=0, M1=1)"""
        self.M0.value(0)
        self.M1.value(1)
        time.sleep_ms(200)  # Increased delay for mode switch
        print(f"[DEBUG] Config mode set: M0={self.M0.value()}, M1={self.M1.value()}")
        
    def set_normal_mode(self):
        """Set module to normal transmission mode (M0=0, M1=0)"""
        self.M0.value(0)
        self.M1.value(0)
        time.sleep_ms(200)  # Increased delay for mode switch
        print(f"[DEBUG] Normal mode set: M0={self.M0.value()}, M1={self.M1.value()}")
        
    def configure_module(self):
        """Configure the LoRa module with specified parameters"""
        self.set_config_mode()
        
        # Build configuration register
        high_addr = (self.addr >> 8) & 0xFF
        low_addr = self.addr & 0xFF
        net_id = 0  # Network ID
        
        # Get configuration values from dictionaries
        uart_baud_val = self.uart_baud_dict.get(9600, 0x60)  # Keep UART at 9600
        air_speed_val = self.air_speed_dict.get(self.air_speed, 0x02)
        power_val = self.power_dict.get(self.power, 0x00)
        buffer_size_val = self.buffer_size_dict.get(240, 0x00)  # Default 240 bytes
        
        # RSSI enable bit
        rssi_bit = 0x80 if self.rssi else 0x00
        
        # Configuration register (12 bytes)
        # 0xC2 = volatile settings (lost on power off)
        # 0xC0 = non-volatile settings (retained on power off)
        config_reg = [
            0xC2,                                    # Header - volatile config
            0x00, 0x09,                             # Address and length
            high_addr,                              # Address high byte
            low_addr,                               # Address low byte  
            net_id,                                 # Network ID
            uart_baud_val | air_speed_val,          # UART baud + air speed
            buffer_size_val | power_val | 0x20,     # Buffer + power + noise RSSI enable
            self.freq_offset,                       # Frequency offset
            0x43 | rssi_bit,                        # Mode + RSSI enable
            0x00,                                   # Encryption key high
            0x00                                    # Encryption key low
        ]
        
        print(f"[INFO] Configuring module to keep UART at 9600 baud...")
        print(f"[CONFIG] Address: {self.addr}, Frequency: {self.freq}.125 MHz")
        print(f"[CONFIG] Power: {self.power} dBm, Air Speed: {self.air_speed} bps")
        
        # Send configuration (try twice)
        for attempt in range(2):
            self.uart.write(bytes(config_reg))
            time.sleep_ms(200)
            
            # Check response
            if self.uart.any():
                time.sleep_ms(100)
                response = self.uart.read()
                if response and len(response) > 0 and response[0] == 0xC1:
                    print("[SUCCESS] Module configured successfully!")
                    self.parse_config_response(response)
                    return True
                else:
                    print(f"[WARNING] Unexpected response: {response}")
            else:
                print(f"[WARNING] No response on attempt {attempt + 1}")
                
        print("[ERROR] Configuration failed!")
        return False
    
    def parse_config_response(self, response):
        """Parse and display the configuration response"""
        if len(response) < 12:
            print(f"[ERROR] Response too short: {len(response)} bytes")
            return
            
        print("[RESPONSE] Configuration response received:")
        print(f"[RESPONSE] Raw bytes: {[hex(b) for b in response]}")
        
        if response[0] == 0xC1:
            addr = (response[3] << 8) | response[4]
            net_id = response[5]
            uart_air = response[6]
            buf_power = response[7]
            freq_offset = response[8]
            mode_rssi = response[9]
            
            # Decode settings
            uart_baud = self._decode_uart_baud(uart_air & 0xE0)
            air_speed = self._decode_air_speed(uart_air & 0x07)
            buffer_size = self._decode_buffer_size(buf_power & 0xC0)
            power = self._decode_power(buf_power & 0x03)
            rssi_enabled = bool(mode_rssi & 0x80)
            
            print(f"[PARSED] Address: {addr}")
            print(f"[PARSED] Network ID: {net_id}")
            print(f"[PARSED] Frequency: {freq_offset + self.start_freq}.125 MHz")
            print(f"[PARSED] UART Baud: {uart_baud} bps")
            print(f"[PARSED] Air Speed: {air_speed} bps")
            print(f"[PARSED] Power: {power} dBm")
            print(f"[PARSED] Buffer Size: {buffer_size} bytes")
            print(f"[PARSED] RSSI Enabled: {rssi_enabled}")
    
    def _decode_uart_baud(self, val):
        """Decode UART baud rate from register value"""
        baud_map = {0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
                   0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200}
        return baud_map.get(val, "Unknown")
    
    def _decode_air_speed(self, val):
        """Decode air speed from register value"""
        speed_map = {0x01: 1200, 0x02: 2400, 0x03: 4800, 0x04: 9600,
                    0x05: 19200, 0x06: 38400, 0x07: 62500}
        return speed_map.get(val, "Unknown")
    
    def _decode_buffer_size(self, val):
        """Decode buffer size from register value"""
        size_map = {0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32}
        return size_map.get(val, "Unknown")
    
    def _decode_power(self, val):
        """Decode transmission power from register value"""
        power_map = {0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10}
        return power_map.get(val, "Unknown")
    
    def get_settings(self):
        """Read current module settings"""
        self.set_config_mode()
        time.sleep_ms(200)  # Give more time for mode switch
        
        # Clear any existing data
        self.uart.read()
        
        print("[INFO] Requesting current settings...")
        self.uart.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(800)  # Longer wait for response
        
        if self.uart.any():
            response = self.uart.read()
            print(f"[INFO] Settings response: {[hex(b) for b in response]} (length: {len(response)})")
            if response and len(response) >= 12 and response[0] == 0xC1:
                self.parse_config_response(response)
                self.set_normal_mode()
                return True
            else:
                print(f"[WARNING] Unexpected response format or length")
        else:
            print("[ERROR] No response to settings request")
            
        self.set_normal_mode()
        return False
    
    def send_data(self, data):
        """Send data via LoRa"""
        self.set_normal_mode()
        
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        print(f"[INFO] Sending {len(data)} bytes: {data}")
        self.uart.write(data)
        time.sleep_ms(100)
    
    def receive_data(self):
        """Check for received data"""
        if self.uart.any():
            time.sleep_ms(100)  # Wait for complete packet
            data = self.uart.read()
            
            if data and len(data) > 3:
                # Parse LoRa packet format
                sender_addr = (data[0] << 8) | data[1]
                freq_info = data[2]
                payload = data[3:]
                
                # Check for RSSI byte at the end
                if self.rssi and len(payload) > 0:
                    rssi_val = 256 - payload[-1]
                    payload = payload[:-1]
                    print(f"[RX] From addr {sender_addr}, freq {freq_info + self.start_freq}.125 MHz")
                    print(f"[RX] Data: {payload}")
                    print(f"[RX] RSSI: -{rssi_val} dBm")
                else:
                    print(f"[RX] From addr {sender_addr}, freq {freq_info + self.start_freq}.125 MHz")
                    print(f"[RX] Data: {payload}")
                    
                return {'addr': sender_addr, 'freq': freq_info, 'data': payload}
        
        return None

# Example usage and test functions
def test_settings_only():
    """Test only settings retrieval"""
    print("=== Testing Settings Retrieval ===")
    
    try:
        lora = SX126X(uart_id=1, freq=868, addr=1000, power=22, rssi=True, air_speed=2400)
        print("\n=== Attempting to get settings ===")
        success = lora.get_settings()
        if success:
            print("Settings retrieved successfully!")
        else:
            print("Failed to retrieve settings - trying alternative method...")
            # Try a different approach
            lora.set_config_mode()
            time.sleep_ms(500)
            lora.uart.write(bytes([0xC1, 0x00, 0x09]))
            time.sleep_ms(1000)
            if lora.uart.any():
                raw_data = lora.uart.read()
                print(f"Raw response: {raw_data}")
                print(f"Raw hex: {[hex(b) for b in raw_data]}")
            lora.set_normal_mode()
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

def test_basic_config():
    """Test basic module configuration"""
    print("=== Testing SX126X Configuration ===")
    
    try:
        # Initialize with basic parameters
        lora = SX126X(
            uart_id=1,          # UART3 on OpenMV RT1062
            freq=868,           # 868 MHz
            addr=1000,          # Node address
            power=22,           # 22 dBm power
            rssi=True,          # Enable RSSI
            air_speed=2400      # 2400 bps air speed
        )
        
        print("\n=== Getting Current Settings ===")
        lora.get_settings()
        
        print("\n=== Testing Send ===")
        lora.send_data("Hello LoRa World!")
        
        print("\n=== Listening for 5 seconds ===")
        for i in range(50):  # Listen for 5 seconds
            received = lora.receive_data()
            if received:
                print("Received data:", received)
            time.sleep_ms(100)
            
        print("Test completed!")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

def test_transmission():
    """Test continuous transmission and monitoring"""
    print("=== Testing LoRa Transmission ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=22, rssi=True, air_speed=2400)
        
        print("\n=== Continuous Send/Listen Test ===")
        print("Sending messages every 2 seconds, listening in between...")
        print("Press Ctrl+C to stop\n")
        
        counter = 0
        
        while True:
            counter += 1
            
            # Send a test message
            message = f"Test message #{counter}"
            print(f"[TX] Sending: {message}")
            lora.send_data(message)
            
            # Listen for responses for 2 seconds
            print("[RX] Listening...")
            received_any = False
            
            for i in range(20):  # 2 seconds of listening
                received = lora.receive_data()
                if received:
                    received_any = True
                    print(f"[RX] *** RECEIVED: {received} ***")
                time.sleep_ms(100)
            
            if not received_any:
                print("[RX] No data received")
            
            print("-" * 40)
            time.sleep_ms(1000)  # Wait 1 second before next transmission
            
    except KeyboardInterrupt:
        print("\n[INFO] Test stopped by user")
    except Exception as e:
        print(f"[ERROR] Transmission test failed: {e}")

def test_receive_only():
    """Test receive-only mode for monitoring"""
    print("=== Testing Receive Only Mode ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=22, rssi=True, air_speed=2400)
        
        print("\n=== Monitoring for LoRa Messages ===")
        print("Listening for incoming messages...")
        print("Press Ctrl+C to stop\n")
        
        while True:
            received = lora.receive_data()
            if received:
                print(f"[RX] *** MESSAGE RECEIVED ***")
                print(f"    From Address: {received['addr']}")
                print(f"    Frequency: {received['freq'] + lora.start_freq}.125 MHz")
                print(f"    Data: {received['data']}")
                print(f"    Time: {time.ticks_ms()}")
                print()
            
            time.sleep_ms(50)  # Check every 50ms
            
    except KeyboardInterrupt:
        print("\n[INFO] Monitoring stopped by user")
    except Exception as e:
        print(f"[ERROR] Receive test failed: {e}")

def diagnose_communication():
    """Diagnose LoRa communication issues"""
    print("=== LoRa Communication Diagnostics ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=22, rssi=True, air_speed=2400)
        
        print("\n1. Checking module configuration...")
        lora.get_settings()
        
        print("\n2. Testing different addressing modes...")
        
        # Test broadcast mode (address 0xFFFF)
        print("--- Testing Broadcast Mode ---")
        lora.configure_for_broadcast()
        
        for i in range(3):
            message = f"Broadcast test #{i+1}"
            print(f"[TX] Broadcasting: {message}")
            lora.send_data(message)
            
            # Listen for responses
            for j in range(15):  # 1.5 seconds
                received = lora.receive_data()
                if received:
                    print(f"[RX] *** RECEIVED: {received} ***")
                time.sleep_ms(100)
            
            time.sleep_ms(1000)
        
        print("\n3. Testing with different power levels...")
        # Test lower power to reduce interference
        print("--- Testing with 10dBm power ---")
        lora_low = SX126X(uart_id=3, freq=868, addr=1000, power=10, rssi=True, air_speed=2400)
        
        for i in range(2):
            message = f"Low power test #{i+1}"
            print(f"[TX] Low power: {message}")
            lora_low.send_data(message)
            time.sleep_ms(2000)
            
    except Exception as e:
        print(f"[ERROR] Diagnostic failed: {e}")

def configure_for_broadcast(self):
    """Configure module for broadcast communication"""
    print("[INFO] Configuring for broadcast mode...")
    self.set_config_mode()
    
    # Configuration for broadcast (address 0xFFFF)
    config_reg = [
        0xC2,           # Header - volatile config
        0x00, 0x09,     # Address and length
        0xFF,           # Address high byte (broadcast)
        0xFF,           # Address low byte (broadcast)  
        0x00,           # Network ID
        0x62,           # UART 9600 + air speed 2400
        0x20,           # Buffer 240 + power 22dBm + noise enable
        0x12,           # Frequency offset (868.125 MHz)
        0xC3,           # Mode + RSSI enable
        0x00,           # Encryption key high
        0x00            # Encryption key low
    ]
    
    self.uart.write(bytes(config_reg))
    time.sleep_ms(300)
    
    if self.uart.any():
        response = self.uart.read()
        if response and len(response) > 0 and response[0] == 0xC1:
            print("[SUCCESS] Broadcast mode configured!")
        else:
            print(f"[WARNING] Unexpected broadcast config response: {response}")
    
    self.set_normal_mode()

# Add the method to the SX126X class
SX126X.configure_for_broadcast = configure_for_broadcast

if __name__ == "__main__":
    test_basic_config()