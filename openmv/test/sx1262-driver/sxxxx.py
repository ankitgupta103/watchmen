import time
from machine import SPI, Pin

class SX1262:
    """SX1262 LoRa driver for OpenMV RT1062 - SPI Bus 1 Configuration"""
    
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
    CMD_GET_STATUS = 0xC0
    CMD_GET_DEVICE_ERRORS = 0x17
    CMD_CLEAR_DEVICE_ERRORS = 0x07
    
    # Packet types
    PACKET_TYPE_LORA = 0x01
    
    # IRQ masks
    IRQ_TX_DONE = 0x0001
    IRQ_RX_DONE = 0x0002
    IRQ_TIMEOUT = 0x0200
    
    def __init__(self, nss_pin='P3', reset_pin='P6', busy_pin='P7', dio1_pin='P13'):
        """
        Initialize SX1262 with OpenMV RT1062 - SPI Bus 1
        Your connections:
        P0 = MOSI, P1 = MISO, P2 = SCLK, P3 = NSS/CS
        P6 = RESET, P7 = BUSY, P13 = DIO1
        """
        
        print("=== Initializing SX1262 on OpenMV RT1062 ===")
        print("SPI Bus 1: P0=MOSI, P1=MISO, P2=SCLK, P3=NSS")
        print(f"Control pins: RESET={reset_pin}, BUSY={busy_pin}, DIO1={dio1_pin}")
        
        # Initialize SPI Bus 1 (matches your connections)
        self.spi = SPI(1, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
        
        # Initialize control pins
        self.nss = Pin(nss_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        # Set initial pin states
        self.nss.on()    # NSS high (deselected)
        self.reset.on()  # Reset inactive (high)
        
        print("Hardware pins initialized")
        
        # Perform hardware reset and initialization
        self.hardware_reset()
        success = self.init_lora()
        
        if success:
            print("✓ SX1262 initialization completed successfully!")
        else:
            print("✗ SX1262 initialization failed!")
    
    def hardware_reset(self):
        """Perform hardware reset sequence"""
        print("Performing hardware reset...")
        
        # Reset sequence
        self.reset.off()  # Reset active (low)
        time.sleep_ms(20)  # Hold reset for 20ms
        self.reset.on()   # Release reset (high)
        time.sleep_ms(50)  # Wait for reset to complete
        
        # Wait for device to be ready
        if self.wait_busy():
            print("✓ Hardware reset completed")
        else:
            print("⚠ Warning: Device still busy after reset")
    
    def wait_busy(self, timeout_ms=1000):
        """Wait for BUSY pin to go low"""
        start_time = time.ticks_ms()
        while self.busy.value():
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
                print(f"⚠ BUSY timeout after {timeout_ms}ms")
                return False
            time.sleep_us(100)
        return True
    
    def spi_transaction(self, data_out, read_length=0):
        """Perform complete SPI transaction with proper timing"""
        
        # Wait for device to be ready
        if not self.wait_busy():
            print("ERROR: Device busy before SPI transaction")
            return None
        
        # Convert data to bytes if needed
        if isinstance(data_out, list):
            data_out = bytes(data_out)
        
        # Start transaction
        self.nss.off()  # Select device
        time.sleep_us(1)  # Brief setup time
        
        try:
            # Write command/data
            self.spi.write(data_out)
            
            # Read response if requested
            if read_length > 0:
                response = self.spi.read(read_length, 0x00)
                time.sleep_us(1)
                self.nss.on()  # Deselect device
                time.sleep_us(10)  # Brief hold time
                return response
            else:
                time.sleep_us(1)
                self.nss.on()  # Deselect device
                time.sleep_us(10)
                return True
                
        except Exception as e:
            print(f"SPI transaction error: {e}")
            self.nss.on()  # Ensure deselection
            return None
    
    def get_status(self):
        """Get device status register"""
        response = self.spi_transaction([self.CMD_GET_STATUS, 0x00], 1)
        if response:
            return response[0]
        return 0
    
    def get_device_errors(self):
        """Get device error flags"""
        response = self.spi_transaction([self.CMD_GET_DEVICE_ERRORS, 0x00], 3)
        if response and len(response) >= 3:
            errors = (response[1] << 8) | response[2]
            return errors
        return 0
    
    def clear_device_errors(self):
        """Clear all device error flags"""
        return self.spi_transaction([self.CMD_CLEAR_DEVICE_ERRORS, 0x00, 0x00])
    
    def check_device_communication(self):
        """Verify device is responding to SPI commands"""
        print("Checking device communication...")
        
        for attempt in range(5):
            status = self.get_status()
            if status != 0:
                mode = (status >> 4) & 0x7
                cmd_status = (status >> 1) & 0x7
                print(f"✓ Device responds: Status=0x{status:02X}, Mode={mode}, CmdStatus={cmd_status}")
                
                # Check for errors
                errors = self.get_device_errors()
                if errors:
                    print(f"⚠ Device errors detected: 0x{errors:04X}")
                    self.clear_device_errors()
                    
                return True
            else:
                print(f"  Attempt {attempt + 1}: No response (status=0x{status:02X})")
                time.sleep_ms(100)
        
        print("✗ ERROR: Device not responding to SPI commands!")
        print("Check your wiring:")
        print("  VCC  → 3.3V")
        print("  GND  → GND") 
        print("  P0   → MOSI")
        print("  P1   → MISO")
        print("  P2   → SCLK")
        print("  P3   → NSS/CS")
        print("  P6   → RESET")
        print("  P7   → BUSY")
        print("  P13  → DIO1")
        return False
    
    def init_lora(self):
        """Initialize LoRa modem with comprehensive error checking"""
        print("\n=== Starting LoRa Initialization ===")
        
        # Step 1: Check basic communication
        if not self.check_device_communication():
            return False
        
        # Step 2: Set standby mode (RC oscillator)
        print("Setting STDBY_RC mode...")
        if not self.spi_transaction([self.CMD_SET_STANDBY, 0x00]):
            print("ERROR: Failed to set STDBY_RC mode")
            return False
        time.sleep_ms(10)
        
        # Step 3: Set regulator mode (LDO for stability)
        print("Setting regulator mode (LDO)...")
        if not self.spi_transaction([self.CMD_SET_REGULATOR_MODE, 0x00]):
            print("ERROR: Failed to set regulator mode")
            return False
        time.sleep_ms(10)
        
        # Step 4: Calibrate all blocks
        print("Calibrating device...")
        if not self.spi_transaction([self.CMD_CALIBRATE, 0x7F]):  # Calibrate all
            print("ERROR: Failed to start calibration")
            return False
        time.sleep_ms(1000)  # Wait for calibration to complete
        
        # Step 5: Configure PA for SX1262
        print("Configuring Power Amplifier...")
        # paDutyCycle=0x04, hpMax=0x07, deviceSel=0x00 (SX1262), paLut=0x01
        if not self.spi_transaction([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01]):
            print("ERROR: Failed to configure PA")
            return False
        time.sleep_ms(10)
        
        # Step 6: Set packet type to LoRa
        print("Setting packet type to LoRa...")
        if not self.spi_transaction([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA]):
            print("ERROR: Failed to set packet type")
            return False
        time.sleep_ms(10)
        
        # Step 7: Set RF frequency (868 MHz)
        print("Setting RF frequency to 868 MHz...")
        freq_raw = int((868000000 * (2**25)) // 32000000)
        freq_bytes = [
            self.CMD_SET_RF_FREQUENCY,
            (freq_raw >> 24) & 0xFF,
            (freq_raw >> 16) & 0xFF, 
            (freq_raw >> 8) & 0xFF,
            freq_raw & 0xFF
        ]
        if not self.spi_transaction(freq_bytes):
            print("ERROR: Failed to set frequency")
            return False
        time.sleep_ms(10)
        
        # Step 8: Set modulation parameters (SF7, BW125, CR4/5)
        print("Setting modulation parameters...")
        if not self.spi_transaction([self.CMD_SET_MODULATION_PARAMS, 0x07, 0x04, 0x01, 0x00]):
            print("ERROR: Failed to set modulation parameters")
            return False
        time.sleep_ms(10)
        
        # Step 9: Set packet parameters
        print("Setting packet parameters...")
        packet_params = [
            self.CMD_SET_PACKET_PARAMS,
            0x00, 0x0C,  # Preamble length: 12 symbols
            0x00,        # Explicit header
            0xFF,        # Max payload length
            0x01,        # CRC enabled
            0x00         # Standard IQ
        ]
        if not self.spi_transaction(packet_params):
            print("ERROR: Failed to set packet parameters")
            return False
        time.sleep_ms(10)
        
        # Step 10: Set buffer base addresses
        print("Setting buffer base addresses...")
        if not self.spi_transaction([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00]):
            print("ERROR: Failed to set buffer addresses")
            return False
        time.sleep_ms(10)
        
        # Step 11: Set TX parameters (14dBm power)
        print("Setting TX parameters...")
        if not self.spi_transaction([self.CMD_SET_TX_PARAMS, 14, 0x02]):
            print("ERROR: Failed to set TX parameters")
            return False
        time.sleep_ms(10)
        
        # Step 12: Configure DIO and IRQ
        print("Configuring IRQ and DIO pins...")
        irq_config = [
            self.CMD_SET_DIO_IRQ_PARAMS,
            0x03, 0xFF,  # IRQ mask (TX_DONE | RX_DONE | TIMEOUT)
            0x03, 0xFF,  # DIO1 mask (same as IRQ mask)
            0x00, 0x00,  # DIO2 mask (none)
            0x00, 0x00   # DIO3 mask (none)
        ]
        if not self.spi_transaction(irq_config):
            print("ERROR: Failed to configure IRQ")
            return False
        time.sleep_ms(10)
        
        # Step 13: Clear any pending IRQs
        print("Clearing IRQ flags...")
        if not self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF]):
            print("ERROR: Failed to clear IRQ flags")
            return False
        
        # Final verification
        final_status = self.get_status()
        print(f"Initialization complete. Final status: 0x{final_status:02X}")
        
        return True
    
    def send_data(self, data):
        """Send data via LoRa"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"Sending {len(data)} bytes: {data}")
        
        # Set standby mode
        if not self.spi_transaction([self.CMD_SET_STANDBY, 0x00]):
            print("ERROR: Failed to set standby mode")
            return False
        time.sleep_ms(10)
        
        # Clear IRQ flags
        if not self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF]):
            print("ERROR: Failed to clear IRQ flags")
            return False
        
        # Write data to buffer
        write_cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        if not self.spi_transaction(write_cmd):
            print("ERROR: Failed to write data to buffer")
            return False
        
        # Update packet length
        packet_update = [
            self.CMD_SET_PACKET_PARAMS,
            0x00, 0x0C,  # Preamble length
            0x00,        # Explicit header
            len(data),   # Actual payload length
            0x01,        # CRC enabled
            0x00         # Standard IQ
        ]
        if not self.spi_transaction(packet_update):
            print("ERROR: Failed to update packet length")
            return False
        
        # Start transmission
        if not self.spi_transaction([self.CMD_SET_TX, 0x00, 0x00, 0x00]):
            print("ERROR: Failed to start transmission")
            return False
        
        # Wait for transmission to complete
        print("Waiting for transmission...")
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < 5000:  # 5 second timeout
            
            # Check DIO1 pin for IRQ
            if self.dio1.value():
                irq_response = self.spi_transaction([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                if irq_response and len(irq_response) >= 3:
                    irq_flags = (irq_response[1] << 8) | irq_response[2]
                    
                    if irq_flags & self.IRQ_TX_DONE:
                        print("✓ Transmission completed successfully!")
                        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return True
                    elif irq_flags & self.IRQ_TIMEOUT:
                        print("✗ Transmission timeout!")
                        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return False
            
            time.sleep_ms(10)
        
        print("✗ Transmission failed - no response within timeout")
        return False
    
    def receive_data(self, timeout_ms=10000):
        """Receive data via LoRa"""
        print(f"Starting reception (timeout: {timeout_ms}ms)...")
        
        # Set standby mode
        if not self.spi_transaction([self.CMD_SET_STANDBY, 0x00]):
            print("ERROR: Failed to set standby mode")
            return None
        time.sleep_ms(10)
        
        # Clear IRQ flags
        if not self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF]):
            print("ERROR: Failed to clear IRQ flags")
            return None
        
        # Calculate timeout value for SX1262
        timeout_steps = int(timeout_ms * 1000 / 15.625)  # Convert to 15.625µs steps
        if timeout_steps > 0xFFFFFF:
            timeout_steps = 0xFFFFFF
        
        # Start reception
        rx_cmd = [
            self.CMD_SET_RX,
            (timeout_steps >> 16) & 0xFF,
            (timeout_steps >> 8) & 0xFF,
            timeout_steps & 0xFF
        ]
        if not self.spi_transaction(rx_cmd):
            print("ERROR: Failed to start reception")
            return None
        
        print("Listening for packets...")
        start_time = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            
            # Check for IRQ on DIO1
            try:
                irq_response = self.spi_transaction([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                if not irq_response or len(irq_response) < 3:
                    time.sleep_ms(50)
                    continue
                
                irq_flags = (irq_response[1] << 8) | irq_response[2]
                
                if irq_flags & self.IRQ_RX_DONE:
                    print("✓ Packet received!")
                    
                    # Get buffer status
                    buffer_response = self.spi_transaction([self.CMD_GET_RX_BUFFER_STATUS, 0x00], 3)
                    if not buffer_response or len(buffer_response) < 3:
                        print("ERROR: Failed to get buffer status")
                        return None
                    
                    payload_length = buffer_response[1]
                    buffer_offset = buffer_response[2]
                    
                    print(f"Payload: {payload_length} bytes at offset {buffer_offset}")
                    
                    if payload_length > 0 and payload_length <= 255:
                        # Read the received data
                        read_cmd = [self.CMD_READ_BUFFER, buffer_offset]
                        data_response = self.spi_transaction(read_cmd, payload_length)
                        
                        if data_response:
                            # Clear IRQ flags
                            self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                            
                            try:
                                decoded = bytes(data_response).decode('utf-8', errors='ignore')
                                print(f"✓ Received: '{decoded}'")
                            except:
                                print(f"✓ Received: {bytes(data_response)}")
                            
                            return bytes(data_response)
                    
                elif irq_flags & self.IRQ_TIMEOUT:
                    print("Reception timeout")
                    self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                    break
                
                elif irq_flags != 0:
                    # Clear any other IRQ flags
                    self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                
            except Exception as e:
                print(f"Reception error: {e}")
                time.sleep_ms(100)
                continue
            
            time.sleep_ms(50)
        
        print("No packet received within timeout")
        return None


def test_two_modules():
    """Test communication between two SX1262 modules"""
    print("=== SX1262 Two Module Communication Test ===")
    print("Make sure you have TWO Core1262 modules connected!")
    print("Connection for each module:")
    print("  VCC → 3.3V, GND → GND")
    print("  P0 → MOSI, P1 → MISO, P2 → SCLK, P3 → NSS")
    print("  P6 → RESET, P7 → BUSY, P13 → DIO1")
    print()
    
    try:
        # Initialize the LoRa module
        lora = SX1262()
        
        print("\nSelect test mode:")
        print("1. Transmitter mode")
        print("2. Receiver mode") 
        print("3. Ping-pong mode (recommended)")
        
        # Auto-select ping-pong mode for testing
        mode = 3
        
        if mode == 1:
            # Transmitter mode
            print("\n=== TRANSMITTER MODE ===")
            counter = 0
            while True:
                message = f"Hello-{counter:03d}"
                print(f"\n--- Transmission {counter} ---")
                
                if lora.send_data(message):
                    print("✓ Message sent successfully!")
                else:
                    print("✗ Failed to send message")
                
                counter += 1
                time.sleep(3)
                
        elif mode == 2:
            # Receiver mode
            print("\n=== RECEIVER MODE ===") 
            print("Listening for messages...")
            
            while True:
                received = lora.receive_data(timeout_ms=30000)
                if received:
                    print("=" * 40)
                else:
                    print("- Still listening...")
                    
        elif mode == 3:
            # Ping-pong mode
            print("\n=== PING-PONG MODE ===")
            print("Sends message, then listens for response")
            
            counter = 0
            while True:
                print(f"\n{'='*50}")
                print(f"Round {counter}")
                print(f"{'='*50}")
                
                # Send ping
                message = f"PING-{counter:03d}"
                print(f"Sending: {message}")
                
                if lora.send_data(message):
                    print("✓ Ping sent successfully")
                    
                    # Listen for response
                    print("Listening for response...")
                    received = lora.receive_data(timeout_ms=8000)
                    
                    if received:
                        print("✓ Got response!")
                    else:
                        print("- No response received")
                else:
                    print("✗ Failed to send ping")
                
                counter += 1
                time.sleep(2)
        
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

# Main execution
if __name__ == "__main__":
    test_two_modules()