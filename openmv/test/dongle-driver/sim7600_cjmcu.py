# This work is licensed under the MIT license.
# Copyright (c) 2013-2023 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE
#
# Final working HTTP POST with SIM7600X cellular connection

import time
import json
from machine import SPI, Pin

class SC16IS750:
    """SC16IS750 UART bridge driver"""
    
    def __init__(self, spi_bus=1, cs_pin="P3", baudrate=115200):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=500000, polarity=0, phase=0)
        self._init_uart(baudrate)
        
    def _init_uart(self, baudrate):
        """Initialize UART for modem communication"""
        # Reset
        reg = self._read_register(0x0E)
        self._write_register(0x0E, reg | 0x08)
        time.sleep_ms(200)
        
        # Set baud rate
        divisor = int(14745600 // (baudrate * 16))
        self._write_register(0x03, 0x80)  # Enable divisor access
        time.sleep_ms(10)
        self._write_register(0x00, divisor & 0xFF)  # DLL
        self._write_register(0x01, divisor >> 8)    # DLH
        self._write_register(0x03, 0x03)  # 8N1
        time.sleep_ms(10)
        
        # Configure UART
        self._write_register(0x02, 0x07)  # Reset & enable FIFO
        self._write_register(0x01, 0x00)  # Disable interrupts
        self._write_register(0x04, 0x00)  # Normal operation
        time.sleep_ms(100)
        
        # Clear buffer
        while self._read_register(0x09) > 0:
            self._read_register(0x00)
    
    def _write_register(self, reg, val):
        """Write to SC16IS750 register"""
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytearray([reg << 3]))
        time.sleep_us(5)
        self.spi.write(bytearray([val]))
        time.sleep_us(10)
        self.cs.value(1)
        time.sleep_us(50)
        
    def _read_register(self, reg):
        """Read from SC16IS750 register"""
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
        """Send data to modem"""
        for char in data:
            # Wait for TX ready
            timeout = 1000
            while timeout > 0 and (self._read_register(0x05) & 0x20) == 0:
                time.sleep_us(10)
                timeout -= 1
            if timeout > 0:
                self._write_register(0x00, ord(char))
            
    def read(self, timeout_ms=1000):
        """Read data from modem"""
        data = ""
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self._read_register(0x09) > 0:  # bytes available
                byte_val = self._read_register(0x00)
                if (32 <= byte_val <= 126) or byte_val in [10, 13]:
                    data += chr(byte_val)
            else:
                time.sleep_ms(10)
                
        return data.strip()

class CellularInternet:
    """
    Cellular internet with redirect handling and proper response reading
    """
    
    def __init__(self, apn="airtelgprs", debug=False):
        self.uart = SC16IS750()
        self.apn = apn
        self.debug = debug
        self.connected = False
        self.ip_address = None
        self.http_initialized = False
        
    def _log(self, message):
        """Log message"""
        print(message)
            
    def _send_at(self, command, timeout_ms=5000, expect="OK"):
        """Send AT command and get response"""
        if command:  # Only log non-empty commands
            self._log(f"→ {command}")
        
        # Clear buffer
        self.uart.read(100)
        
        # Send command
        if command:
            self.uart.write(command + "\r\n")
        time.sleep_ms(200)  # Longer delay for stability
        
        # Get response
        response = self.uart.read(timeout_ms)
        if response:  # Only log non-empty responses
            self._log(f"← {response}")
        
        success = expect in response if expect else True
        return success, response
    
    def _send_data_raw(self, data):
        """Send raw data without AT command formatting"""
        print(f"Sending raw data: {data[:50]}{'...' if len(data) > 50 else ''}")
        
        # Send data directly without \r\n
        self.uart.write(data)
        
        # Wait for data to be transmitted
        time.sleep_ms(len(data) * 2)  # Allow time for transmission
        
        # Wait for response
        response = self.uart.read(3000)
        print(f"Upload response: {response}")
        
        return "OK" in response
        
    def connect(self):
        """Connect to cellular internet"""
        print("Connecting to cellular network...")
        
        try:
            # Test AT communication
            success, _ = self._send_at("AT", timeout_ms=2000)
            if not success:
                print("Modem not responding")
                return False
            
            # Turn off echo
            self._send_at("ATE0")
            
            # Check SIM card
            success, response = self._send_at("AT+CPIN?", timeout_ms=5000)
            if "READY" not in response:
                print("SIM card not ready")
                return False
                
            print("SIM card ready")
                
            # Check signal
            success, response = self._send_at("AT+CSQ")
            if "+CSQ:" in response:
                signal = response.split("+CSQ:")[1].split(",")[0].strip()
                if signal.isdigit() and int(signal) > 0:
                    print(f"Signal strength: {signal}/31")
                    
            # Set network mode
            self._send_at("AT+CNMP=38")  # LTE only
            
            # Wait for network registration
            print("Registering to network...")
            for _ in range(30):
                success, response = self._send_at("AT+CREG?")
                if "+CREG:" in response and (",1" in response or ",5" in response):
                    print("Network registered")
                    break
                time.sleep_ms(1000)
            else:
                print("Network registration timeout")
                return False
                
            # Set APN and connect
            print(f"Connecting with APN: {self.apn}")
            self._send_at(f'AT+CGDCONT=1,"IP","{self.apn}"')
            
            # Activate connection
            success, response = self._send_at("AT+CGACT=1,1", timeout_ms=20000)
            if not success:
                print("Data connection failed")
                return False
                
            # Get IP address
            success, response = self._send_at("AT+CGPADDR=1")
            if "+CGPADDR:" in response:
                try:
                    ip_part = response.split("+CGPADDR:")[1]
                    self.ip_address = ip_part.split(",")[1].strip().strip('"')
                    if self.ip_address and self.ip_address != "0.0.0.0":
                        print(f"Connected! IP: {self.ip_address}")
                        self.connected = True
                        return True
                except:
                    pass
                    
            print("Failed to get IP address")
            return False
            
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def _init_http_client(self):
        """Initialize HTTP client"""
        if self.http_initialized:
            return True
            
        print("Initializing HTTP client...")
        
        # Terminate any existing session
        self._send_at("AT+HTTPTERM")
        time.sleep_ms(500)
        
        # Initialize HTTP service
        success, response = self._send_at("AT+HTTPINIT")
        if not success:
            print("Failed to initialize HTTP service")
            return False
        
        # Set HTTP parameters
        self._send_at('AT+HTTPPARA="CID",1')  # Use PDP context 1
        time.sleep_ms(500)
        
        # Enable redirect following
        self._send_at('AT+HTTPPARA="REDIR",1')  # Follow redirects
        time.sleep_ms(500)
        
        self.http_initialized = True
        print("HTTP client initialized")
        return True
    
    def http_post(self, url, data, headers=None, follow_redirects=True):
        """
        Send HTTP POST with redirect handling and proper response reading
        """
        print(f"HTTP POST to: {url}")
        
        if not self._init_http_client():
            return None
        
        try:
            # Handle HTTPS by trying HTTPS first, then HTTP fallback
            original_url = url
            if url.startswith("https://"):
                print("Trying HTTPS first...")
                # Try HTTPS
                result = self._do_http_post(url, data, headers, use_ssl=True)
                if result and "301" not in str(result) and "302" not in str(result):
                    return result
                
                # If HTTPS fails or redirects, try HTTP
                print("HTTPS failed or redirected, trying HTTP...")
                url = "http://" + url[8:]
            elif not url.startswith("http://"):
                url = "http://" + url
            
            # Try HTTP
            return self._do_http_post(url, data, headers, use_ssl=False)
                
        except Exception as e:
            print(f"HTTP POST error: {e}")
            return None
    
    def _do_http_post(self, url, data, headers, use_ssl=False):
        """Perform the actual HTTP POST"""
        try:
            # Set SSL if needed
            if use_ssl:
                self._send_at('AT+HTTPPARA="SSL",1')
            else:
                self._send_at('AT+HTTPPARA="SSL",0')
            time.sleep_ms(500)
            
            # Set URL
            success, response = self._send_at(f'AT+HTTPPARA="URL","{url}"', timeout_ms=5000)
            if not success:
                print(f"Failed to set URL: {url}")
                return None
            
            # Set content type
            if headers and "Content-Type" in headers:
                content_type = headers["Content-Type"]
            else:
                content_type = "application/json"
                
            self._send_at(f'AT+HTTPPARA="CONTENT","{content_type}"')
            time.sleep_ms(500)
            
            # Prepare data
            if isinstance(data, str):
                data_to_send = data
            else:
                data_to_send = data.decode('utf-8') if hasattr(data, 'decode') else str(data)
                
            data_length = len(data_to_send)
            print(f"Preparing to upload {data_length} bytes")
            
            # Set data length
            upload_timeout = max(20000, data_length * 100)
            success, response = self._send_at(f"AT+HTTPDATA={data_length},{upload_timeout}", timeout_ms=5000)
            
            if "DOWNLOAD" in response:
                print(f"Got DOWNLOAD prompt, uploading data...")
                
                # Send the actual data
                upload_success = self._send_data_raw(data_to_send)
                
                if upload_success:
                    print("✓ Data uploaded successfully")
                    
                    # Execute POST
                    print("Executing HTTP POST...")
                    success, response = self._send_at("AT+HTTPACTION=1", timeout_ms=30000)
                    
                    if success:
                        # Wait for action to complete
                        time.sleep_ms(3000)
                        
                        # Parse the HTTPACTION response to get status
                        status_code = 0
                        response_length = 0
                        
                        if "+HTTPACTION:" in response:
                            try:
                                # Parse: +HTTPACTION: 1,status_code,data_length
                                action_line = response.split("+HTTPACTION:")[1].strip()
                                parts = action_line.split(",")
                                if len(parts) >= 3:
                                    status_code = int(parts[1])
                                    response_length = int(parts[2])
                                    print(f"HTTP Status: {status_code}, Response Length: {response_length} bytes")
                            except Exception as e:
                                print(f"Failed to parse HTTPACTION response: {e}")
                        
                        # Read response if there's data
                        response_data = ""
                        if response_length > 0:
                            print("Reading HTTP response...")
                            
                            # Try different read commands
                            for read_cmd in [f"AT+HTTPREAD=0,{response_length}", "AT+HTTPREAD"]:
                                success, read_response = self._send_at(read_cmd, timeout_ms=15000)
                                if success and "+HTTPREAD:" in read_response:
                                    try:
                                        # Extract response data
                                        if "+HTTPREAD:" in read_response:
                                            # Format: +HTTPREAD: length\r\ndata
                                            parts = read_response.split("+HTTPREAD:")
                                            if len(parts) > 1:
                                                data_part = parts[1]
                                                # Find the actual response content after the length line
                                                if "\n" in data_part:
                                                    response_data = data_part.split("\n", 1)[1].strip()
                                                else:
                                                    response_data = data_part.strip()
                                                break
                                    except Exception as e:
                                        print(f"Failed to parse response: {e}")
                                        
                            if response_data:
                                print("✓ HTTP response received!")
                                print(f"Response preview: {response_data[:200]}...")
                                return f"Status: {status_code}\r\n\r\n{response_data}"
                            else:
                                print("✓ HTTP POST completed but no response data")
                                return f"Status: {status_code}\r\n\r\nHTTP POST completed successfully"
                        else:
                            print("✓ HTTP POST completed (no response body)")
                            return f"Status: {status_code}\r\n\r\nHTTP POST completed successfully"
                    else:
                        print("HTTP POST action failed")
                        return None
                else:
                    print("✗ Data upload failed")
                    return None
            else:
                print(f"Did not receive DOWNLOAD prompt. Response: {response}")
                return None
                
        except Exception as e:
            print(f"HTTP POST execution error: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from cellular internet"""
        if self.connected:
            # Terminate HTTP service
            if self.http_initialized:
                self._send_at("AT+HTTPTERM")
                self.http_initialized = False
            
            # Deactivate PDP context
            self._send_at("AT+CGACT=0,1")
            
            self.connected = False
            self.ip_address = None
            print("Disconnected from cellular network")
            
    def isconnected(self):
        """Check if connected"""
        return self.connected

class CellularRequests:
    """Requests interface for cellular HTTP with proper response handling"""
    
    def __init__(self, internet):
        self.internet = internet
        
    def post(self, url, data=None, headers=None):
        """Send HTTP POST request"""
        if not self.internet.connected:
            raise Exception("Not connected to internet")
            
        response_text = self.internet.http_post(url, data, headers)
        
        # Create response object
        class Response:
            def __init__(self, text):
                self.text = text or "No response"
                self.content = self.text.encode('utf-8')
                self.headers = {}
                
                # Extract status code from response
                if "Status:" in self.text:
                    try:
                        status_line = self.text.split("Status:")[1].split("\n")[0].strip()
                        self.status_code = int(status_line) if status_line.isdigit() else 200
                    except:
                        self.status_code = 200
                else:
                    self.status_code = 200 if text else 0
        
        return Response(response_text)

def main():
    """Main function with working HTTPS/HTTP handling"""
    
    # Configuration - using HTTPS (will auto-fallback to HTTP if needed)
    URL = "https://n8n.vyomos.org/webhook/watchmen-detect"
    
    # Initialize cellular internet
    print("=== Final Working Cellular HTTP Client ===")
    cellular = CellularInternet(apn="airtelgprs", debug=False)
    
    # Connect to cellular network
    if not cellular.connect():
        print("Failed to connect to cellular network!")
        return
        
    print(f"✓ Connected with IP: {cellular.ip_address}")
    
    # Create requests object
    requests = CellularRequests(cellular)
    
    # Test with httpbin first
    print("\n=== Testing with httpbin.org ===")
    
    try:
        test_url = "https://httpbin.org/post"
        test_data = '{"test": "Hello from SIM7600X!"}'
        
        r = requests.post(test_url, data=test_data, headers={"Content-Type": "application/json"})
        
        print(f"Test Status: {r.status_code}")
        if r.status_code == 200:
            print("✓ Basic HTTPS/HTTP POST working!")
            print(f"Response preview: {r.text[:300]}...")
        
    except Exception as e:
        print(f"Test failed: {e}")
    
    # Send to your webhook
    print(f"\n=== Sending to your webhook ===")
    
    # Define the payload
    machine_id = 228
    message_type = "event"
    example_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
    
    payload = {
        "machine_id": machine_id,
        "message_type": message_type,
        "image": example_image,
    }
    
    json_payload = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending POST request to: {URL}")
        r = requests.post(URL, data=json_payload, headers=headers)
        
        print("Status:", r.status_code)
        print("Full Response:")
        print("-" * 50)
        print(r.text)
        print("-" * 50)
        
        if r.status_code == 200:
            print("✓ Webhook POST successful!")
        else:
            print(f"⚠ Webhook returned status {r.status_code}")
            
    except Exception as e:
        print(f"Webhook request failed: {e}")
    
    # Keep connection for more requests
    print("\n✓ Connection ready for more requests")
    cellular.disconnect()

if __name__ == "__main__":
    main()