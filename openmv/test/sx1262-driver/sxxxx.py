import time
from machine import SPI, Pin

class SX1262:
    """SX1262 LoRa driver - Diagnostic version for transmission debugging"""
    
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
    IRQ_PREAMBLE_DETECTED = 0x0004
    IRQ_SYNC_WORD_VALID = 0x0008
    IRQ_HEADER_VALID = 0x0010
    IRQ_HEADER_ERR = 0x0020
    IRQ_CRC_ERR = 0x0040
    IRQ_CAD_DONE = 0x0080
    IRQ_CAD_DETECTED = 0x0100
    
    def __init__(self, nss_pin='P3', reset_pin='P6', busy_pin='P7', dio1_pin='P13'):
        """Initialize SX1262 with diagnostic features"""
        
        print("=== SX1262 Diagnostic Initialization ===")
        
        # Initialize SPI Bus 1
        self.spi = SPI(1, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
        
        # Initialize control pins
        self.nss = Pin(nss_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        # Set initial pin states
        self.nss.on()
        self.reset.on()
        
        # Reset and initialize
        self.hardware_reset()
        success = self.init_lora()
        
        if success:
            print("✓ Diagnostic initialization completed!")
        else:
            print("✗ Diagnostic initialization failed!")
    
    def hardware_reset(self):
        """Hardware reset with status monitoring"""
        print("Hardware reset...")
        self.reset.off()
        time.sleep_ms(20)
        self.reset.on()
        time.sleep_ms(50)
        self.wait_busy()
        print("✓ Reset completed")
    
    def wait_busy(self, timeout_ms=1000):
        """Wait for BUSY with status reporting"""
        start_time = time.ticks_ms()
        while self.busy.value():
            if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
                print(f"⚠ BUSY timeout after {timeout_ms}ms")
                return False
            time.sleep_us(100)
        return True
    
    def spi_transaction(self, data_out, read_length=0):
        """SPI transaction with enhanced debugging"""
        if not self.wait_busy():
            print("ERROR: Device busy before SPI")
            return None
        
        if isinstance(data_out, list):
            data_out = bytes(data_out)
        
        self.nss.off()
        time.sleep_us(1)
        
        try:
            self.spi.write(data_out)
            if read_length > 0:
                response = self.spi.read(read_length, 0x00)
                time.sleep_us(1)
                self.nss.on()
                time.sleep_us(10)
                return response
            else:
                time.sleep_us(1)
                self.nss.on()
                time.sleep_us(10)
                return True
        except Exception as e:
            print(f"SPI error: {e}")
            self.nss.on()
            return None
    
    def get_status(self):
        """Get status with detailed decoding"""
        response = self.spi_transaction([self.CMD_GET_STATUS, 0x00], 1)
        if response:
            status = response[0]
            mode = (status >> 4) & 0x7
            cmd_status = (status >> 1) & 0x7
            
            mode_names = {0: "SLEEP", 1: "STBY_RC", 2: "STBY_XOSC", 3: "FS", 4: "RX", 5: "TX"}
            cmd_names = {0: "Reserved", 1: "RFU", 2: "Data Available", 3: "Timeout", 4: "Processing Error", 5: "Execution Failure", 6: "TX Done"}
            
            return {
                'raw': status,
                'mode': mode,
                'mode_name': mode_names.get(mode, f"Unknown({mode})"),
                'cmd_status': cmd_status,
                'cmd_name': cmd_names.get(cmd_status, f"Unknown({cmd_status})")
            }
        return None
    
    def get_irq_status(self):
        """Get IRQ status with detailed decoding"""
        response = self.spi_transaction([self.CMD_GET_IRQ_STATUS, 0x00], 3)
        if response and len(response) >= 3:
            irq_flags = (response[1] << 8) | response[2]
            
            active_irqs = []
            if irq_flags & self.IRQ_TX_DONE: active_irqs.append("TX_DONE")
            if irq_flags & self.IRQ_RX_DONE: active_irqs.append("RX_DONE")
            if irq_flags & self.IRQ_TIMEOUT: active_irqs.append("TIMEOUT")
            if irq_flags & self.IRQ_PREAMBLE_DETECTED: active_irqs.append("PREAMBLE")
            if irq_flags & self.IRQ_SYNC_WORD_VALID: active_irqs.append("SYNC_WORD")
            if irq_flags & self.IRQ_HEADER_VALID: active_irqs.append("HEADER_VALID")
            if irq_flags & self.IRQ_HEADER_ERR: active_irqs.append("HEADER_ERR")
            if irq_flags & self.IRQ_CRC_ERR: active_irqs.append("CRC_ERR")
            if irq_flags & self.IRQ_CAD_DONE: active_irqs.append("CAD_DONE")
            if irq_flags & self.IRQ_CAD_DETECTED: active_irqs.append("CAD_DETECTED")
            
            return {
                'raw': irq_flags,
                'active': active_irqs
            }
        return None
    
    def get_device_errors(self):
        """Get device errors"""
        response = self.spi_transaction([self.CMD_GET_DEVICE_ERRORS, 0x00], 3)
        if response and len(response) >= 3:
            errors = (response[1] << 8) | response[2]
            return errors
        return 0
    
    def clear_device_errors(self):
        """Clear device errors"""
        return self.spi_transaction([self.CMD_CLEAR_DEVICE_ERRORS, 0x00, 0x00])
    
    def print_status(self, prefix=""):
        """Print comprehensive status information"""
        status = self.get_status()
        irq = self.get_irq_status()
        errors = self.get_device_errors()
        dio1_state = self.dio1.value()
        
        if status:
            print(f"{prefix}Status: 0x{status['raw']:02X} - {status['mode_name']} - {status['cmd_name']}")
        if irq:
            print(f"{prefix}IRQ: 0x{irq['raw']:04X} - {irq['active']}")
        if errors:
            print(f"{prefix}Errors: 0x{errors:04X}")
        print(f"{prefix}DIO1: {dio1_state}")
    
    def init_lora(self):
        """Simplified initialization for testing"""
        print("Starting LoRa initialization...")
        
        # Basic initialization steps
        self.spi_transaction([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        self.clear_device_errors()
        
        self.spi_transaction([self.CMD_SET_REGULATOR_MODE, 0x00])
        time.sleep_ms(10)
        
        self.spi_transaction([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(500)
        
        self.spi_transaction([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01])
        time.sleep_ms(10)
        
        self.spi_transaction([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        time.sleep_ms(10)
        
        # Set frequency
        freq_raw = int((868000000 * (2**25)) // 32000000)
        self.spi_transaction([self.CMD_SET_RF_FREQUENCY, 
                             (freq_raw >> 24) & 0xFF, (freq_raw >> 16) & 0xFF, 
                             (freq_raw >> 8) & 0xFF, freq_raw & 0xFF])
        time.sleep_ms(10)
        
        # Set modulation
        self.spi_transaction([self.CMD_SET_MODULATION_PARAMS, 0x07, 0x04, 0x01, 0x00])
        time.sleep_ms(10)
        
        # Set packet params
        self.spi_transaction([self.CMD_SET_PACKET_PARAMS, 0x00, 0x0C, 0x00, 0xFF, 0x01, 0x00])
        time.sleep_ms(10)
        
        # Set buffer addresses
        self.spi_transaction([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00])
        time.sleep_ms(10)
        
        # Set TX params
        self.spi_transaction([self.CMD_SET_TX_PARAMS, 14, 0x02])
        time.sleep_ms(10)
        
        # Set IRQ params - Enable all IRQs on DIO1
        self.spi_transaction([self.CMD_SET_DIO_IRQ_PARAMS,
                             0xFF, 0xFF,  # Enable all IRQs
                             0xFF, 0xFF,  # Map all to DIO1
                             0x00, 0x00,  # None to DIO2
                             0x00, 0x00]) # None to DIO3
        time.sleep_ms(10)
        
        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        
        print("✓ Basic initialization completed")
        self.print_status("Init: ")
        return True
    
    def send_data_diagnostic(self, data):
        """Send data with comprehensive diagnostics"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"\n=== DIAGNOSTIC TRANSMISSION ===")
        print(f"Data: {data} ({len(data)} bytes)")
        
        # Pre-transmission status
        print("\n1. Pre-transmission status:")
        self.print_status("  ")
        
        # Set standby
        print("\n2. Setting standby mode...")
        result = self.spi_transaction([self.CMD_SET_STANDBY, 0x00])
        print(f"  Standby command result: {result}")
        time.sleep_ms(10)
        self.print_status("  ")
        
        # Clear IRQs
        print("\n3. Clearing IRQ flags...")
        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        time.sleep_ms(10)
        self.print_status("  ")
        
        # Write data to buffer
        print("\n4. Writing data to buffer...")
        write_cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        result = self.spi_transaction(write_cmd)
        print(f"  Buffer write result: {result}")
        
        # Update packet length
        print("\n5. Setting packet parameters...")
        result = self.spi_transaction([self.CMD_SET_PACKET_PARAMS, 0x00, 0x0C, 0x00, len(data), 0x01, 0x00])
        print(f"  Packet params result: {result}")
        
        # Check status before TX
        print("\n6. Status before transmission:")
        self.print_status("  ")
        
        # Start transmission
        print("\n7. Starting transmission...")
        result = self.spi_transaction([self.CMD_SET_TX, 0x00, 0x00, 0x00])
        print(f"  TX command result: {result}")
        time.sleep_ms(50)  # Give it time to start
        
        # Monitor transmission
        print("\n8. Monitoring transmission...")
        for i in range(100):  # Check for 10 seconds
            self.print_status(f"  Check {i:2d}: ")
            
            # Check if DIO1 is high
            if self.dio1.value():
                print("  >>> DIO1 is HIGH - Checking IRQ status...")
                irq_info = self.get_irq_status()
                if irq_info and irq_info['raw'] != 0:
                    print(f"  >>> Active IRQs detected!")
                    
                    if self.IRQ_TX_DONE & irq_info['raw']:
                        print("  ✓ TX_DONE detected!")
                        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return True
                    elif self.IRQ_TIMEOUT & irq_info['raw']:
                        print("  ✗ TIMEOUT detected!")
                        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                        return False
                    else:
                        print(f"  >>> Other IRQ: {irq_info['active']}")
            
            time.sleep_ms(100)
        
        print("\n9. Final status:")
        self.print_status("  ")
        print("✗ Transmission monitoring timeout")
        return False
    
    def receive_data_diagnostic(self, timeout_ms=10000):
        """Receive data with diagnostics"""
        print(f"\n=== DIAGNOSTIC RECEPTION ===")
        print(f"Timeout: {timeout_ms}ms")
        
        # Pre-reception status
        print("\n1. Pre-reception status:")
        self.print_status("  ")
        
        # Set standby
        self.spi_transaction([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        # Clear IRQs
        self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
        time.sleep_ms(10)
        
        # Calculate timeout
        timeout_steps = int(timeout_ms * 1000 / 15.625)
        if timeout_steps > 0xFFFFFF:
            timeout_steps = 0xFFFFFF
        
        # Start reception
        print("\n2. Starting reception...")
        rx_cmd = [self.CMD_SET_RX, (timeout_steps >> 16) & 0xFF, (timeout_steps >> 8) & 0xFF, timeout_steps & 0xFF]
        result = self.spi_transaction(rx_cmd)
        print(f"  RX command result: {result}")
        time.sleep_ms(50)
        
        print("\n3. Status after RX start:")
        self.print_status("  ")
        
        # Monitor reception
        print("\n4. Monitoring reception...")
        start_time = time.ticks_ms()
        check_count = 0
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            check_count += 1
            
            if check_count % 50 == 0:  # Print status every 5 seconds
                print(f"  Check {check_count}: Still listening...")
                self.print_status("    ")
            
            # Check IRQ status
            irq_info = self.get_irq_status()
            if irq_info and irq_info['raw'] != 0:
                print(f"\n  >>> IRQ detected: {irq_info['active']}")
                
                if self.IRQ_RX_DONE & irq_info['raw']:
                    print("  ✓ RX_DONE detected!")
                    
                    # Get buffer status
                    buffer_response = self.spi_transaction([self.CMD_GET_RX_BUFFER_STATUS, 0x00], 3)
                    if buffer_response and len(buffer_response) >= 3:
                        payload_length = buffer_response[1]
                        buffer_offset = buffer_response[2]
                        print(f"  Payload: {payload_length} bytes at offset {buffer_offset}")
                        
                        if payload_length > 0:
                            # Read data
                            data_response = self.spi_transaction([self.CMD_READ_BUFFER, buffer_offset], payload_length)
                            if data_response:
                                self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                                try:
                                    decoded = bytes(data_response).decode('utf-8', errors='ignore')
                                    print(f"  ✓ Received: '{decoded}'")
                                except:
                                    print(f"  ✓ Received: {bytes(data_response)}")
                                return bytes(data_response)
                
                elif self.IRQ_TIMEOUT & irq_info['raw']:
                    print("  Reception timeout")
                    self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
                    break
                else:
                    # Clear other IRQs and continue
                    self.spi_transaction([self.CMD_CLEAR_IRQ_STATUS, 0xFF, 0xFF])
            
            time.sleep_ms(100)
        
        print("\nNo packet received")
        return None


def test_diagnostic():
    """Run diagnostic tests"""
    print("=== SX1262 DIAGNOSTIC TEST ===")
    
    try:
        lora = SX1262()
        
        print("\nSelect diagnostic mode:")
        print("1. Send diagnostic test")
        print("2. Receive diagnostic test")
        print("3. Status monitoring only")
        
        mode = 1  # Default to send test
        
        if mode == 1:
            print("\n=== DIAGNOSTIC SEND TEST ===")
            counter = 0
            while True:
                message = f"TEST-{counter:03d}"
                print(f"\n{'='*60}")
                print(f"DIAGNOSTIC SEND ATTEMPT {counter}")
                print(f"{'='*60}")
                
                success = lora.send_data_diagnostic(message)
                
                if success:
                    print(f"\n✓ DIAGNOSTIC: Message '{message}' sent successfully!")
                else:
                    print(f"\n✗ DIAGNOSTIC: Failed to send '{message}'")
                
                counter += 1
                time.sleep(5)
                
        elif mode == 2:
            print("\n=== DIAGNOSTIC RECEIVE TEST ===")
            while True:
                received = lora.receive_data_diagnostic(timeout_ms=30000)
                if received:
                    print("✓ DIAGNOSTIC: Message received!")
                else:
                    print("- DIAGNOSTIC: No message in timeout period")
                
        elif mode == 3:
            print("\n=== STATUS MONITORING ===")
            while True:
                lora.print_status("Monitor: ")
                time.sleep(2)
        
    except KeyboardInterrupt:
        print("\nDiagnostic stopped by user")
    except Exception as e:
        print(f"Diagnostic error: {e}")
        import traceback
        traceback.print_exc()

# Run diagnostic
if __name__ == "__main__":
    test_diagnostic()