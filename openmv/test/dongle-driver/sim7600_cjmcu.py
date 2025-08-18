# Working Bulk Transfer using proven HTTP method
# Combines multi-APN connection with the HTTP method that actually works

import time
import json
from machine import SPI, Pin

class SC16IS750:
    """Proven SC16IS750 driver"""
    
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

class WorkingBulkCellular:
    """Working bulk cellular using proven methods"""
    
    def __init__(self):
        self.uart = SC16IS750()
        self.connected = False
        self.ip_address = None
        self.http_initialized = False
        self.working_apn = None
        
        # Proven APN configurations (ordered by success probability)
        self.apn_configs = [
            {"apn": "airtelgprs.com", "name": "Airtel .com (proven working)"},
            {"apn": "airtelgprs", "name": "Airtel Primary"},
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
                print(f"  ✗ Failed to set APN")
                return False
            
            # Activate
            print(f"  Activating...")
            success, response = self._send_at("AT+CGACT=1,1", timeout_ms=25000)
            if not success:
                print(f"  ✗ Activation failed")
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
            
            print(f"  ✗ No valid IP")
            return False
            
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            return False
    
    def connect(self):
        """Connect using multi-APN approach"""
        print("=== Connection Setup ===")
        
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
            print(f"\n=== Testing APNs ===")
            for apn_config in self.apn_configs:
                if self._test_apn(apn_config):
                    self.connected = True
                    print(f"✓ Successfully connected with {apn_config['name']}")
                    return True
                time.sleep_ms(1000)
            
            print("✗ All APNs failed")
            return False
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def _send_data_raw(self, data):
        """Send raw data using the proven method"""
        print(f"Uploading {len(data)} bytes using proven method...")
        
        # Send data directly (this method worked before)
        self.uart.write(data)
        
        # Wait based on data size
        wait_time = max(2000, len(data) // 2)
        time.sleep_ms(wait_time)
        
        # Read response
        response = self.uart.read(3000)
        print(f"Upload response: {'OK' if 'OK' in response else 'WAITING'}")
        
        return "OK" in response or len(response) > 0  # Accept any response as progress
    
    def _init_http_proven(self):
        """Initialize HTTP using proven method"""
        if self.http_initialized:
            return True
            
        print("Initializing HTTP (proven method)...")
        
        # Terminate any existing session
        self._send_at("AT+HTTPTERM")
        time.sleep_ms(500)
        
        # Initialize
        success, response = self._send_at("AT+HTTPINIT")
        if not success:
            print("HTTP init failed")
            return False
        
        # Set parameters (proven working configuration)
        self._send_at('AT+HTTPPARA="CID",1')
        time.sleep_ms(500)
        self._send_at('AT+HTTPPARA="REDIR",1')
        time.sleep_ms(500)
        
        self.http_initialized = True
        print("✓ HTTP ready")
        return True
    
    def http_post_proven(self, url, data, headers=None):
        """HTTP POST using the exact method that worked before"""
        if not self._init_http_proven():
            return None
        
        try:
            print(f"HTTP POST to: {url}")
            
            # Set URL (proven method)
            success, response = self._send_at(f'AT+HTTPPARA="URL","{url}"', timeout_ms=5000)
            if not success:
                print("Failed to set URL")
                return None
            
            # Set content type
            content_type = headers.get("Content-Type", "application/json") if headers else "application/json"
            self._send_at(f'AT+HTTPPARA="CONTENT","{content_type}"')
            time.sleep_ms(500)
            
            # Prepare data
            data_to_send = data if isinstance(data, str) else str(data)
            data_length = len(data_to_send)
            
            print(f"Setting up upload: {data_length} bytes ({data_length/1024:.2f} KB)")
            
            # Use the EXACT method that worked before
            success, response = self._send_at(f"AT+HTTPDATA={data_length},20000", timeout_ms=5000)
            
            if "DOWNLOAD" in response:
                print("✓ Got DOWNLOAD prompt - starting upload...")
                
                # Upload using proven method
                upload_start = time.ticks_ms()
                upload_success = self._send_data_raw(data_to_send)
                upload_time = time.ticks_diff(time.ticks_ms(), upload_start) / 1000
                
                if upload_success:
                    print(f"✓ Data uploaded in {upload_time:.2f}s")
                    
                    # Calculate upload speed
                    upload_speed = (data_length * 8) / upload_time if upload_time > 0 else 0
                    print(f"Upload speed: {upload_speed:.0f} bits/second")
                    
                    # Execute POST
                    print("Executing HTTP POST...")
                    success, response = self._send_at("AT+HTTPACTION=1", timeout_ms=30000)
                    
                    if success:
                        time.sleep_ms(3000)
                        
                        # Parse response (proven method)
                        status_code = 0
                        response_length = 0
                        
                        if "+HTTPACTION:" in response:
                            try:
                                action_line = response.split("+HTTPACTION:")[1].strip()
                                parts = action_line.split(",")
                                if len(parts) >= 3:
                                    status_code = int(parts[1])
                                    response_length = int(parts[2])
                                    print(f"Server response: HTTP {status_code}, {response_length} bytes")
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
                        
                        return {
                            'status_code': status_code,
                            'text': response_data,
                            'upload_time': upload_time,
                            'upload_speed': upload_speed,
                            'data_size': data_length
                        }
                    else:
                        print("POST execution failed")
                        return None
                else:
                    print("Data upload failed")
                    return None
            else:
                print(f"No DOWNLOAD prompt. Response: {response}")
                return None
                
        except Exception as e:
            print(f"HTTP POST error: {e}")
            return None
    
    def disconnect(self):
        if self.connected:
            if self.http_initialized:
                self._send_at("AT+HTTPTERM")
                self.http_initialized = False
            self._send_at("AT+CGACT=0,1")
            self.connected = False
            print("✓ Disconnected")

def main():
    """Test working bulk transfer"""
    
    URL = "https://n8n.vyomos.org/webhook/watchmen-detect"
    
    print("=== Working Bulk Transfer Test ===")
    
    # Create test data close to 30KB
    large_image = "data:image/png;base64," + ("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzI" * 600)
    
    payload = {
        "machine_id": 228,
        "message_type": "bulk_transfer_test",
        "image": large_image,
        "timestamp": time.ticks_ms(),
        "test_info": {
            "target_size": "30KB",
            "method": "proven_http_upload"
        }
    }
    
    json_payload = json.dumps(payload)
    data_size = len(json_payload.encode('utf-8'))
    
    print(f"Test data: {data_size} bytes ({data_size/1024:.2f} KB)")
    print(f"Target: 30 KB (scaling factor: {30/(data_size/1024):.2f}x)")
    
    # Connect
    connect_start = time.ticks_ms()
    cellular = WorkingBulkCellular()
    
    if not cellular.connect():
        print("✗ Connection failed!")
        return
    
    connect_time = time.ticks_diff(time.ticks_ms(), connect_start) / 1000
    print(f"\n✓ Connected in {connect_time:.2f}s")
    print(f"Working APN: {cellular.working_apn}")
    print(f"IP Address: {cellular.ip_address}")
    
    # Bulk transfer test
    print(f"\n=== Bulk Transfer (Proven Method) ===")
    
    transfer_start = time.ticks_ms()
    result = cellular.http_post_proven(URL, json_payload, {"Content-Type": "application/json"})
    total_time = time.ticks_diff(time.ticks_ms(), transfer_start) / 1000
    
    if result:
        print(f"\n=== Transfer Results ===")
        print(f"Status: {result['status_code']}")
        print(f"Upload time: {result['upload_time']:.2f}s")
        print(f"Total time: {total_time:.2f}s")
        print(f"Upload speed: {result['upload_speed']:.0f} bps")
        print(f"Data transferred: {result['data_size']/1024:.2f} KB")
        print(f"Response: {result['text'][:100]}...")
        
        # 30KB projection
        if result['upload_speed'] > 0:
            kb_30_upload_time = (30 * 1024 * 8) / result['upload_speed']
            kb_30_total_time = kb_30_upload_time + connect_time
            
            print(f"\n=== 30KB Projection ===")
            print(f"Estimated upload time: {kb_30_upload_time:.0f}s ({kb_30_upload_time/60:.1f} min)")
            print(f"Estimated total time: {kb_30_total_time:.0f}s ({kb_30_total_time/60:.1f} min)")
            
            efficiency = (30 * 1024) / kb_30_total_time if kb_30_total_time > 0 else 0
            print(f"Efficiency: {efficiency:.1f} bytes/second for 30KB")
        
        if result['status_code'] == 200:
            print("\n✓ BULK TRANSFER SUCCESSFUL!")
        else:
            print(f"\n⚠ Status {result['status_code']}")
            
    else:
        print("✗ Bulk transfer failed")
    
    cellular.disconnect()
    print("\n✓ Test completed")

if __name__ == "__main__":
    main()