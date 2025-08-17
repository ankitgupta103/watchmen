import time
from machine import SPI, Pin

class SX1262:
    """SX1262 LoRa driver for OpenMV RT1062 - FIXED VERSION"""
    
    # Command opcodes
    CMD_SET_STANDBY = 0x80
    CMD_SET_PACKET_TYPE = 0x8A
    CMD_SET_RF_FREQUENCY = 0x86
    CMD_SET_TX_PARAMS = 0x8E
    CMD_SET_MODULATION_PARAMS = 0x8B
    CMD_SET_PACKET_PARAMS = 0x8C
    CMD_SET_DIO_IRQ_PARAMS = 0x08
    CMD_SET_BUFFER_BASE_ADDRESS = 0x8F
    CMD_WRITE_BUFFER = 0x0E
    CMD_SET_TX = 0x83
    CMD_SET_RX = 0x82
    CMD_GET_IRQ_STATUS = 0x12
    CMD_CLEAR_IRQ_STATUS = 0x02
    CMD_READ_BUFFER = 0x1E
    CMD_GET_RX_BUFFER_STATUS = 0x13
    CMD_SET_REGULATOR_MODE = 0x96
    CMD_CALIBRATE = 0x89
    CMD_SET_PA_CONFIG = 0x95
    
    # Packet types
    PACKET_TYPE_LORA = 0x01
    
    # IRQ masks
    IRQ_TX_DONE = 0x0001
    IRQ_RX_DONE = 0x0002
    IRQ_TIMEOUT = 0x0200
    
    def __init__(self, spi_id=1, nss_pin='P3', reset_pin='P6', busy_pin='P7', dio1_pin='P13'):
        """Initialize SX1262 with OpenMV RT1062 pins"""
        # Initialize SPI
        self.spi = SPI(spi_id)
        self.spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
        
        # Initialize control pins
        self.nss = Pin(nss_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        # Initialize pins
        self.nss.on()
        self.reset.on()
        
        # Reset and initialize
        self.hardware_reset()
        self.init_lora()
    
    def hardware_reset(self):
        """Hardware reset of SX1262"""
        self.reset.off()
        time.sleep_ms(10)
        self.reset.on()
        time.sleep_ms(20)
        self.wait_busy()
    
    def wait_busy(self):
        """Wait for BUSY pin to go low"""
        timeout = 10000
        while self.busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        if timeout == 0:
            print("Warning: BUSY timeout")
    
    def spi_write(self, data):
        """Write data via SPI"""
        self.wait_busy()
        self.nss.off()
        if isinstance(data, list):
            data = bytes(data)
        self.spi.write(data)
        self.nss.on()
        time.sleep_ms(1)
    
    def spi_read(self, cmd, length):
        """Read data via SPI"""
        self.wait_busy()
        self.nss.off()
        
        if isinstance(cmd, list):
            cmd = bytes(cmd)
        self.spi.write(cmd)
        
        data = self.spi.read(length, 0x00)
        self.nss.on()
        time.sleep_ms(1)
        return data
    
    def get_status(self):
        """Get device status"""
        try:
            status = self.spi_read([0xC0, 0x00], 1)
            return status[0] if status else 0
        except:
            return 0
    
    def check_device_errors(self, context=""):
        """Check for device errors"""
        try:
            error_data = self.spi_read([0x17, 0x00], 3)
            errors = (error_data[1] << 8) | error_data[2]
            if errors != 0:
                print(f"Device errors {context}: 0x{errors:04X}")
                error_names = []
                if errors & 0x01: error_names.append("RC64K_CALIB_ERR")
                if errors & 0x02: error_names.append("RC13M_CALIB_ERR") 
                if errors & 0x04: error_names.append("PLL_CALIB_ERR")
                if errors & 0x08: error_names.append("ADC_CALIB_ERR")
                if errors & 0x10: error_names.append("IMG_CALIB_ERR")
                if errors & 0x20: error_names.append("XOSC_START_ERR")
                if errors & 0x40: error_names.append("PLL_LOCK_ERR")
                if errors & 0x100: error_names.append("PA_RAMP_ERR")
                print(f"  Specific errors: {', '.join(error_names)}")
                self.spi_write([0x07, 0x00, 0x00])  # Clear errors
        except Exception as e:
            print(f"Error checking device errors: {e}")
    
    def init_lora(self):
        """Initialize LoRa with TCXO"""
        print("Initializing SX1262 with TCXO...")
        
        # STDBY_RC mode
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(50)
        
        # Enable TCXO
        print("Enabling TCXO...")
        self.spi_write([0x97, 0x02, 0x00, 0x00, 0x20])
        time.sleep_ms(100)
        
        # Switch to STDBY_XOSC
        print("Switching to STDBY_XOSC...")
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(200)
        
        # Verify TCXO mode
        status = self.get_status()
        mode = (status >> 4) & 0x7
        if mode != 3:
            print(f"ERROR: TCXO mode failed. Mode: {mode}")
            return False
        print("SUCCESS: TCXO active!")
        
        # Set regulator and calibrate
        self.spi_write([self.CMD_SET_REGULATOR_MODE, 0x00])
        time.sleep_ms(10)
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(500)
        
        # Configure for LoRa
        self.spi_write([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01])
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        
        # Set frequency (868 MHz)
        freq_raw = int((868000000 * 33554432) // 32000000)
        self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                       (freq_raw >> 24) & 0xFF, (freq_raw >> 16) & 0xFF, 
                       (freq_raw >> 8) & 0xFF, freq_raw & 0xFF])
        
        # Set modulation: SF7 BW125 CR4/5 (for faster, more reliable communication)
        self.spi_write([self.CMD_SET_MODULATION_PARAMS, 0x07, 0x04, 0x01, 0x00])
        
        # Set packet params
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x08,  # 8 symbol preamble
                       0x00,        # Explicit header
                       0xFF,        # Max payload
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        
        # Set buffer and power
        self.spi_write([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00])
        self.spi_write([self.CMD_SET_TX_PARAMS, 14, 0x02])  # 14dBm power
        
        # Set IRQ params
        self.spi_write([self.CMD_SET_DIO_IRQ_PARAMS,
                       0x03, 0xFF,  # IRQ mask
                       0x03, 0xFF,  # DIO1 mask
                       0x00, 0x00, 0x00, 0x00])
        
        # Clear IRQs
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        
        print("✓ SX1262 initialized successfully!")
        return True
    
    def send_data(self, data):
        """Send data via LoRa"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"Sending: {data}")
        
        # Ensure standby mode
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(10)
        
        # Clear IRQs
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        
        # Write data to buffer
        cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        self.spi_write(cmd)
        
        # Update packet length
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x08, 0x00, len(data), 0x01, 0x00])
        
        # Set TX mode
        self.spi_write([self.CMD_SET_TX, 0x00, 0x00, 0x00])
        
        # Wait for TX completion
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < 5000:
            if self.dio1.value():
                irq_data = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                irq = (irq_data[1] << 8) | irq_data[2]
                
                if irq & self.IRQ_TX_DONE:
                    print("✓ TX Done!")
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                    return True
                elif irq & self.IRQ_TIMEOUT:
                    print("✗ TX Timeout!")
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                    return False
            time.sleep_ms(10)
        
        print("✗ TX failed")
        return False
    
    def receive_data(self, timeout_ms=10000):
        """Receive data via LoRa - FIXED VERSION"""
        print("Listening...")
        
        # Ensure standby mode
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(10)
        
        # Clear IRQs and errors
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        self.spi_write([0x07, 0x00, 0x00])  # Clear device errors
        
        # Set RX mode
        timeout = int(timeout_ms * 1000 // 15.625)
        if timeout > 0xFFFFFF:
            timeout = 0xFFFFFF
        
        self.spi_write([self.CMD_SET_RX,
                       (timeout >> 16) & 0xFF,
                       (timeout >> 8) & 0xFF,
                       timeout & 0xFF])
        
        # Wait for reception
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            # Check IRQ every 100ms
            try:
                irq_data = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                irq = (irq_data[1] << 8) | irq_data[2]
                
                if irq & self.IRQ_RX_DONE:
                    print("✓ RX Done!")
                    
                    # Get buffer info
                    buffer_status = self.spi_read([self.CMD_GET_RX_BUFFER_STATUS, 0x00], 3)
                    payload_length = buffer_status[1]
                    buffer_offset = buffer_status[2]
                    
                    if payload_length > 0 and payload_length < 256:
                        # Read data
                        received_data = self.spi_read([self.CMD_READ_BUFFER, buffer_offset], payload_length)
                        
                        # Clear IRQ and return
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        
                        try:
                            decoded = bytes(received_data).decode('utf-8', errors='ignore')
                            print(f"Received: '{decoded}'")
                            return bytes(received_data)
                        except:
                            print(f"Received: {bytes(received_data)}")
                            return bytes(received_data)
                
                elif irq & self.IRQ_TIMEOUT:
                    print("RX Timeout")
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                    break
                
                elif irq != 0:
                    # Clear other IRQs (preamble, sync, etc.)
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                
            except Exception as e:
                print(f"RX error: {e}")
                time.sleep_ms(100)
                continue
            
            time.sleep_ms(100)
        
        return None


def test_two_core1262_modules():
    """Test communication between two Core1262 modules"""
    print("=== Two Core1262 Module Communication Test ===")
    print("Make sure you have TWO Core1262 modules connected!")
    print("This will test if they can communicate with each other.")
    print()
    
    try:
        # Initialize LoRa module
        lora = SX1262()
        
        print("Choose test mode:")
        print("1. Transmitter mode (sends messages)")
        print("2. Receiver mode (listens for messages)")
        print("3. Ping-pong mode (sends then listens)")
        
        # For demo, we'll use ping-pong mode
        mode = 3
        
        if mode == 1:
            # Transmitter mode
            print("\n=== TRANSMITTER MODE ===")
            counter = 0
            while True:
                message = f"Core1262-TX-{counter:03d}"
                print(f"Sending: {message}")
                
                if lora.send_data(message):
                    print("✓ Sent successfully!")
                else:
                    print("✗ Send failed")
                
                counter += 1
                time.sleep(3)
                
        elif mode == 2:
            # Receiver mode
            print("\n=== RECEIVER MODE ===")
            print("Listening for messages from other Core1262...")
            
            while True:
                received = lora.receive_data(timeout_ms=30000)
                if received:
                    try:
                        message = received.decode('utf-8')
                        print(f"✓ RECEIVED: '{message}'")
                    except:
                        print(f"✓ RECEIVED: {received}")
                else:
                    print("- No message (timeout)")
                    
        elif mode == 3:
            # Ping-pong mode
            print("\n=== PING-PONG MODE ===")
            print("Sends a message, then listens for response")
            
            counter = 0
            while True:
                # Send
                message = f"PING-{counter:03d}"
                print(f"\nSending: {message}")
                
                if lora.send_data(message):
                    print("✓ Sent")
                    
                    # Listen for response
                    print("Listening for response...")
                    received = lora.receive_data(timeout_ms=5000)
                    
                    if received:
                        try:
                            response = received.decode('utf-8')
                            print(f"✓ Response: '{response}'")
                        except:
                            print(f"✓ Response: {received}")
                    else:
                        print("- No response")
                else:
                    print("✗ Send failed")
                
                counter += 1
                time.sleep(5)
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def simple_send_test():
    """Simple continuous sending test"""
    try:
        lora = SX1262()
        
        counter = 0
        while True:
            message = f"MSG-{counter:03d}: Hello other Core1262!"
            print(f"Sending: {message}")
            
            if lora.send_data(message):
                print("✓ Sent successfully!")
            else:
                print("✗ Send failed")
            
            counter += 1
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")

def simple_receive_test():
    """Simple continuous listening test"""
    try:
        lora = SX1262()
        print("Listening for messages from other Core1262...")
        
        while True:
            received = lora.receive_data(timeout_ms=30000)
            
            if received:
                try:
                    message = received.decode('utf-8')
                    print(f"✓ RECEIVED: '{message}'")
                except:
                    print(f"✓ RECEIVED: {received}")
            else:
                print("- Timeout, still listening...")
                
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}")

# Main execution
if __name__ == "__main__":
    # Choose which test to run:
    
    # Test communication between two Core1262 modules
    test_two_core1262_modules()
    
    # Simple send test
    # simple_send_test()
    
    # Simple receive test  
    # simple_receive_test()