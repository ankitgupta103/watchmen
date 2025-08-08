# Simple LoRa Communication Script for OpenMV RT1062
# Load this script after configuring your LoRa module

import machine
import time
from machine import Pin, UART

class LoRa:
    def __init__(self, uart_id=1, baudrate=9600):
        """Initialize LoRa for communication only"""
        
        # Initialize UART for communication (no M0/M1 control needed for normal mode)
        print(f"[LoRa] Starting communication on UART{uart_id} at {baudrate} baud")
        self.uart = UART(uart_id, baudrate=baudrate)
        
        # Clear any existing data in buffer
        time.sleep_ms(100)
        if self.uart.any():
            self.uart.read()
            
        print("[LoRa] Ready for communication")
        
    def send(self, message):
        """Send a message"""
        
        if isinstance(message, str):
            data = message.encode('utf-8')
        else:
            data = message
            
        print(f"[SEND] {message}")
        self.uart.write(data)
        time.sleep_ms(50)  # Small delay after sending
        
    def receive(self, timeout_ms=1000):
        """Receive a message with timeout"""
        
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.uart.any():
                time.sleep_ms(100)  # Let complete message arrive
                data = self.uart.read()
                
                if data:
                    try:
                        # Try to decode as text
                        message = data.decode('utf-8', errors='ignore')
                        
                        # Check if last byte might be RSSI (values > 200)
                        if len(data) > 1 and data[-1] > 200:
                            rssi = 256 - data[-1]
                            message = data[:-1].decode('utf-8', errors='ignore')
                            print(f"[RECV] {message} (RSSI: -{rssi}dBm)")
                        else:
                            print(f"[RECV] {message}")
                            
                        return message
                        
                    except:
                        print(f"[RECV] Raw: {[hex(b) for b in data]}")
                        return data
                        
            time.sleep_ms(10)
            
        return None  # Timeout
        
    def listen(self):
        """Listen continuously for messages"""
        
        print("[LoRa] Listening for messages... (Ctrl+C to stop)")
        
        try:
            while True:
                message = self.receive(timeout_ms=2000)
                if not message:
                    print(".", end="")  # Show we're alive
                    
        except KeyboardInterrupt:
            print("\n[LoRa] Stopped listening")
            
    def close(self):
        """Close UART"""
        self.uart.deinit()
        print("[LoRa] Closed")

# Simple test functions

def sender_test():
    """Simple sender - sends messages every 5 seconds"""
    
    print("=== LoRa Sender Test ===")
    lora = LoRa()
    
    counter = 0
    
    try:
        while True:
            message = f"Hello from OpenMV #{counter}"
            lora.send(message)
            counter += 1
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\nSent {counter} messages")
    finally:
        lora.close()

def receiver_test():
    """Simple receiver - listens for messages"""
    
    print("=== LoRa Receiver Test ===")
    lora = LoRa()
    
    try:
        lora.listen()
    finally:
        lora.close()

def ping_test():
    """Send ping and wait for response"""
    
    print("=== LoRa Ping Test ===")
    lora = LoRa()
    
    try:
        for i in range(5):
            ping_msg = f"PING {i+1}"
            
            print(f"Sending: {ping_msg}")
            lora.send(ping_msg)
            
            print("Waiting for response...")
            response = lora.receive(timeout_ms=3000)
            
            if response:
                print(f"Got response: {response}")
            else:
                print("No response")
                
            time.sleep(2)
            
    finally:
        lora.close()

def chat_mode():
    """Interactive chat mode"""
    
    print("=== LoRa Chat Mode ===")
    print("Type messages and press Enter to send")
    print("Ctrl+C to exit")
    
    lora = LoRa()
    
    try:
        while True:
            # Check for incoming messages
            message = lora.receive(timeout_ms=100)
            if message:
                print(f"\n>> {message}")
                
            # Send user input (simplified for OpenMV)
            # Note: OpenMV doesn't have input(), so this is just an example
            # You'll need to modify this based on how you want to input messages
            
    except KeyboardInterrupt:
        print("\nChat ended")
    finally:
        lora.close()

def range_test():
    """Range test - sends numbered messages"""
    
    print("=== LoRa Range Test ===")
    print("Sends numbered messages every 10 seconds")
    
    lora = LoRa()
    counter = 1
    
    try:
        while True:
            timestamp = time.ticks_ms()
            message = f"RANGE_TEST #{counter} Time:{timestamp}"
            
            lora.send(message)
            print(f"Sent message {counter}")
            
            counter += 1
            time.sleep(10)
            
    except KeyboardInterrupt:
        print(f"\nRange test stopped at message {counter-1}")
    finally:
        lora.close()

def echo_test():
    """Echo test - receives messages and echoes them back"""
    
    print("=== LoRa Echo Test ===")
    print("Receives messages and echoes them back")
    
    lora = LoRa()
    
    try:
        while True:
            message = lora.receive(timeout_ms=1000)
            
            if message:
                echo = f"ECHO: {message}"
                print(f"Echoing back: {echo}")
                lora.send(echo)
            else:
                print("Waiting for messages to echo...")
                
    except KeyboardInterrupt:
        print("\nEcho test stopped")
    finally:
        lora.close()

# Main execution - choose your test
if __name__ == "__main__":
    print("LoRa Communication Script for OpenMV RT1062")
    print("\nAvailable tests:")
    print("1. sender_test()     - Send messages every 5 seconds")
    print("2. receiver_test()   - Listen for incoming messages")  
    print("3. ping_test()       - Send ping and wait for response")
    print("4. range_test()      - Send numbered messages for range testing")
    print("5. echo_test()       - Echo back received messages")
    
    print("\nUncomment the test you want to run:")
    
    # Uncomment ONE of these to run:
    
    sender_test()        # Use this to send messages
    # receiver_test()    # Use this to receive messages
    # ping_test()        # Use this to test bidirectional communication
    # range_test()       # Use this for range testing
    # echo_test()        # Use this to echo back received messages

# Quick usage examples:
"""
For two devices:

Device 1 (Sender):
>>> sender_test()

Device 2 (Receiver): 
>>> receiver_test()

Or for bidirectional:

Device 1:
>>> ping_test()

Device 2:
>>> echo_test()
"""