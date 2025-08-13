# SIM7600X 4G DONGLE Integration with OpenMV RT1062 (Simplified)
# Save this file as: sim7600x.py

import time
from machine import UART

class SIM7600X:
    def __init__(self, uart_id=1, baudrate=115200):
        """Initialize SIM7600X module"""
        self.uart = UART(uart_id, baudrate)
        
    def send_command(self, cmd, wait_time=2):
        """Send AT command and get response"""
        self.uart.write(cmd + '\r\n')
        print(f">> {cmd}")
        time.sleep(wait_time)
        
        response = ""
        if self.uart.any():
            raw_data = self.uart.read()
            if raw_data:
                response = raw_data.decode('utf-8')
            print(f"<< {response.strip()}")
        return response
    
    def init_module(self, apn="internet"):
        """Initialize module and connect to network"""
        print("Initializing SIM7600X...")
        
        # Test communication
        self.send_command("AT")
        
        # Check SIM card
        resp = self.send_command("AT+CPIN?")
        if "READY" not in resp:
            print("SIM card not ready!")
            return False
        
        # Wait for network registration
        print("Waiting for network...")
        for i in range(20):
            resp = self.send_command("AT+CREG?", 1)
            if ",1" in resp or ",5" in resp:
                print("Network connected!")
                break
            time.sleep(1)
        else:
            print("Network connection failed!")
            return False
        
        # Setup internet connection
        self.send_command(f'AT+CGDCONT=1,"IP","{apn}"')
        self.send_command("AT+CGACT=1,1", 5)
        
        # Check IP address
        resp = self.send_command("AT+CGPADDR=1")
        if "1," in resp:
            print("Internet connected!")
            return True
        
        print("Internet connection failed!")
        return False
    
    def http_get(self, url):
        """Send HTTP GET request"""
        print(f"GET: {url}")
        
        self.send_command("AT+HTTPTERM")  # Clean up
        time.sleep(0.5)
        
        self.send_command("AT+HTTPINIT")
        self.send_command('AT+HTTPPARA="CID",1')
        self.send_command(f'AT+HTTPPARA="URL","{url}"')
        
        resp = self.send_command("AT+HTTPACTION=0", 5)
        if "OK" in resp:
            # Wait for +HTTPACTION response
            time.sleep(3)
            # Try to read response with length parameter
            response = self.send_command("AT+HTTPREAD=0,500", 3)
            if "ERROR" in response:
                # Try without parameters
                response = self.send_command("AT+HTTPHEAD", 2)
            self.send_command("AT+HTTPTERM")
            return True, response
        
        self.send_command("AT+HTTPTERM")
        return False, ""
    
    def http_post(self, url, data):
        """Send HTTP POST request"""
        print(f"POST: {url}")
        print(f"Data length: {len(data)} bytes")
        
        # Try HTTP instead of HTTPS first
        if url.startswith("https://"):
            print(" HTTPS detected - trying HTTP for better compatibility")
            url = url.replace("https://", "http://")
        
        self.send_command("AT+HTTPTERM")  # Clean up
        time.sleep(0.5)
        
        self.send_command("AT+HTTPINIT")
        self.send_command('AT+HTTPPARA="CID",1')
        self.send_command(f'AT+HTTPPARA="URL","{url}"')
        self.send_command('AT+HTTPPARA="CONTENT","application/json"')
        
        # Enable SSL if needed 
        # if "https" in url:
        #     self.send_command('AT+HTTPPARA="SSLCFG",1')
        
        # Send data in smaller chunks if too large
        data_len = len(data)
        max_chunk = 1024  # Limit chunk size
        
        if data_len > max_chunk:
            print(f" Large payload ({data_len} bytes), consider reducing size")
        
        resp = self.send_command(f"AT+HTTPDATA={data_len},15000", 3)  # Increased timeout
        if "DOWNLOAD" in resp:
            # Module is ready to receive data
            print(f"Uploading {data_len} bytes...")
            
            # Send data in chunks to avoid buffer overflow
            chunk_size = 256
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                self.uart.write(chunk)
                time.sleep(0.1)  # Small delay between chunks
            
            print(f"✓ Data upload completed")
            time.sleep(3)  # Wait for data processing
            
            # Now perform POST action
            print("Sending POST request...")
            resp = self.send_command("AT+HTTPACTION=1", 10)  # Increased timeout
            if "OK" in resp:
                print("Waiting for server response...")
                time.sleep(5)  # Wait longer for response
                
                # Try to get response status first
                status_resp = self.send_command("AT+HTTPSTATUS?", 2)
                print(f"HTTP Status: {status_resp}")
                
                response = self.send_command("AT+HTTPREAD", 3)
                if "ERROR" in response:
                    response = self.send_command("AT+HTTPHEAD", 2)
                
                self.send_command("AT+HTTPTERM")
                return True, response
        
        self.send_command("AT+HTTPTERM")
        return False, ""