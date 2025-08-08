import time
from machine import UART, Pin

class SX126x_Debug:
    def __init__(self, uart_id=1, freq=868, addr=100, m0_pin='P6', m1_pin='P7'):
        print(f"Initializing with address {addr}")

        self.addr = addr
        self.freq = freq

        # Initialize M0 and M1 control pins
        self.M0 = Pin(m0_pin, Pin.OUT)
        self.M1 = Pin(m1_pin, Pin.OUT)

        # Initialize UART
        self.uart = UART(uart_id, baudrate=9600, bits=8, parity=None, stop=1)

        # Simple configuration
        self.configure_module()
        print("Module configured")

    def configure_module(self):
        """Simple configuration"""
        # Enter configuration mode (M0=LOW, M1=HIGH)
        print("Entering config mode...")
        self.M0.value(0)
        self.M1.value(1)
        time.sleep(0.5)

        # Clear buffer
        while self.uart.any():
            self.uart.read()

        # Basic config: [C0 00 09 00 64 00 00 00 3A 43 00 00]
        # This sets address to 100 (0x0064), 868MHz, other defaults
        if self.addr == 100:
            config = [0xC0, 0x00, 0x09, 0x00, 0x64, 0x00, 0x00, 0x00, 0x3A, 0x43, 0x00, 0x00]
        elif self.addr == 200:
            config = [0xC0, 0x00, 0x09, 0x00, 0xC8, 0x00, 0x00, 0x00, 0x3A, 0x43, 0x00, 0x00]
        else:
            # Generic config
            addr_high = (self.addr >> 8) & 0xFF
            addr_low = self.addr & 0xFF
            config = [0xC0, 0x00, 0x09, addr_high, addr_low, 0x00, 0x00, 0x00, 0x3A, 0x43, 0x00, 0x00]

        print(f"Sending config: {[hex(x) for x in config]}")

        for attempt in range(3):
            self.uart.write(bytes(config))
            time.sleep(0.3)

            if self.uart.any():
                time.sleep(0.2)
                response = self.uart.read()
                print(f"Config response: {[hex(x) for x in response] if response else 'None'}")
                if response and response[0] == 0xC1:
                    print("✅ Configuration successful!")
                    break
            else:
                print(f"⚠️ Config attempt {attempt + 1}: No response")

        # Enter transmission mode (M0=LOW, M1=LOW)
        print("Entering transmission mode...")
        self.M0.value(0)
        self.M1.value(0)
        time.sleep(0.5)

    def send_raw(self, data):
        """Send raw bytes"""
        print(f"Sending raw: {[hex(x) for x in data]}")
        self.uart.write(data)
        time.sleep(0.1)

    def send_simple(self, message):
        """Send simple broadcast message"""
        # Format: [target_high] [target_low] [channel] [payload]
        # Broadcast address: 0xFFFF, channel: 58 (868.0 - 850 = 18, but let's try different values)

        if isinstance(message, str):
            payload = message.encode('utf-8')
        else:
            payload = message

        # Try different packet formats
        packet1 = bytes([0xFF, 0xFF, 0x12]) + payload  # Broadcast, channel 18
        packet2 = bytes([0xFF, 0xFF, 0x00]) + payload  # Broadcast, channel 0
        packet3 = payload  # Raw payload only

        print(f"📡 Sending: '{message}'")
        print(f"Packet format 1: {[hex(x) for x in packet1[:6]]}...")
        self.send_raw(packet1)
        time.sleep(1)

    def receive_raw(self):
        """Check for any received data"""
        if self.uart.any():
            time.sleep(0.3)  # Wait for complete message
            data = self.uart.read()
            print(f"📥 Raw received ({len(data)} bytes): {[hex(x) for x in data]}")

            # Try to decode as string
            try:
                # Try different parsing methods
                if len(data) >= 3:
                    # Method 1: Skip first 3 bytes (addr + channel)
                    msg1 = data[3:].decode('utf-8', errors='ignore')
                    print(f"Method 1 (skip 3): '{msg1}'")

                    # Method 2: Parse as documented format
                    if len(data) >= 4:
                        sender = (data[0] << 8) + data[1]
                        channel = data[2]
                        msg2 = data[3:].decode('utf-8', errors='ignore')
                        print(f"Method 2: From {sender}, Ch {channel}: '{msg2}'")

                # Method 3: Try entire message as string
                msg3 = data.decode('utf-8', errors='ignore')
                print(f"Method 3 (full): '{msg3}'")

            except Exception as e:
                print(f"Decode error: {e}")

            return data
        return None

def test_communication():
    """Test basic communication"""
    print("=== SX126x Communication Test ===")

    # Ask for device address
    print("Enter device address (100 for device 1, 200 for device 2):")
    # try:
    #     addr = int(input().strip())
    # except:
    #     addr = 100
    #     print(f"Using default address: {addr}")

    addr = 100

    # Initialize
    lora = SX126x_Debug(addr=addr)

    print(f"\n📡 Device {addr} ready!")
    print("Commands:")
    print("- 's': Send test message")
    print("- 'l': Listen for 10 seconds")
    print("- 'r': Check receive buffer once")
    print("- 't': Send test sequence")
    print("- 'q': Quit")

    message_count = 0

    while True:
        try:
            # Always check for received messages
            lora.receive_raw()

            # print("\nEnter command (s/l/r/t/q): ", end="")
            # cmd = input().strip().lower()
            cmd = 's'

            if cmd == 'q':
                break
            elif cmd == 's':
                message_count += 1
                msg = f"Test message {message_count} from device {addr}"
                lora.send_simple(msg)
            elif cmd == 'l':
                print("Listening for 10 seconds...")
                for i in range(10):
                    lora.receive_raw()
                    time.sleep(1)
                    if i % 2 == 0:
                        print(f"Listening... {10-i}s left")
            elif cmd == 'r':
                lora.receive_raw()
            elif cmd == 't':
                print("Sending test sequence...")
                for i in range(3):
                    msg = f"Seq {i+1} from {addr}"
                    lora.send_simple(msg)
                    time.sleep(2)
                    lora.receive_raw()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def simple_broadcast_test(device_addr=100):
    """Simple broadcast test - just send and listen"""
    print(f"=== Simple Broadcast Test - Device {device_addr} ===")

    lora = SX126x_Debug(addr=device_addr)
    count = 0

    print("Starting broadcast test...")
    print("Will send message every 5 seconds and listen continuously")

    while True:
        try:
            # Check for messages
            lora.receive_raw()

            # Send message every 5 seconds
            time.sleep(5)
            count += 1
            msg = f"Hello from {device_addr} #{count}"
            lora.send_simple(msg)

        except KeyboardInterrupt:
            print("Stopping...")
            break

# Quick test functions
def device_100():
    """Quick start for device 100"""
    simple_broadcast_test(100)

def device_200():
    """Quick start for device 200"""
    simple_broadcast_test(200)

if __name__ == "__main__":
    # Choose test mode
    print("Choose test:")
    print("1. Interactive test")
    print("2. Device 100 broadcast")
    print("3. Device 200 broadcast")

    # choice = input("Enter choice (1/2/3): ").strip()
    choice = 2

    if choice == "2":
        device_100()
    elif choice == "3":
        device_200()
    else:
        test_communication()
