# Fast Cellular Internet Module for SIM7600X
# Production-ready version without debugging overhead

import time
import json
from machine import SPI, Pin

class SC16IS750:
    """Fast SC16IS750 UART bridge driver"""
    
    def __init__(self, spi_bus=1, cs_pin="P3", baudrate=115200):
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        self.spi = SPI(spi_bus, baudrate=500000, polarity=0, phase=0)
        self._init_uart(baudrate)
        
    def _init_uart(self, baudrate):
        # Reset
        reg = self._read_register(0x0E)
        self._write_register(0x0E, reg | 0x08)
        time.sleep_ms(100)
        
        # Set baud rate
        divisor = int(14745600 // (baudrate * 16))
        self._write_register(0x03, 0x80)
        self._write_register(0x00, divisor & 0xFF)
        self._write_register(0x01, divisor >> 8)
        self._write_register(0x03, 0x03)
        
        # Configure UART
        self._write_register(0x02, 0x07)
        self._write_register(0x01, 0x00)
        self._write_register(0x04, 0x00)
        time.sleep_ms(50)
        
        # Clear buffer
        while self._read_register(0x09) > 0:
            self._read_register(0x00)
    
    def _write_register(self, reg, val):
        self.cs.value(0)
        time.sleep_us(5)
        self.spi.write(bytearray([reg << 3]))
        self.spi.write(bytearray([val]))
        time.sleep_us(5)
        self.cs.value(1)
        time.sleep_us(20)
        
    def _read_register(self, reg):
        self.cs.value(0)
        time.sleep_us(5)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        result = self.spi.read(1)[0]
        time.sleep_us(5)
        self.cs.value(1)
        time.sleep_us(20)
        return result
        
    def write(self, data):
        for char in data:
            timeout = 500
            while timeout > 0 and (self._read_register(0x05) & 0x20) == 0:
                time.sleep_us(5)
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
                time.sleep_ms(5)
                
        return data.strip()

class FastCellularInternet:
    """Fast cellular internet connection without debug overhead"""
    
    def __init__(self, apn="airtelgprs"):
        self.uart = SC16IS750()
        self.apn = apn
        self.connected = False
        self.ip_address = None
        self.http_initialized = False
        
    def _send_at(self, command, timeout_ms=3000, expect="OK"):
        # Clear buffer
        self.uart.read(50)
        
        # Send command
        if command:
            self.uart.write(command + "\r\n")
        time.sleep_ms(100)
        
        # Get response
        response = self.uart.read(timeout_ms)
        success = expect in response if expect else True
        return success, response
    
    def _send_data_raw(self, data):
        self.uart.write(data)
        time.sleep_ms(len(data))
        response = self.uart.read(2000)
        return "OK" in response
        
    def connect(self):
        """Fast connection without debug output"""
        # Test AT
        success, _ = self._send_at("AT", timeout_ms=1000)
        if not success:
            return False
        
        # Setup
        self._send_at("ATE0")
        
        # Check SIM
        success, response = self._send_at("AT+CPIN?", timeout_ms=3000)
        if "READY" not in response:
            return False
        
        # Set network mode
        self._send_at("AT+CNMP=38")
        
        # Wait for registration (quick check)
        for _ in range(20):
            success, response = self._send_at("AT+CREG?")
            if "+CREG:" in response and (",1" in response or ",5" in response):
                break
            time.sleep_ms(500)
        else:
            return False
        
        # Set APN and connect
        self._send_at(f'AT+CGDCONT=1,"IP","{self.apn}"')
        success, response = self._send_at("AT+CGACT=1,1", timeout_ms=15000)
        if not success:
            return False
        
        # Get IP
        success, response = self._send_at("AT+CGPADDR=1")
        if "+CGPADDR:" in response:
            try:
                ip_part = response.split("+CGPADDR:")[1]
                self.ip_address = ip_part.split(",")[1].strip().strip('"')
                if self.ip_address and self.ip_address != "0.0.0.0":
                    self.connected = True
                    return True
            except:
                pass
                
        return False
    
    def _init_http_client(self):
        if self.http_initialized:
            return True
            
        self._send_at("AT+HTTPTERM")
        time.sleep_ms(200)
        
        success, response = self._send_at("AT+HTTPINIT")
        if not success:
            return False
        
        self._send_at('AT+HTTPPARA="CID",1')
        self._send_at('AT+HTTPPARA="REDIR",1')
        
        self.http_initialized = True
        return True
    
    def http_post(self, url, data, headers=None):
        """Fast HTTP POST"""
        if not self._init_http_client():
            return None
        
        try:
            # Set URL
            success, response = self._send_at(f'AT+HTTPPARA="URL","{url}"', timeout_ms=3000)
            if not success:
                return None
            
            # Set content type
            content_type = headers.get("Content-Type", "application/json") if headers else "application/json"
            self._send_at(f'AT+HTTPPARA="CONTENT","{content_type}"')
            
            # Prepare data
            data_to_send = data if isinstance(data, str) else str(data)
            data_length = len(data_to_send)
            
            # Upload data
            success, response = self._send_at(f"AT+HTTPDATA={data_length},15000", timeout_ms=3000)
            
            if "DOWNLOAD" in response:
                upload_success = self._send_data_raw(data_to_send)
                
                if upload_success:
                    # Execute POST
                    success, response = self._send_at("AT+HTTPACTION=1", timeout_ms=20000)
                    
                    if success:
                        time.sleep_ms(2000)
                        
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
                            except:
                                pass
                        
                        # Read response if available
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
                            'success': status_code == 200
                        }
            
            return None
                
        except Exception as e:
            return None
    
    def disconnect(self):
        if self.connected:
            if self.http_initialized:
                self._send_at("AT+HTTPTERM")
                self.http_initialized = False
            self._send_at("AT+CGACT=0,1")
            self.connected = False
            self.ip_address = None
            
    def isconnected(self):
        return self.connected

class CellularRequests:
    """Fast requests interface"""
    
    def __init__(self, internet):
        self.internet = internet
        
    def post(self, url, data=None, headers=None):
        if not self.internet.connected:
            raise Exception("Not connected")
            
        result = self.internet.http_post(url, data, headers)
        
        class Response:
            def __init__(self, result):
                if result:
                    self.status_code = result['status_code']
                    self.text = result['text']
                    self.content = self.text.encode('utf-8')
                else:
                    self.status_code = 0
                    self.text = "Failed"
                    self.content = b"Failed"
                self.headers = {}
        
        return Response(result)

def main():
    """Fast main function for testing"""
    
    # Configuration
    URL = "https://n8n.vyomos.org/webhook/watchmen-detect"
    
    print("Connecting...")
    cellular = FastCellularInternet(apn="airtelgprs")
    
    if not cellular.connect():
        print("Connection failed!")
        return
        
    print(f"Connected! IP: {cellular.ip_address}")
    
    # Create requests
    requests = CellularRequests(cellular)
    
    # Send webhook data
    print("Sending webhook...")
    
    payload = {
        "machine_id": 228,
        "message_type": "event",
        "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII"
    }
    
    json_payload = json.dumps(payload)
    headers = {"Content-Type": "application/json"}
    
    try:
        r = requests.post(URL, data=json_payload, headers=headers)
        
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        
        if r.status_code == 200:
            print("✓ Success!")
        else:
            print("⚠ Warning: Non-200 status")
            
    except Exception as e:
        print(f"Error: {e}")
        
    cellular.disconnect()
    print("Done.")

# For importing in other modules
def create_cellular_connection(apn="airtelgprs"):
    """
    Simple function to create cellular internet connection
    
    Usage:
        from cellular_internet import create_cellular_connection
        internet = create_cellular_connection()
        if internet.connect():
            # Use internet connection
            pass
    """
    return FastCellularInternet(apn)

if __name__ == "__main__":
    main()