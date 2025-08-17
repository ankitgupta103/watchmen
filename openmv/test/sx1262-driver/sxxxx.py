import time
from machine import SPI, Pin

class SX1262:
    """SX1262 LoRa driver for OpenMV RT1062"""
    
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
        """Initialize SX1262 with OpenMV RT1062 pins
        
        Pin connections:
        P0 - MOSI (automatic)
        P1 - MISO (automatic) 
        P2 - SCLK (automatic)
        P3 - NSS (Chip Select)
        P6 - RESET
        P7 - BUSY
        P13 - DIO1
        """
        # Initialize SPI (pins P0=MOSI, P1=MISO, P2=SCLK are automatic for hardware SPI)
        self.spi = SPI(spi_id)
        self.spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
        
        # Initialize control pins
        self.nss = Pin(nss_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        # Initialize pins
        self.nss.on()  # Set NSS high (inactive)
        self.reset.on()  # Set reset high (inactive)
        
        # Reset the module
        self.hardware_reset()
        
        # Initialize the module
        self.init_lora()
    
    def hardware_reset(self):
        """Hardware reset of SX1262"""
        self.reset.off()  # Pull reset low
        time.sleep_ms(10)
        self.reset.on()   # Release reset
        time.sleep_ms(20)
        self.wait_busy()
    
    def wait_busy(self):
        """Wait for BUSY pin to go low"""
        timeout = 10000  # 1 second timeout (10000 * 100us)
        while self.busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        if timeout == 0:
            print("Warning: BUSY timeout")
    
    def spi_write(self, data):
        """Write data via SPI"""
        self.wait_busy()
        self.nss.off()  # Select device (active low)
        if isinstance(data, list):
            data = bytes(data)
        self.spi.write(data)
        self.nss.on()   # Deselect device
        time.sleep_ms(1)  # Small delay after SPI transaction
    
    def spi_read(self, cmd, length):
        """Read data via SPI"""
        self.wait_busy()
        self.nss.off()  # Select device
        
        # Send command
        if isinstance(cmd, list):
            cmd = bytes(cmd)
        self.spi.write(cmd)
        
        # Read response
        data = self.spi.read(length, 0x00)
        self.nss.on()   # Deselect device
        time.sleep_ms(1)  # Small delay after SPI transaction
        return data
    
    def get_status(self):
        """Get device status for debugging"""
        try:
            status = self.spi_read([0xC0, 0x00], 1)
            return status[0] if status else 0
        except:
            return 0
    
    def init_lora(self):
        """Initialize LoRa configuration"""
        print("Initializing SX1262...")
        
        # Check initial status
        status = self.get_status()
        print(f"Initial status: 0x{status:02X}")
        
        # Set standby mode (STDBY_RC)
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(50)
        
        # Check if we're in standby
        status = self.get_status()
        print(f"After standby command: 0x{status:02X}")
        
        # Set regulator mode to LDO (more reliable than DC-DC for initial testing)
        self.spi_write([self.CMD_SET_REGULATOR_MODE, 0x00])  # 0x00 = LDO only
        time.sleep_ms(10)
        
        # Check for device errors before calibration
        self.check_device_errors("Before calibration")
        
        # Calibrate all blocks - IMPORTANT for proper operation
        print("Calibrating...")
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(500)  # Give more time for calibration
        
        # Check status and errors after calibration
        status = self.get_status()
        print(f"After calibration: 0x{status:02X}")
        self.check_device_errors("After calibration")
        
        # CRITICAL: Set PA config for SX1262 BEFORE other RF settings
        print("Setting PA config...")
        self.spi_write([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01])
        time.sleep_ms(10)
        
        # Set packet type to LoRa
        print("Setting packet type...")
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        time.sleep_ms(10)
        
        # Try multiple frequencies to see which one works
        frequencies = [
            (433000000, "433 MHz (LF band)"),
            (490000000, "490 MHz (LF band)"), 
            (868000000, "868 MHz (HF band)"),
            (915000000, "915 MHz (HF band)")
        ]
        
        working_freq = None
        for freq_hz, freq_name in frequencies:
            print(f"Testing {freq_name}...")
            freq_raw = int((freq_hz * 33554432) // 32000000)
            print(f"  Raw value: {freq_raw} (0x{freq_raw:08X})")
            
            self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                           (freq_raw >> 24) & 0xFF,
                           (freq_raw >> 16) & 0xFF, 
                           (freq_raw >> 8) & 0xFF,
                           freq_raw & 0xFF])
            time.sleep_ms(10)
            
            # Test FS mode
            self.spi_write([0xC1])  # SetFs command
            time.sleep_ms(100)
            
            status = self.get_status()
            fs_mode = (status >> 4) & 0x7
            print(f"  FS test result - Status: 0x{status:02X}, Mode: {fs_mode}")
            
            if fs_mode == 4:  # FS mode successful
                print(f"  SUCCESS: {freq_name} works!")
                working_freq = freq_hz
                # Return to standby
                self.spi_write([self.CMD_SET_STANDBY, 0x00])
                time.sleep_ms(10)
                break
            else:
                print(f"  FAILED: {freq_name} doesn't work")
                # Return to standby
                self.spi_write([self.CMD_SET_STANDBY, 0x00])
                time.sleep_ms(10)
                # Check for errors
                self.check_device_errors(f"After {freq_name} test")
        
        if working_freq is None:
            print("ERROR: No frequency worked! This may be a hardware issue.")
            return False
        
        print(f"Using working frequency: {working_freq} Hz")
        
        # Set modulation params - MUST be done before packet params
        print("Setting modulation params...")
        self.spi_write([self.CMD_SET_MODULATION_PARAMS, 
                       0x07,  # SF7
                       0x04,  # BW125kHz
                       0x01,  # CR4/5
                       0x00]) # LDRO off
        time.sleep_ms(10)
        
        # Set packet params
        print("Setting packet params...")
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x08,  # Preamble length (8 symbols)
                       0x00,        # Explicit header
                       0x20,        # Payload length (32 bytes default)
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        time.sleep_ms(10)
        
        # Set buffer base addresses
        print("Setting buffer addresses...")
        self.spi_write([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00])
        time.sleep_ms(10)
        
        # Set TX power (start with lower power for testing)
        print("Setting TX power...")
        self.spi_write([self.CMD_SET_TX_PARAMS, 10, 0x02])  # 10dBm, 40us ramp
        time.sleep_ms(10)
        
        # Configure DIO IRQ params
        print("Setting IRQ params...")
        self.spi_write([self.CMD_SET_DIO_IRQ_PARAMS,
                       0x03, 0xFF,  # IRQ mask (enable TX_DONE, RX_DONE, TIMEOUT)
                       0x03, 0xFF,  # DIO1 mask
                       0x00, 0x00,  # DIO2 mask  
                       0x00, 0x00]) # DIO3 mask
        time.sleep_ms(10)
        
        # Clear any pending IRQs
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        time.sleep_ms(10)
        
        # Final test: Try FS mode again with working frequency
        print("Final FS mode test...")
        self.spi_write([0xC1])  # SetFs command
        time.sleep_ms(50)
        
        status = self.get_status()
        fs_mode = (status >> 4) & 0x7
        print(f"Final FS test - Status: 0x{status:02X}, Mode: {fs_mode}")
        
        # Return to standby
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        # Final status check
        status = self.get_status()
        print(f"Final status: 0x{status:02X}")
        chip_mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        print(f"Chip mode: {chip_mode}, Command status: {cmd_status}")
        
        success = (cmd_status == 1) and (working_freq is not None)
        if success:
            print("SX1262 initialized successfully!")
        else:
            print(f"WARNING: Initialization issues detected")
        
        return success
    
    def check_device_errors(self, context=""):
        """Check for device errors and print them"""
        try:
            error_data = self.spi_read([0x17, 0x00], 3)  # GetDeviceErrors
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
                
                # Clear errors for next test
                self.spi_write([0x07, 0x00, 0x00])  # ClearDeviceErrors
            else:
                print(f"No device errors {context}")
        except Exception as e:
            print(f"Error checking device errors: {e}")
    
    def send_data(self, data):
        """Send data via LoRa"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"Sending: {data}")
        
        # Ensure we're in standby mode first
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        # Clear any pending IRQs
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        time.sleep_ms(10)
        
        # Write data to buffer
        cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        self.spi_write(cmd)
        time.sleep_ms(10)
        
        # Update packet params with actual payload length (keep it simple)
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x08,  # Preamble length (8 symbols)
                       0x00,        # Explicit header
                       len(data),   # Actual payload length
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        time.sleep_ms(10)
        
        # Check status before TX
        status = self.get_status()
        print(f"Status before TX: 0x{status:02X}")
        
        # Set TX mode with shorter timeout (3 seconds)
        timeout = int(3000000 // 15.625)  # Convert to internal units
        self.spi_write([self.CMD_SET_TX,
                       (timeout >> 16) & 0xFF,
                       (timeout >> 8) & 0xFF,
                       timeout & 0xFF])
        
        print("TX command sent, waiting for completion...")
        
        # Wait a moment for the command to be processed
        time.sleep_ms(100)
        
        # Check if we entered TX mode
        status = self.get_status()
        chip_mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        print(f"Status after TX command: 0x{status:02X} (mode: {chip_mode}, cmd: {cmd_status})")
        
        if chip_mode != 6:  # 6 = TX mode
            print(f"ERROR: Device not in TX mode! Current mode: {chip_mode}")
            return False
        
        # Wait for TX done with monitoring
        start_time = time.ticks_ms()
        last_check = 0
        
        while time.ticks_diff(time.ticks_ms(), start_time) < 5000:  # 5 second timeout
            current_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            # Check DIO1 state
            dio1_state = self.dio1.value()
            
            # Print status every second
            if current_time - last_check >= 1000:
                status = self.get_status()
                mode = (status >> 4) & 0x7
                print(f"Time: {current_time}ms, DIO1: {dio1_state}, Mode: {mode}")
                last_check = current_time
            
            if dio1_state:
                # Check IRQ status
                try:
                    irq_data = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                    irq = (irq_data[1] << 8) | irq_data[2]
                    print(f"IRQ Status: 0x{irq:04X}")
                    
                    if irq & self.IRQ_TX_DONE:
                        print("TX Done!")
                        # Clear IRQ
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return True
                    elif irq & self.IRQ_TIMEOUT:
                        print("TX Timeout!")
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return False
                except Exception as e:
                    print(f"Error reading IRQ: {e}")
            
            time.sleep_ms(100)
        
        print("TX failed - no response within timeout")
        # Clear any IRQs and return to standby
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        return False
    
    def receive_data(self, timeout_ms=30000):
        """Receive data via LoRa"""
        print("Listening for data...")
        
        # Set RX mode with timeout
        timeout = int(timeout_ms * 1000 // 15.625)  # Convert to internal units
        if timeout > 0xFFFFFF:
            timeout = 0xFFFFFF
            
        self.spi_write([self.CMD_SET_RX,
                       (timeout >> 16) & 0xFF,
                       (timeout >> 8) & 0xFF,
                       timeout & 0xFF])
        
        # Wait for RX done or timeout
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.dio1.value():
                # Check IRQ status
                irq_status = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                irq = (irq_status[1] << 8) | irq_status[2]
                
                if irq & self.IRQ_RX_DONE:
                    print("RX Done!")
                    # Get buffer status
                    buffer_status = self.spi_read([self.CMD_GET_RX_BUFFER_STATUS, 0x00], 3)
                    payload_length = buffer_status[1]
                    buffer_offset = buffer_status[2]
                    
                    # Read received data
                    if payload_length > 0:
                        received_data = self.spi_read([self.CMD_READ_BUFFER, buffer_offset], payload_length)
                        # Clear IRQ
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0x02, 0x03])
                        return bytes(received_data)
                
                elif irq & self.IRQ_TIMEOUT:
                    print("RX Timeout!")
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0x02, 0x03])
                    return None
            
            time.sleep_ms(10)
        
        print("RX failed - timeout")
        return None


# Example usage
def main():
    """Main function demonstrating LoRa communication"""
    try:
        # Initialize LoRa module
        lora = SX1262()
        
        # Example: Send sensor data
        while True:
            # Get some sensor data (example)
            sensor_data = f"Hello from OpenMV! Time: {time.ticks_ms()}"
            
            # Send data
            if lora.send_data(sensor_data):
                print("Data sent successfully!")
            else:
                print("Failed to send data")
            
            # Optional: Listen for incoming data
            received = lora.receive_data(timeout_ms=5000)
            if received:
                print(f"Received: {received.decode('utf-8', errors='ignore')}")
            
            # Wait before next transmission
            time.sleep(5)
            
    except Exception as e:
        print(f"Error: {e}")

# Uncomment to run the main function
main()