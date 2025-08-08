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
    
    def send_data(self, data, target_addr=None):
        """Send data via LoRa with proper packet formatting"""
        self.set_normal_mode()
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Use target address or broadcast if not specified
        if target_addr is None:
            target_addr = 0xFFFF  # Broadcast address
            
        # Create LoRa packet format: target_addr(2 bytes) + channel(1 byte) + data
        packet = bytearray()
        packet.append((target_addr >> 8) & 0xFF)  # High byte of target address
        packet.append(target_addr & 0xFF)         # Low byte of target address  
        packet.append(self.freq_offset)           # Frequency channel
        packet.extend(data)                       # Actual data
        
        print(f"[INFO] Sending {len(data)} bytes to addr {target_addr}: {data}")
        print(f"[DEBUG] Packet format: {[hex(b) for b in packet]}")
        self.uart.write(bytes(packet))
        time.sleep_ms(100)
    
    def receive_data(self):
        """Check for received data with improved parsing"""
        if self.uart.any():
            time.sleep_ms(50)  # Wait for complete packet
            data = self.uart.read()
            
            if data and len(data) >= 3:
                print(f"[DEBUG] Raw received: {[hex(b) for b in data]} (len: {len(data)})")
                
                # Parse LoRa packet format: sender_addr(2) + freq(1) + payload + [rssi]
                sender_addr = (data[0] << 8) | data[1]
                freq_info = data[2]
                
                # Check if this is our own transmission (ignore)
                if sender_addr == self.addr:
                    print("[DEBUG] Ignoring own transmission")
                    return None
                
                payload = data[3:]
                rssi_val = None
                
                # Check for RSSI byte at the end
                if self.rssi and len(payload) > 0:
                    # RSSI is typically the last byte
                    rssi_val = 256 - payload[-1] if payload[-1] > 128 else None
                    if rssi_val:
                        payload = payload[:-1]
                
                try:
                    # Try to decode as text
                    decoded_payload = payload.decode('utf-8')
                    print(f"[RX] From addr {sender_addr}, freq {freq_info + self.start_freq}.125 MHz")
                    print(f"[RX] Data: {decoded_payload}")
                    if rssi_val:
                        print(f"[RX] RSSI: -{rssi_val} dBm")
                except:
                    # Keep as bytes if decode fails
                    decoded_payload = payload
                    print(f"[RX] From addr {sender_addr}, freq {freq_info + self.start_freq}.125 MHz")
                    print(f"[RX] Data (bytes): {payload}")
                    if rssi_val:
                        print(f"[RX] RSSI: -{rssi_val} dBm")
                    
                return {
                    'addr': sender_addr, 
                    'freq': freq_info, 
                    'data': decoded_payload,
                    'rssi': rssi_val,
                    'raw': data
                }
            else:
                print(f"[DEBUG] Short packet received: {[hex(b) for b in data] if data else 'None'}")
        
        return None

# Test Functions
def test_basic_config():
    """Test basic module configuration"""
    print("=== Testing SX126X Configuration ===")
    
    try:
        # Initialize with basic parameters
        lora = SX126X(
            uart_id=3,          # UART3 on OpenMV RT1062
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

def test_fixed_broadcast():
    """Fixed broadcast test with proper packet formatting"""
    print("=== Fixed Broadcast Test ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=22, rssi=True, air_speed=2400)
        
        print("Starting broadcast test with proper packet formatting...")
        print("Run this on both devices simultaneously")
        print("Press Ctrl+C to stop\n")
        
        counter = 0
        while True:
            counter += 1
            
            # Send broadcast message with proper formatting
            message = f"OpenMV broadcast #{counter}"
            print(f"[TX] Broadcasting: {message}")
            lora.send_data(message, target_addr=0xFFFF)  # Broadcast address
            
            # Listen for broadcasts from other devices
            print("[RX] Listening for other broadcasts...")
            received_any = False
            
            for i in range(25):  # Listen for 2.5 seconds
                received = lora.receive_data()
                if received:
                    received_any = True
                    print(f"[RX] *** BROADCAST RECEIVED: {received} ***")
                time.sleep_ms(100)
            
            if not received_any:
                print("[RX] No broadcasts received")
            
            print("-" * 50)
            time.sleep_ms(1500)  # Wait 1.5 seconds before next broadcast
            
    except KeyboardInterrupt:
        print("\nBroadcast test stopped")
    except Exception as e:
        print(f"[ERROR] Broadcast test failed: {e}")

def test_device_a():
    """Run this on Device A - sends messages and listens"""
    print("=== Device A: Sender/Receiver ===")
    
    try:
        # Configure as Device A with address 1001
        lora = SX126X(uart_id=3, freq=868, addr=1001, power=22, rssi=True, air_speed=2400)
        
        print("Device A ready. Starting communication test...")
        print("Make sure Device B is running test_device_b()")
        print("Press Ctrl+C to stop\n")
        
        counter = 0
        while True:
            counter += 1
            
            # Send message to Device B (address 1002)
            message = f"A->B: Hello from Device A #{counter}"
            print(f"[TX] Sending to Device B: {message}")
            lora.send_data(message, target_addr=1002)
            
            # Listen for response from Device B
            print("[RX] Listening for Device B response...")
            received_response = False
            
            for i in range(30):  # Listen for 3 seconds
                received = lora.receive_data()
                if received:
                    print(f"[RX] *** RECEIVED FROM DEVICE B: {received} ***")
                    received_response = True
                time.sleep_ms(100)
            
            if not received_response:
                print("[RX] No response from Device B")
            
            print("-" * 50)
            time.sleep_ms(2000)  # Wait 2 seconds before next message
            
    except KeyboardInterrupt:
        print("\nDevice A stopped")
    except Exception as e:
        print(f"[ERROR] Device A failed: {e}")

def test_device_b():
    """Run this on Device B - receives messages and responds"""
    print("=== Device B: Receiver/Responder ===")
    
    try:
        # Configure as Device B with address 1002
        lora = SX126X(uart_id=3, freq=868, addr=1002, power=22, rssi=True, air_speed=2400)
        
        print("Device B ready. Listening for Device A...")
        print("Make sure Device A is running test_device_a()")
        print("Press Ctrl+C to stop\n")
        
        response_counter = 0
        
        while True:
            received = lora.receive_data()
            if received:
                response_counter += 1
                print(f"[RX] *** RECEIVED FROM DEVICE A: {received} ***")
                
                # Send response back to Device A (address 1001)
                response_msg = f"B->A: Response #{response_counter} - Got your message!"
                print(f"[TX] Sending response to Device A: {response_msg}")
                lora.send_data(response_msg, target_addr=1001)
                
                print("-" * 50)
            
            time.sleep_ms(50)  # Check every 50ms
            
    except KeyboardInterrupt:
        print("\nDevice B stopped")
    except Exception as e:
        print(f"[ERROR] Device B failed: {e}")

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
                if received['rssi']:
                    print(f"    RSSI: -{received['rssi']} dBm")
            def test_simple_transparent():
    """Test simple transparent communication - no packet formatting"""
    print("=== Simple Transparent Mode Test ===")
    print("This bypasses all packet formatting for basic RF test")
    
    try:
        # Create module with lower power to avoid interference
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=13, rssi=True, air_speed=2400)
        
        print("Setting transparent mode (M0=0, M1=0)...")
        lora.M0.value(0)
        lora.M1.value(0)
        time.sleep_ms(500)
        
        print("Starting transparent communication test...")
        print("This should work even without proper packet formatting\n")
        
        counter = 0
        while True:
            counter += 1
            
            # Send simple string directly
            message = f"Simple{counter}"
            print(f"[TX] Sending raw: {message}")
            lora.uart.write(message.encode())
            
            # Listen for any incoming data
            received_any = False
            for i in range(30):  # 3 seconds
                if lora.uart.any():
                    data = lora.uart.read()
                    if data:
                        try:
                            decoded = data.decode('utf-8')
                            print(f"[RX] *** RECEIVED RAW: {decoded} ***")
                        except:
                            print(f"[RX] *** RECEIVED BYTES: {data} ***")
                        received_any = True
                time.sleep_ms(100)
            
            if not received_any:
                print("[RX] No data received")
            
            print("-" * 30)
            time.sleep_ms(2000)
            
    except KeyboardInterrupt:
        print("\nTransparent test stopped")
    except Exception as e:
        print(f"[ERROR] Transparent test failed: {e}")

def test_loopback_check():
    """Test if module can hear its own transmission (loopback test)"""
    print("=== Loopback Test (Self-Reception Check) ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=10, rssi=True, air_speed=2400)
        
        print("Testing if module can receive its own transmissions...")
        print("(This would indicate RF transmission is working)\n")
        
        for i in range(5):
            message = f"Loopback{i+1}"
            print(f"[TX] Sending: {message}")
            
            # Send message
            lora.send_data(message)
            
            # Immediately listen for our own signal
            time.sleep_ms(50)  # Small delay
            
            for j in range(20):  # 2 seconds
                received = lora.receive_data()
                if received:
                    print(f"[RX] *** LOOPBACK DETECTED: {received} ***")
                    print("^ This means RF transmission is working!")
                time.sleep_ms(100)
            
            time.sleep_ms(1000)
        
        print("Loopback test completed.")
        print("If you saw loopback messages, RF is working - check other device.")
        print("If no loopback, check antenna connections.")
        
    except Exception as e:
        print(f"[ERROR] Loopback test failed: {e}")

def test_hardware_check():
    """Check hardware connections and basic functionality"""
    print("=== Hardware Check ===")
    
    try:
        print("1. Testing GPIO pin control...")
        m0 = Pin('P6', Pin.OUT)
        m1 = Pin('P7', Pin.OUT)
        
        print("Testing M0 pin...")
        m0.value(0)
        print(f"M0 set to 0: {m0.value()}")
        m0.value(1) 
        print(f"M0 set to 1: {m0.value()}")
        
        print("Testing M1 pin...")
        m1.value(0)
        print(f"M1 set to 0: {m1.value()}")
        m1.value(1)
        print(f"M1 set to 1: {m1.value()}")
        
        print("\n2. Testing UART communication...")
        uart = UART(3, baudrate=9600, bits=8, parity=None, stop=1, timeout=1000)
        
        print("UART initialized successfully")
        
        # Test configuration mode
        print("\n3. Testing module response...")
        m0.value(0)
        m1.value(1)
        time.sleep_ms(300)
        
        uart.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(500)
        
        if uart.any():
            response = uart.read()
            print(f"Module responded: {[hex(b) for b in response]}")
            if response[0] == 0xC1:
                print("✅ Module communication working!")
            else:
                print("❌ Unexpected response")
        else:
            print("❌ No response from module - check connections")
        
        # Return to normal mode
        m0.value(0)
        m1.value(0)
        uart.deinit()
        
    except Exception as e:
        print(f"[ERROR] Hardware check failed: {e}")

def quick_fixes():
    """Quick troubleshooting guide"""
    print("=== Quick Troubleshooting Guide ===")
    print()
    print("If modules are not receiving each other:")
    print()
    print("1. ANTENNA CHECK (Most Common Issue):")
    print("   - Both modules MUST have antennas connected")
    print("   - Use 868MHz antennas (not WiFi antennas)")
    print("   - Check antenna connections are tight")
    print()
    print("2. DISTANCE & ENVIRONMENT:")
    print("   - Start with modules 0.5-1 meter apart")
    print("   - Move away from computers, WiFi routers")
    print("   - Test in open area if possible")
    print()
    print("3. POWER SUPPLY:")
    print("   - Ensure stable 3.3V power")
    print("   - Check for voltage drops during transmission")
    print()
    print("4. HARDWARE CONNECTIONS:")
    print("   - M0 → P6, M1 → P7")
    print("   - UART TX/RX not swapped")
    print("   - Good ground connections")
    print()
    print("5. TRY THESE TESTS:")
    print("   test_hardware_check()    - Basic hardware test")
    print("   test_simple_transparent() - Bypass packet formatting") 
    print("   test_loopback_check()    - Test self-reception")
    print("   diagnose_reception()     - Full diagnostic")
    print()
    print("6. LAST RESORT:")
    print("   - Try different frequency (e.g., freq=915)")
    print("   - Lower power (power=10)")
    print("   - Different air speed (air_speed=1200)")
    print()
            
            time.sleep_ms(50)  # Check every 50ms
            
    except KeyboardInterrupt:
        print("\n[INFO] Monitoring stopped by user")
    except Exception as e:
        print(f"[ERROR] Receive test failed: {e}")

def diagnose_reception():
    """Diagnose why modules aren't receiving"""
    print("=== Reception Diagnostics ===")
    
    try:
        lora = SX126X(uart_id=3, freq=868, addr=1000, power=17, rssi=True, air_speed=2400)
        
        print("\n1. Testing module mode stability...")
        for i in range(5):
            print(f"Mode check {i+1}: M0={lora.M0.value()}, M1={lora.M1.value()}")
            time.sleep_ms(200)
        
        print("\n2. Testing with different configurations...")
        
        # Test with transparent transmission mode
        print("--- Testing Transparent Mode ---")
        lora.set_transparent_mode()
        
        for i in range(3):
            message = f"Transparent test {i+1}"
            print(f"[TX] Transparent: {message}")
            # Send raw data without packet format in transparent mode
            lora.uart.write(message.encode())
            
            # Listen
            for j in range(15):
                if lora.uart.any():
                    data = lora.uart.read()
                    print(f"[RX] Raw received: {data}")
                time.sleep_ms(100)
            time.sleep_ms(1000)
        
        print("\n3. Testing with different power levels...")
        for power in [10, 17]:
            print(f"--- Testing {power}dBm power ---")
            lora_test = SX126X(uart_id=3, freq=868, addr=1000, power=power, rssi=True, air_speed=2400)
            
            message = f"Power {power}dBm test"
            print(f"[TX] {message}")
            lora_test.send_data(message)
            
            for j in range(10):
                received = lora_test.receive_data()
                if received:
                    print(f"[RX] Received: {received}")
                time.sleep_ms(100)
            time.sleep_ms(1000)
        
        print("\n4. Testing raw UART communication...")
        lora.set_normal_mode()
        
        # Check if UART is working at all
        print("Checking UART buffer...")
        if lora.uart.any():
            data = lora.uart.read()
            print(f"Found data in buffer: {data}")
        else:
            print("UART buffer is empty")
            
    except Exception as e:
        print(f"[ERROR] Diagnostic failed: {e}")

def set_transparent_mode(self):
    """Set module to transparent transmission mode (M0=0, M1=0)"""
    self.M0.value(0)
    self.M1.value(0)
    time.sleep_ms(300)
    print(f"[DEBUG] Transparent mode: M0={self.M0.value()}, M1={self.M1.value()}")

# Add method to class
SX126X.set_transparent_mode = set_transparent_mode

# Quick Start Guide
def quick_start():
    """Quick start guide for testing"""
    print("=== SX126X LoRa Quick Start Guide ===")
    print()
    print("Available test functions:")
    print("1. test_basic_config()      - Test configuration and basic send")
    print("2. test_fixed_broadcast()   - Test broadcast (run on both devices)")
    print("3. test_device_a()          - Device A for peer-to-peer")
    print("4. test_device_b()          - Device B for peer-to-peer") 
    print("5. test_receive_only()      - Listen for any LoRa traffic")
    print("6. test_basic_send_receive() - Simple send/receive test")
    print()
    print("For two-device testing:")
    print("- Run test_fixed_broadcast() on both devices simultaneously")
    print("- Or run test_device_a() on one and test_device_b() on the other")
    print()
    print("Hardware connections:")
    print("- M0 → Pin P6")
    print("- M1 → Pin P7") 
    print("- UART → UART3 (or adjust uart_id parameter)")
    print("- Don't forget antennas!")
    print()

if __name__ == "__main__":
    quick_start()