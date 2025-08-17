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
        """Initialize LoRa configuration for Core1262 with TCXO"""
        print("Initializing SX1262 with TCXO...")
        
        # Check initial status
        status = self.get_status()
        print(f"Initial status: 0x{status:02X}")
        
        # Start in STDBY_RC mode
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(50)
        
        status = self.get_status()
        print(f"STDBY_RC status: 0x{status:02X}")
        
        # CRITICAL: Enable TCXO before anything else
        print("Enabling TCXO...")
        # SetDIO3AsTCXOCtrl: voltage=1.8V (0x02), timeout=320us (0x000020)
        self.spi_write([0x97, 0x02, 0x00, 0x00, 0x20])
        time.sleep_ms(100)
        
        # Now switch to STDBY_XOSC (with TCXO)
        print("Switching to STDBY_XOSC with TCXO...")
        self.spi_write([self.CMD_SET_STANDBY, 0x01])  # STDBY_XOSC
        time.sleep_ms(200)  # Give TCXO time to stabilize
        
        # Verify TCXO mode
        status = self.get_status()
        mode = (status >> 4) & 0x7
        print(f"TCXO mode status: 0x{status:02X}, Mode: {mode}")
        
        if mode != 3:  # 3 = STDBY_XOSC
            print(f"ERROR: Failed to enter TCXO mode. Mode: {mode}")
            return False
        
        print("SUCCESS: TCXO mode active!")
        
        # Set regulator mode to LDO (more stable)
        self.spi_write([self.CMD_SET_REGULATOR_MODE, 0x00])  # LDO
        time.sleep_ms(10)
        
        # Check for any errors before calibration
        self.check_device_errors("Before calibration")
        
        # Calibrate with TCXO running
        print("Calibrating with TCXO...")
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(500)
        
        # Check calibration results
        status = self.get_status()
        print(f"After calibration: 0x{status:02X}")
        self.check_device_errors("After calibration")
        
        # Set PA config for SX1262 HF variant
        print("Setting PA config...")
        self.spi_write([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01])
        time.sleep_ms(10)
        
        # Set packet type to LoRa
        print("Setting packet type...")
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        time.sleep_ms(10)
        
        # Set frequency for HF band (868 MHz)
        freq_hz = 868000000
        freq_raw = int((freq_hz * 33554432) // 32000000)
        print(f"Setting frequency: {freq_hz} Hz (0x{freq_raw:08X})")
        self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                       (freq_raw >> 24) & 0xFF,
                       (freq_raw >> 16) & 0xFF, 
                       (freq_raw >> 8) & 0xFF,
                       freq_raw & 0xFF])
        time.sleep_ms(10)
        
        # Test FS mode to verify frequency synthesis works
        print("Testing FS mode...")
        self.spi_write([0xC1])  # SetFs command
        time.sleep_ms(100)
        
        status = self.get_status()
        fs_mode = (status >> 4) & 0x7
        print(f"FS test result: Status=0x{status:02X}, Mode={fs_mode}")
        
        if fs_mode != 4:  # 4 = FS mode
            print(f"ERROR: FS mode failed. Mode: {fs_mode}")
            self.check_device_errors("After FS test")
            return False
        
        print("SUCCESS: FS mode works!")
        
        # Return to standby XOSC
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(10)
        
        # Set modulation params to match LoRaHat air_speed=2400
        print("Setting modulation params for 2400 bps compatibility...")
        # For ~2400 bps: SF9 + BW125 = ~2344 bps (closest match)
        self.spi_write([self.CMD_SET_MODULATION_PARAMS, 
                       0x09,  # SF9 (instead of SF7)
                       0x04,  # BW125kHz
                       0x01,  # CR4/5
                       0x01]) # LDRO on (required for SF9+BW125)
        time.sleep_ms(10)
        
        # Set packet params with longer preamble for better compatibility
        print("Setting packet params...")
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x0C,  # Preamble length (12 symbols - standard)
                       0x00,        # Explicit header
                       0xFF,        # Payload length (255 max)
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        time.sleep_ms(10)
        
        # Set buffer base addresses
        print("Setting buffer addresses...")
        self.spi_write([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00])
        time.sleep_ms(10)
        
        # Set TX power to match LoRaHat
        print("Setting TX power...")
        self.spi_write([self.CMD_SET_TX_PARAMS, 22, 0x02])  # 22dBm to match LoRaHat
        time.sleep_ms(10)
        
        # Configure DIO IRQ params
        print("Setting IRQ params...")
        self.spi_write([self.CMD_SET_DIO_IRQ_PARAMS,
                       0x03, 0xFF,  # IRQ mask (TX_DONE, RX_DONE, TIMEOUT)
                       0x03, 0xFF,  # DIO1 mask
                       0x00, 0x00,  # DIO2 mask  
                       0x00, 0x00]) # DIO3 mask (DIO3 used for TCXO)
        time.sleep_ms(10)
        
        # Clear any pending IRQs
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        time.sleep_ms(10)
        
        # Final status check
        status = self.get_status()
        print(f"Final status: 0x{status:02X}")
        chip_mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        print(f"Chip mode: {chip_mode}, Command status: {cmd_status}")
        
        if cmd_status == 1:
            print("✓ SX1262 with TCXO initialized successfully!")
            return True
        else:
            print(f"✗ Initialization failed. Command status: {cmd_status}")
            return False
    
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
        
        # Ensure we're in standby XOSC mode with TCXO
        self.spi_write([self.CMD_SET_STANDBY, 0x01])  # STDBY_XOSC
        time.sleep_ms(20)
        
        # Clear any pending IRQs and errors
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        self.spi_write([0x07, 0x00, 0x00])  # Clear device errors
        time.sleep_ms(10)
        
        # Re-calibrate before TX (important for PLL stability)
        print("Re-calibrating before TX...")
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(100)
        
        # Check for calibration errors
        self.check_device_errors("After pre-TX calibration")
        
        # Write data to buffer
        cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        self.spi_write(cmd)
        time.sleep_ms(10)
        
        # Update packet params with actual payload length and longer preamble
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x0C,  # Preamble length (12 symbols)
                       0x00,        # Explicit header
                       len(data),   # Actual payload length
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        time.sleep_ms(10)
        
        # Test FS mode first to ensure PLL locks
        print("Testing PLL lock...")
        self.spi_write([0xC1])  # SetFs command
        time.sleep_ms(50)
        
        status = self.get_status()
        fs_mode = (status >> 4) & 0x7
        print(f"FS test: Status=0x{status:02X}, Mode={fs_mode}")
        
        if fs_mode != 4:
            print("ERROR: PLL failed to lock!")
            self.check_device_errors("After FS test")
            return False
        
        # Return to standby before TX
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(10)
        
        # Check status before TX
        status = self.get_status()
        print(f"Status before TX: 0x{status:02X}")
        
        # Set TX mode with no timeout (0x000000 = infinite)
        print("Setting TX mode...")
        self.spi_write([self.CMD_SET_TX, 0x00, 0x00, 0x00])
        
        # Wait a moment for the command to be processed
        time.sleep_ms(50)
        
        # Check if we entered TX mode
        status = self.get_status()
        chip_mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        print(f"Status after TX command: 0x{status:02X} (mode: {chip_mode}, cmd: {cmd_status})")
        
        if chip_mode == 6:  # 6 = TX mode
            print("SUCCESS: Device entered TX mode!")
        elif cmd_status == 6:  # TX done immediately (very short packet)
            print("SUCCESS: TX completed immediately!")
            return True
        else:
            print(f"ERROR: Device not in TX mode! Current mode: {chip_mode}")
            self.check_device_errors("After TX command")
            return False
        
        # Wait for TX completion
        start_time = time.ticks_ms()
        max_wait = 10000  # 10 seconds max
        
        while time.ticks_diff(time.ticks_ms(), start_time) < max_wait:
            # Check DIO1 state
            dio1_state = self.dio1.value()
            
            if dio1_state:
                # Check IRQ status
                try:
                    irq_data = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                    irq = (irq_data[1] << 8) | irq_data[2]
                    print(f"IRQ Status: 0x{irq:04X}")
                    
                    if irq & self.IRQ_TX_DONE:
                        print("✓ TX Done!")
                        # Clear IRQ
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return True
                    elif irq & self.IRQ_TIMEOUT:
                        print("✗ TX Timeout!")
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return False
                except Exception as e:
                    print(f"Error reading IRQ: {e}")
            
            # Check if TX completed (mode changed back to standby)
            status = self.get_status()
            current_mode = (status >> 4) & 0x7
            cmd_status = (status >> 1) & 0x7
            
            if current_mode == 3 and cmd_status == 6:  # Back to STDBY_XOSC with TX done
                print("✓ TX completed (returned to standby)!")
                return True
            
            time.sleep_ms(50)
        
        print("✗ TX failed - timeout")
        return False
    
    def receive_data(self, timeout_ms=30000):
        """Receive data via LoRa with proper IRQ handling"""
        print("Listening for data...")
        
        # Ensure we're in standby XOSC mode
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        time.sleep_ms(20)
        
        # Clear any pending IRQs and errors
        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        self.spi_write([0x07, 0x00, 0x00])  # Clear device errors
        time.sleep_ms(10)
        
        # Re-calibrate before RX for stability
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(50)
        
        # Set RX mode with timeout
        timeout = int(timeout_ms * 1000 // 15.625)  # Convert to internal units
        if timeout > 0xFFFFFF:
            timeout = 0xFFFFFF
            
        print(f"Setting RX mode with {timeout_ms}ms timeout...")
        self.spi_write([self.CMD_SET_RX,
                       (timeout >> 16) & 0xFF,
                       (timeout >> 8) & 0xFF,
                       timeout & 0xFF])
        
        # Verify we entered RX mode
        time.sleep_ms(50)
        status = self.get_status()
        mode = (status >> 4) & 0x7
        print(f"RX mode status: 0x{status:02X}, Mode: {mode}")
        
        if mode != 5:  # 5 = RX mode
            print(f"ERROR: Failed to enter RX mode. Current mode: {mode}")
            return None
        
        print("Listening for packets...")
        
        # Wait for RX done or timeout
        start_time = time.ticks_ms()
        last_status_check = 0
        packets_received = 0
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            current_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            # Check status less frequently to avoid spam
            if current_time - last_status_check >= 5000:  # Check every 5 seconds
                status = self.get_status()
                mode = (status >> 4) & 0x7
                print(f"RX status check: Mode={mode}, Time={current_time}ms")
                last_status_check = current_time
            
            # Check IRQ status
            try:
                irq_data = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                irq = (irq_data[1] << 8) | irq_data[2]
                
                if irq != 0:
                    print(f"IRQ: 0x{irq:04X}")
                    
                    if irq & self.IRQ_RX_DONE:
                        packets_received += 1
                        print(f"✓ Packet #{packets_received} received!")
                        
                        # Get buffer status
                        try:
                            buffer_status = self.spi_read([self.CMD_GET_RX_BUFFER_STATUS, 0x00], 3)
                            payload_length = buffer_status[1]
                            buffer_offset = buffer_status[2]
                            
                            print(f"  Payload: {payload_length} bytes at offset {buffer_offset}")
                            
                            # Read received data
                            if payload_length > 0 and payload_length < 256:
                                received_data = self.spi_read([self.CMD_READ_BUFFER, buffer_offset], payload_length)
                                
                                # Clear IRQ and return data
                                self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                                
                                try:
                                    decoded = bytes(received_data).decode('utf-8', errors='ignore')
                                    print(f"  Decoded: {decoded}")
                                    return bytes(received_data)
                                except:
                                    print(f"  Raw data: {bytes(received_data)}")
                                    return bytes(received_data)
                            else:
                                print(f"  Invalid payload length: {payload_length}")
                        except Exception as e:
                            print(f"  Error reading buffer: {e}")
                    
                    elif irq & self.IRQ_TIMEOUT:
                        print("RX Timeout")
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        break
                    
                    else:
                        # Clear other IRQs (like preamble detected, header valid, etc.)
                        self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                
            except Exception as e:
                print(f"Error checking IRQ: {e}")
                time.sleep_ms(100)
                continue
            
            time.sleep_ms(200)  # Check every 200ms instead of 100ms
        
        print(f"RX finished. Packets received: {packets_received}")
        # Ensure we're back in standby
        self.spi_write([self.CMD_SET_STANDBY, 0x01])
        return None
    
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