# Bulk Data Cellular Transfer Module for SIM7600X
# Optimized for large data transfers (30KB+)

import time
import json
from machine import SPI, Pin

class BulkSC16IS750:
    """SC16IS750 optimized for bulk data transfer"""
    
    def __init__(self, spi_bus=1, cs_pin="P3", baudrate=460800):  # Higher baud rate
        self.cs = Pin(cs_pin, Pin.OUT)
        self.cs.value(1)
        # Maximum SPI speed
        self.spi = SPI(spi_bus, baudrate=4000000, polarity=0, phase=0)
        self._init_uart(baudrate)
        
    def _init_uart(self, baudrate):
        # Quick reset
        reg = self._read_register(0x0E)
        self._write_register(0x0E, reg | 0x08)
        time.sleep_ms(100)
        
        # Set high baud rate for faster modem communication
        divisor = int(14745600 // (baudrate * 16))
        if divisor < 1:
            divisor = 1
            
        self._write_register(0x03, 0x80)
        self._write_register(0x00, divisor & 0xFF)
        self._write_register(0x01, divisor >> 8)
        self._write_register(0x03, 0x03)
        
        # Enable large FIFO and optimize for bulk transfer
        self._write_register(0x02, 0xC7)  # Enable FIFO with 56-byte trigger
        self._write_register(0x01, 0x00)
        self._write_register(0x04, 0x00)
        time.sleep_ms(50)
        
        # Clear buffer
        while self._read_register(0x09) > 0:
            self._read_register(0x00)
    
    def _write_register(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([reg << 3, val]))
        self.cs.value(1)
        
    def _read_register(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([0x80 | (reg << 3)]))
        result = self.spi.read(1)[0]
        self.cs.value(1)
        return result
        
    def write_bulk(self, data):
        """Optimized bulk write for large data"""
        # Write in larger chunks for efficiency
        chunk_size = 32
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            for char in chunk:
                # Minimal wait for TX ready
                retries = 50
                while retries > 0 and (self._read_register(0x05) & 0x20) == 0:
                    retries -= 1
                if retries > 0:
                    self._write_register(0x00, ord(char))
            # Small delay between chunks
            time.sleep_ms(5)
            
    def read_bulk(self, timeout_ms=1000):
        """Fast bulk read"""
        data = ""
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            available = self._read_register(0x09)
            if available > 0:
                # Read multiple bytes at once
                for _ in range(min(available, 32)):
                    byte_val = self._read_register(0x00)
                    if (32 <= byte_val <= 126) or byte_val in [10, 13]:
                        data += chr(byte_val)
            else:
                time.sleep_ms(1)
                
        return data.strip()

class BulkCellularInternet:
    """Cellular internet optimized for bulk data transfer"""
    
    def __init__(self, apn="airtelgprs"):
        self.uart = BulkSC16IS750()
        self.apn = apn
        self.connected = False
        self.ip_address = None
        self.http_initialized = False
        
    def _send_at_bulk(self, command, timeout_ms=3000, expect="OK"):
        """AT command optimized for bulk operations"""
        self.uart.read_bulk(50)
        
        if command:
            self.uart.write_bulk(command + "\r\n")
        time.sleep_ms(100)
        
        response = self.uart.read_bulk(timeout_ms)
        success = expect in response if expect else True
        return success, response
    
    def _send_data_bulk(self, data):
        """Optimized bulk data transfer"""
        print(f"Uploading {len(data)} bytes in bulk mode...")
        
        # Send data in optimal chunks
        chunk_size = 512  # Larger chunks for bulk transfer
        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            chunk_num = i // chunk_size + 1
            
            print(f"Chunk {chunk_num}/{total_chunks} ({len(chunk)} bytes)")
            self.uart.write_bulk(chunk)
            
            # Dynamic delay based on chunk size
            time.sleep_ms(max(20, len(chunk) // 8))
        
        # Wait for completion with timeout based on data size
        wait_time = max(2000, len(data) // 2)
        response = self.uart.read_bulk(wait_time)
        return "OK" in response
        
    def connect_bulk(self):
        """Fast connection optimized for bulk transfers"""
        # Quick connection sequence
        success, _ = self._send_at_bulk("AT", timeout_ms=1000)
        if not success:
            return False
        
        self._send_at_bulk("ATE0")
        
        success, response = self._send_at_bulk("AT+CPIN?", timeout_ms=2000)
        if "READY" not in response:
            return False
        
        # Set to highest performance network mode
        self._send_at_bulk("AT+CNMP=38")  # LTE only
        
        # Quick registration
        for _ in range(10):
            success, response = self._send_at_bulk("AT+CREG?")
            if "+CREG:" in response and (",1" in response or ",5" in response):
                break
            time.sleep_ms(500)
        else:
            return False
        
        # Fast APN setup
        self._send_at_bulk(f'AT+CGDCONT=1,"IP","{self.apn}"')
        success, response = self._send_at_bulk("AT+CGACT=1,1", timeout_ms=15000)
        if not success:
            return False
        
        # Get IP
        success, response = self._send_at_bulk("AT+CGPADDR=1")
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
    
    def _init_http_bulk(self):
        """HTTP initialization optimized for bulk transfer"""
        if self.http_initialized:
            return True
            
        self._send_at_bulk("AT+HTTPTERM")
        time.sleep_ms(200)
        
        success, response = self._send_at_bulk("AT+HTTPINIT")
        if not success:
            return False
        
        # Bulk transfer optimizations
        self._send_at_bulk('AT+HTTPPARA="CID",1')
        self._send_at_bulk('AT+HTTPPARA="REDIR",1')
        self._send_at_bulk('AT+HTTPPARA="TIMEOUT",120')  # 2-minute timeout for large uploads
        self._send_at_bulk('AT+HTTPPARA="BREAK",30000')  # 30-second break timeout
        self._send_at_bulk('AT+HTTPPARA="BREAKEND",5000')  # 5-second break end timeout
        
        self.http_initialized = True
        return True
    
    def http_post_bulk(self, url, data, headers=None):
        """HTTP POST optimized for bulk data (30KB+)"""
        if not self._init_http_bulk():
            return None
        
        try:
            print(f"Setting up bulk transfer to: {url}")
            
            # Set URL
            success, response = self._send_at_bulk(f'AT+HTTPPARA="URL","{url}"', timeout_ms=3000)
            if not success:
                return None
            
            # Set content type
            content_type = headers.get("Content-Type", "application/json") if headers else "application/json"
            self._send_at_bulk(f'AT+HTTPPARA="CONTENT","{content_type}"')
            
            # Prepare data
            data_to_send = data if isinstance(data, str) else str(data)
            data_length = len(data_to_send)
            
            print(f"Initiating bulk upload: {data_length} bytes")
            
            # Set data length with extended timeout for large data
            upload_timeout = max(60000, data_length * 20)  # Minimum 1 minute
            success, response = self._send_at_bulk(f"AT+HTTPDATA={data_length},{upload_timeout}", timeout_ms=5000)
            
            if "DOWNLOAD" in response:
                print("Received DOWNLOAD prompt, starting bulk upload...")
                
                # Bulk data upload
                upload_success = self._send_data_bulk(data_to_send)
                
                if upload_success:
                    print("✓ Bulk upload completed, executing POST...")
                    
                    # Execute POST with extended timeout
                    success, response = self._send_at_bulk("AT+HTTPACTION=1", timeout_ms=60000)
                    
                    if success:
                        # Wait for large data processing
                        print("Waiting for server response...")
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
                                    print(f"Server response: {status_code}, {response_length} bytes")
                            except:
                                pass
                        
                        # Read response
                        response_data = ""
                        if response_length > 0:
                            success, read_response = self._send_at_bulk(f"AT+HTTPREAD=0,{response_length}", timeout_ms=15000)
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
                    else:
                        print("✗ POST action failed")
                        return None
                else:
                    print("✗ Bulk upload failed")
                    return None
            else:
                print(f"Did not receive DOWNLOAD prompt: {response}")
                return None
                
        except Exception as e:
            print(f"Bulk transfer error: {e}")
            return None
    
    def disconnect_bulk(self):
        """Fast disconnect"""
        if self.connected:
            if self.http_initialized:
                self._send_at_bulk("AT+HTTPTERM")
                self.http_initialized = False
            self._send_at_bulk("AT+CGACT=0,1")
            self.connected = False
            self.ip_address = None
            
    def estimate_transfer_time(self, data_size_kb):
        """Estimate transfer time for given data size"""
        # Based on optimized performance (assuming ~200 bps effective)
        estimated_seconds = (data_size_kb * 1024 * 8) / 200
        return estimated_seconds

class BulkCellularRequests:
    """Requests interface optimized for bulk transfers"""
    
    def __init__(self, internet):
        self.internet = internet
        
    def post(self, url, data=None, headers=None):
        if not self.internet.connected:
            raise Exception("Not connected")
            
        result = self.internet.http_post_bulk(url, data, headers)
        
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
    """Test with 30KB data simulation"""
    
    URL = "https://n8n.vyomos.org/webhook/watchmen-detect"
    
    print("=== Bulk Data Cellular Transfer Test (30KB) ===")
    
    # Create simulated 30KB data
    large_image_data = "data:image/png;base64," + "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzI" * 500  # Simulate large image
    
    payload = {
        "machine_id": 228,
        "message_type": "bulk_data",
        "image": large_image_data,
        "timestamp": time.ticks_ms(),
        "metadata": {
            "device_info": "OpenMV RT1062",
            "connection": "SIM7600X Cellular",
            "data_type": "bulk_transfer_test"
        }
    }
    
    json_payload = json.dumps(payload)
    data_size_bytes = len(json_payload.encode('utf-8'))
    data_size_kb = data_size_bytes / 1024
    
    print(f"Test data size: {data_size_bytes} bytes ({data_size_kb:.2f} KB)")
    
    # Connection
    print("\nConnecting for bulk transfer...")
    connect_start = time.ticks_ms()
    
    cellular = BulkCellularInternet(apn="airtelgprs")
    
    if not cellular.connect_bulk():
        print("Connection failed!")
        return
        
    connect_time = time.ticks_diff(time.ticks_ms(), connect_start)
    print(f"✓ Connected! IP: {cellular.ip_address}")
    print(f"Connection time: {connect_time/1000:.2f} seconds")
    
    # Estimate transfer time
    estimated_time = cellular.estimate_transfer_time(data_size_kb)
    print(f"Estimated transfer time: {estimated_time:.0f} seconds")
    
    # Create bulk requests
    requests = BulkCellularRequests(cellular)
    headers = {"Content-Type": "application/json"}
    
    # Bulk upload test
    print(f"\n=== Starting Bulk Upload ===")
    upload_start = time.ticks_ms()
    
    try:
        r = requests.post(URL, data=json_payload, headers=headers)
        
        upload_time = time.ticks_diff(time.ticks_ms(), upload_start)
        
        print(f"\n=== Bulk Transfer Results ===")
        print(f"Upload time: {upload_time/1000:.2f} seconds")
        
        if upload_time > 0:
            upload_speed_bps = (data_size_bytes * 8) / (upload_time/1000)
            upload_speed_kbps = data_size_kb / (upload_time/1000)
            
            print(f"Bulk upload speed: {upload_speed_bps:.0f} bits/second")
            print(f"Bulk upload speed: {upload_speed_kbps:.3f} KB/second")
            
            # Calculate time for actual 30KB
            actual_30kb_time = (30 * 1024 * 8) / upload_speed_bps if upload_speed_bps > 0 else float('inf')
            print(f"Estimated time for 30KB: {actual_30kb_time:.0f} seconds ({actual_30kb_time/60:.1f} minutes)")
        
        print(f"\nHTTP Status: {r.status_code}")
        print(f"Response: {r.text[:200]}...")
        
        if r.status_code == 200:
            print("✓ Bulk transfer successful!")
        
        # Performance summary
        total_time = connect_time + upload_time
        print(f"\n=== Bulk Performance Summary ===")
        print(f"Total time: {total_time/1000:.2f} seconds")
        print(f"Data transferred: {data_size_kb:.2f} KB")
        print(f"Overall efficiency: {data_size_kb/(total_time/1000):.3f} KB/second")
        
    except Exception as e:
        upload_time = time.ticks_diff(time.ticks_ms(), upload_start)
        print(f"Bulk transfer failed after {upload_time/1000:.2f}s: {e}")
        
    cellular.disconnect_bulk()
    print("\n✓ Bulk transfer test completed.")

if __name__ == "__main__":
    main()