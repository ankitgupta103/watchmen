# Production Bulk Cellular Transfer System
# Initializes once, uploads data every 1 minute
# Optimized for reliability and continuous operation

import time
import json
from machine import SPI, Pin
import gc

class SC16IS750:
    """Optimized SC16IS750 driver for production use"""
    
    def __init__(self, spi_bus=1, cs_pin="P3", baudrate=115200):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=500000, polarity=0, phase=0)
        self._init_uart(baudrate)
        
    def _init_uart(self, baudrate):
        reg = self._read_register(0x0E)
        self._write_register(0x0E, reg | 0x08)
        time.sleep_ms(200)
        
        divisor = int(14745600 // (baudrate * 16))
        self._write_register(0x03, 0x80)
        time.sleep_ms(10)
        self._write_register(0x00, divisor & 0xFF)
        self._write_register(0x01, divisor >> 8)
        self._write_register(0x03, 0x03)
        time.sleep_ms(10)
        
        self._write_register(0x02, 0x07)
        self._write_register(0x01, 0x00)
        self._write_register(0x04, 0x00)
        time.sleep_ms(100)
        
        while self._read_register(0x09) > 0:
            self._read_register(0x00)
    
    def _write_register(self, reg, val):
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytearray([reg << 3]))
        time.sleep_us(5)
        self.spi.write(bytearray([val]))
        time.sleep_us(10)
        self.cs.value(1)
        time.sleep_us(50)
        
    def _read_register(self, reg):
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        time.sleep_us(5)
        result = self.spi.read(1)[0]
        time.sleep_us(10)
        self.cs.value(1)
        time.sleep_us(50)
        return result
        
    def write(self, data):
        for char in data:
            timeout = 1000
            while timeout > 0 and (self._read_register(0x05) & 0x20) == 0:
                time.sleep_us(10)
                timeout -= 1
            if timeout > 0:
                self._write_register(0x00, ord(char))
            
    def read(self, timeout_ms=1000):
        data = ""
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self._read_register(0x09) > 0:
                byte_val = self._read_register(0x00)
                if (32 <= byte_val <= 126) or byte_val in [10, 13]:
                    data += chr(byte_val)
            else:
                time.sleep_ms(10)
                
        return data.strip()

class ProductionBulkCellular:
    """Production cellular system - initialize once, use continuously"""
    
    def __init__(self, machine_id=228):
        self.uart = SC16IS750()
        self.machine_id = machine_id
        self.connected = False
        self.ip_address = None
        self.http_initialized = False
        self.working_apn = None
        self.upload_count = 0
        
        # Proven APN configurations (ordered by success probability)
        self.apn_configs = [
            {"apn": "airtelgprs", "name": "Airtel Primary"},
            {"apn": "airtelgprs.com", "name": "Airtel .com"},
            {"apn": "www.airtelgprs.com", "name": "Airtel WWW"},
            {"apn": "internet", "name": "Generic Internet"},
            {"apn": "airtel.in", "name": "Airtel India"}
        ]
        
    def _send_at(self, command, timeout_ms=5000, expect="OK"):
        # Clear buffer
        self.uart.read(100)
        
        # Send command
        if command:
            self.uart.write(command + "\r\n")
        time.sleep_ms(200)
        
        # Get response
        response = self.uart.read(timeout_ms)
        success = expect in response if expect else True
        return success, response
    
    def _test_apn(self, apn_config):
        """Test APN connection"""
        apn = apn_config["apn"]
        name = apn_config["name"]
        
        print(f"Testing {name}: {apn}")
        
        try:
            # Reset connection
            self._send_at("AT+CGACT=0,1")
            time.sleep_ms(2000)
            
            # Set APN
            success, response = self._send_at(f'AT+CGDCONT=1,"IP","{apn}"')
            if not success:
                return False
            
            # Activate
            success, response = self._send_at("AT+CGACT=1,1", timeout_ms=25000)
            if not success:
                return False
            
            # Get IP
            success, response = self._send_at("AT+CGPADDR=1")
            if "+CGPADDR:" in response:
                try:
                    ip_part = response.split("+CGPADDR:")[1]
                    ip_address = ip_part.split(",")[1].strip().strip('"')
                    if ip_address and ip_address != "0.0.0.0":
                        print(f"  ✓ Connected! IP: {ip_address}")
                        self.ip_address = ip_address
                        self.working_apn = apn
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            return False
    
    def initialize(self):
        """One-time initialization - call this at startup"""
        print("=== Production System Initialization ===")
        
        try:
            # Basic setup
            success, _ = self._send_at("AT", timeout_ms=2000)
            if not success:
                print("✗ Modem not responding")
                return False
            
            self._send_at("ATE0")
            
            # Check SIM
            success, response = self._send_at("AT+CPIN?", timeout_ms=5000)
            if "READY" not in response:
                print("✗ SIM card not ready")
                return False
            print("✓ SIM card ready")
                
            # Check signal
            success, response = self._send_at("AT+CSQ")
            if "+CSQ:" in response:
                signal = response.split("+CSQ:")[1].split(",")[0].strip()
                if signal.isdigit() and int(signal) > 0:
                    print(f"✓ Signal strength: {signal}/31")
                    
            # Set network mode
            self._send_at("AT+CNMP=38")
            
            # Wait for registration
            print("Waiting for network registration...")
            for attempt in range(30):
                success, response = self._send_at("AT+CREG?")
                if "+CREG:" in response and (",1" in response or ",5" in response):
                    print("✓ Network registered")
                    break
                time.sleep_ms(1000)
            else:
                print("✗ Registration timeout")
                return False
            
            # Try APNs
            print(f"=== Connecting to Network ===")
            for apn_config in self.apn_configs:
                if self._test_apn(apn_config):
                    self.connected = True
                    print(f"✓ Connected with {apn_config['name']}")
                    break
                time.sleep_ms(1000)
            
            if not self.connected:
                print("✗ All APNs failed")
                return False
            
            # Initialize HTTP
            if not self._init_http():
                return False
            
            print(f"\n✓ SYSTEM READY")
            print(f"APN: {self.working_apn}")
            print(f"IP: {self.ip_address}")
            print(f"Ready for data uploads every 1 minute\n")
            
            return True
            
        except Exception as e:
            print(f"Initialization error: {e}")
            return False
    
    def _init_http(self):
        """Initialize HTTP session"""
        if self.http_initialized:
            return True
            
        print("Initializing HTTP...")
        
        # Terminate any existing session
        self._send_at("AT+HTTPTERM")
        time.sleep_ms(500)
        
        # Initialize
        success, response = self._send_at("AT+HTTPINIT")
        if not success:
            print("HTTP init failed")
            return False
        
        # Set parameters
        self._send_at('AT+HTTPPARA="CID",1')
        time.sleep_ms(500)
        self._send_at('AT+HTTPPARA="REDIR",1')
        time.sleep_ms(500)
        
        self.http_initialized = True
        print("✓ HTTP ready")
        return True
    
    def _send_data_raw(self, data):
        """Send raw data using proven method"""
        self.uart.write(data)
        wait_time = max(2000, len(data) // 2)
        time.sleep_ms(wait_time)
        response = self.uart.read(3000)
        return "OK" in response or len(response) > 0
    
    def upload_data(self, data_payload, url="https://n8n.vyomos.org/webhook/watchmen-detect"):
        """Upload data - call this whenever you need to send data"""
        if not self.connected or not self.http_initialized:
            print("✗ System not initialized")
            return None
        
        try:
            self.upload_count += 1
            print(f"\n=== Upload #{self.upload_count} ===")
            
            # Prepare payload
            if isinstance(data_payload, dict):
                data_payload['upload_id'] = self.upload_count
                data_payload['timestamp'] = time.ticks_ms()
                json_data = json.dumps(data_payload)
            else:
                json_data = str(data_payload)
            
            data_size = len(json_data)
            print(f"Uploading {data_size} bytes ({data_size/1024:.2f} KB)")
            
            # Set URL
            success, response = self._send_at(f'AT+HTTPPARA="URL","{url}"', timeout_ms=5000)
            if not success:
                print("✗ Failed to set URL")
                return None
            
            # Set content type
            self._send_at('AT+HTTPPARA="CONTENT","application/json"')
            time.sleep_ms(500)
            
            # Setup upload
            success, response = self._send_at(f"AT+HTTPDATA={data_size},20000", timeout_ms=5000)
            
            if "DOWNLOAD" in response:
                upload_start = time.ticks_ms()
                upload_success = self._send_data_raw(json_data)
                upload_time = time.ticks_diff(time.ticks_ms(), upload_start) / 1000
                
                if upload_success:
                    print(f"✓ Data uploaded in {upload_time:.2f}s")
                    
                    # Execute POST
                    success, response = self._send_at("AT+HTTPACTION=1", timeout_ms=30000)
                    
                    if success:
                        time.sleep_ms(3000)
                        
                        # Parse response
                        status_code = 0
                        response_length = 0
                        
                        if "+HTTPACTION:" in response:
                            try:
                                action_line = response.split("+HTTPACTION:")[1].strip()
                                parts = action_line.split(",")
                                if len(parts) >= 3:
                                    status_code = int(parts[1])
                                    response_length = int(parts[2])
                                    print(f"Server response: HTTP {status_code}")
                            except:
                                pass
                        
                        # Read response
                        response_data = ""
                        if response_length > 0:
                            success, read_response = self._send_at(f"AT+HTTPREAD=0,{response_length}", timeout_ms=10000)
                            if success and "+HTTPREAD:" in read_response:
                                try:
                                    if "+HTTPREAD: DATA," in read_response:
                                        response_data = read_response.split("+HTTPREAD: DATA,")[1]
                                        if "\n" in response_data:
                                            response_data = response_data.split("\n", 1)[1].strip()
                                except:
                                    pass
                        
                        result = {
                            'status_code': status_code,
                            'text': response_data,
                            'upload_time': upload_time,
                            'data_size': data_size,
                            'upload_id': self.upload_count
                        }
                        
                        if status_code == 200:
                            print(f"✓ SUCCESS: Upload #{self.upload_count}")
                        else:
                            print(f"⚠ HTTP {status_code}: Upload #{self.upload_count}")
                        
                        return result
                    else:
                        print("✗ POST execution failed")
                        return None
                else:
                    print("✗ Data upload failed")
                    return None
            else:
                print(f"✗ No DOWNLOAD prompt")
                return None
                
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    def check_connection(self):
        """Check if connection is still active"""
        try:
            success, response = self._send_at("AT+CGPADDR=1", timeout_ms=3000)
            if "+CGPADDR:" in response and self.ip_address in response:
                return True
            return False
        except:
            return False
    
    def reconnect(self):
        """Reconnect if connection is lost"""
        print("=== Reconnecting ===")
        self.connected = False
        self.http_initialized = False
        return self.initialize()
    
    def shutdown(self):
        """Clean shutdown"""
        if self.http_initialized:
            self._send_at("AT+HTTPTERM")
            self.http_initialized = False
        if self.connected:
            self._send_at("AT+CGACT=0,1")
            self.connected = False
        print("✓ System shutdown")

# Global system instance
cellular_system = None

def generate_sample_data():
    """Generate sample data for testing - replace with your actual data"""
    # Create a sample payload with image data (adjust size as needed)
    sample_image = "data:image/png;base64," + ("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzI" * 600)
    
    payload = {
        "machine_id": 228,
        "message_type": "periodic_data",
        "image": sample_image,
        "sensor_data": {
            "temperature": 25.5,
            "humidity": 60.2,
            "pressure": 1013.25
        },
        "system_info": {
            "memory_free": gc.mem_free(),
            "uptime": time.ticks_ms()
        }
    }
    
    return payload

def main():
    """Production main function - initialize once, upload every 1 minute"""
    global cellular_system
    
    print("=== Production Bulk Cellular System ===")
    print("Initialize once, upload every 1 minute")
    
    # Initialize system
    cellular_system = ProductionBulkCellular(machine_id=228)
    
    if not cellular_system.initialize():
        print("✗ System initialization failed!")
        return
    
    print("✓ System initialized successfully")
    print("Starting 1-minute upload cycle...\n")
    
    upload_interval = 0  # 1 minute in seconds
    last_upload_time = 0
    consecutive_failures = 0
    max_failures = 5
    
    try:
        while True:
            current_time = time.ticks_ms() / 1000
            
            # Check if it's time for next upload
            if current_time - last_upload_time >= upload_interval:
                # Check connection health periodically
                if consecutive_failures > 2:
                    print("Checking connection health...")
                    if not cellular_system.check_connection():
                        print("Connection lost - attempting reconnect...")
                        if cellular_system.reconnect():
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                            print(f"Reconnect failed ({consecutive_failures}/{max_failures})")
                            if consecutive_failures >= max_failures:
                                print("Max failures reached - system restart needed")
                                break
                
                # Generate data to upload (replace with your actual data collection)
                data_to_upload = generate_sample_data()
                
                # Upload data
                result = cellular_system.upload_data(data_to_upload)
                
                if result and result.get('status_code') == 200:
                    consecutive_failures = 0
                    print(f"Next upload in {upload_interval} seconds...")
                else:
                    consecutive_failures += 1
                    print(f"Upload failed ({consecutive_failures}/{max_failures})")
                
                last_upload_time = current_time
                
                # Memory cleanup
                gc.collect()
            
            # Sleep for 1 second before checking again
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n=== Shutting Down ===")
        cellular_system.shutdown()
        print("✓ System stopped")
    except Exception as e:
        print(f"\n=== System Error ===")
        print(f"Error: {e}")
        cellular_system.shutdown()

if __name__ == "__main__":
    main()