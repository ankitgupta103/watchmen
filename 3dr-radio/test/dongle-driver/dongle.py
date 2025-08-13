# SIM7600X 4G DONGLE Integration with OpenMV RT1062 (Simplified)
# Using machine module for UART communication

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
            return response
        
        self.send_command("AT+HTTPTERM")
        return ""
    
    def http_post(self, url, data):
        """Send HTTP POST request"""
        print(f"POST: {url}")
        print(f"Data: {data}")
        
        self.send_command("AT+HTTPTERM")  # Clean up
        time.sleep(0.5)
        
        self.send_command("AT+HTTPINIT")
        self.send_command('AT+HTTPPARA="CID",1')
        self.send_command(f'AT+HTTPPARA="URL","{url}"')
        self.send_command('AT+HTTPPARA="CONTENT","application/json"')
        
        # Send data
        data_len = len(data)
        resp = self.send_command(f"AT+HTTPDATA={data_len},10000", 3)
        if "DOWNLOAD" in resp:
            # Module is ready to receive data
            self.uart.write(data)
            print(f"Data sent: {data}")
            time.sleep(2)  # Wait for data upload
            
            # Now perform POST action
            resp = self.send_command("AT+HTTPACTION=1", 5)
            if "OK" in resp:
                time.sleep(3)  # Wait for response
                response = self.send_command("AT+HTTPREAD=0,500", 3)
                if "ERROR" in response:
                    response = self.send_command("AT+HTTPHEAD", 2)
                self.send_command("AT+HTTPTERM")
                return response
        
        self.send_command("AT+HTTPTERM")
        return ""

# Simple usage example
def main():
    # Initialize module
    sim = SIM7600X(uart_id=1, baudrate=115200)  # Using UART1
    
    # Connect to network (change APN for your carrier)
    if not sim.init_module(apn="airtelgprs.com"):  # Use "cmnet", "3gnet", etc.
        print("Setup failed!")
        return
    
    # Send GET request
    response = sim.http_get("http://httpbin.org/get")
    print("GET response received")
    
    # Send sensor data via POST
    sensor_data = '{"temperature": 25.6, "humidity": 60.2}'
    response = sim.http_post("http://httpbin.org/post", sensor_data)
    print("POST response received")
    
    print("Done!")

# Hardware connections:
"""
SIM7600X DONGLE → OpenMV RT1062:
- TX → RX (UART1)
- RX → TX (UART1) 
- GND → GND
- Power via USB

Don't forget:
1. Insert 4G SIM card
2. Connect 4G antenna
3. Change APN for your carrier
"""

if __name__ == "__main__":
    main()