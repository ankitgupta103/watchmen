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
        return data
    
    def init_lora(self):
        """Initialize LoRa configuration"""
        print("Initializing SX1262...")
        
        # Set standby mode
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        # Set regulator mode (DC-DC)
        self.spi_write([self.CMD_SET_REGULATOR_MODE, 0x01])
        
        # Calibrate
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(10)
        
        # Set PA config for SX1262
        self.spi_write([self.CMD_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01])
        
        # Set packet type to LoRa
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        
        # Set RF frequency (868 MHz)
        freq_raw = int((868000000 * (1 << 25)) / 32000000)
        self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                       (freq_raw >> 24) & 0xFF,
                       (freq_raw >> 16) & 0xFF, 
                       (freq_raw >> 8) & 0xFF,
                       freq_raw & 0xFF])
        
        # Set TX power (22 dBm) and ramp time
        self.spi_write([self.CMD_SET_TX_PARAMS, 22, 0x02])  # 22dBm, 40us ramp
        
        # Set modulation params (SF7, BW125, CR4/5, LDRO off)
        self.spi_write([self.CMD_SET_MODULATION_PARAMS, 
                       0x07,  # SF7
                       0x04,  # BW125
                       0x01,  # CR4/5
                       0x00]) # LDRO off
        
        # Set packet params (12 symbols preamble, explicit header, 255 max payload, CRC on, normal IQ)
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x0C,  # Preamble length (12)
                       0x00,        # Explicit header
                       0xFF,        # Payload length (255 max)
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        
        # Set buffer base addresses
        self.spi_write([self.CMD_SET_BUFFER_BASE_ADDRESS, 0x00, 0x00])
        
        # Set DIO IRQ params
        self.spi_write([self.CMD_SET_DIO_IRQ_PARAMS,
                       0x02, 0x03,  # IRQ mask (TX_DONE | RX_DONE | TIMEOUT)
                       0x02, 0x03,  # DIO1 mask
                       0x00, 0x00,  # DIO2 mask
                       0x00, 0x00]) # DIO3 mask
        
        print("SX1262 initialized successfully!")
    
    def send_data(self, data):
        """Send data via LoRa"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        print(f"Sending: {data}")
        
        # Write data to buffer
        cmd = [self.CMD_WRITE_BUFFER, 0x00] + list(data)
        self.spi_write(cmd)
        
        # Update packet params with actual payload length
        self.spi_write([self.CMD_SET_PACKET_PARAMS,
                       0x00, 0x0C,  # Preamble length
                       0x00,        # Explicit header
                       len(data),   # Actual payload length
                       0x01,        # CRC on
                       0x00])       # Normal IQ
        
        # Set TX mode with timeout (5 seconds)
        timeout = 5000000 // 15.625  # Convert to internal units
        self.spi_write([self.CMD_SET_TX,
                       (timeout >> 16) & 0xFF,
                       (timeout >> 8) & 0xFF,
                       timeout & 0xFF])
        
        # Wait for TX done
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < 5000:
            if self.dio1.value():
                # Check IRQ status
                irq_status = self.spi_read([self.CMD_GET_IRQ_STATUS, 0x00], 3)
                irq = (irq_status[1] << 8) | irq_status[2]
                
                if irq & self.IRQ_TX_DONE:
                    print("TX Done!")
                    # Clear IRQ
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0x02, 0x03])
                    return True
                elif irq & self.IRQ_TIMEOUT:
                    print("TX Timeout!")
                    self.spi_write([self.CMD_CLEAR_IRQ_STATUS, 0x02, 0x03])
                    return False
            time.sleep_ms(10)
        
        print("TX failed - no response")
        return False
    
    def receive_data(self, timeout_ms=30000):
        """Receive data via LoRa"""
        print("Listening for data...")
        
        # Set RX mode with timeout
        timeout = timeout_ms * 1000 // 15.625  # Convert to internal units
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
# main()