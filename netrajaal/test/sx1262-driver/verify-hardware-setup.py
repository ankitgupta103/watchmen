# Simple connection test for SX1262
import time
from machine import SPI, Pin

def test_spi_connection():
    """Test basic SPI connection to SX1262"""
    print("Testing SPI connection...")
    
    # Initialize SPI and pins
    spi = SPI(1)
    spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
    
    nss = Pin('P3', Pin.OUT)
    reset = Pin('P6', Pin.OUT)
    busy = Pin('P7', Pin.IN)
    dio1 = Pin('P13', Pin.IN)
    
    # Initialize pins
    nss.on()   # Deselect
    reset.on() # Not in reset
    
    print(f"Initial pin states:")
    print(f"  NSS: {nss.value()}")
    print(f"  RESET: {reset.value()}")
    print(f"  BUSY: {busy.value()}")
    print(f"  DIO1: {dio1.value()}")
    
    # Hardware reset
    print("\nPerforming hardware reset...")
    reset.off()
    time.sleep_ms(10)
    reset.on()
    time.sleep_ms(100)
    
    print(f"After reset - BUSY: {busy.value()}")
    
    # Wait for BUSY to go low
    timeout = 100
    while busy.value() and timeout > 0:
        time.sleep_ms(10)
        timeout -= 1
    
    if timeout == 0:
        print("ERROR: BUSY pin stuck high after reset!")
        return False
    else:
        print("BUSY pin went low - good!")
    
    # Try to read status
    print("\nTesting SPI communication...")
    try:
        nss.off()  # Select device
        spi.write(bytes([0xC0, 0x00]))  # GetStatus command
        status_data = spi.read(1, 0x00)
        nss.on()   # Deselect
        
        if status_data:
            status = status_data[0]
            print(f"Status register: 0x{status:02X}")
            
            chip_mode = (status >> 4) & 0x7
            cmd_status = (status >> 1) & 0x7
            
            print(f"  Chip mode: {chip_mode}")
            print(f"  Command status: {cmd_status}")
            
            if chip_mode == 2:  # STDBY_RC
                print("  Device is in STDBY_RC mode - GOOD!")
                return True
            else:
                print(f"  Unexpected chip mode: {chip_mode}")
                return True  # Still communicating
        else:
            print("ERROR: No response from SPI")
            return False
            
    except Exception as e:
        print(f"ERROR: SPI communication failed: {e}")
        return False

def test_basic_commands():
    """Test sending basic commands"""
    print("\nTesting basic commands...")
    
    # Initialize SPI and pins
    spi = SPI(1)
    spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
    
    nss = Pin('P3', Pin.OUT)
    reset = Pin('P6', Pin.OUT)
    busy = Pin('P7', Pin.IN)
    
    nss.on()
    reset.on()
    
    def wait_busy():
        timeout = 1000
        while busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        return timeout > 0
    
    def send_command(cmd):
        if not wait_busy():
            print(f"BUSY timeout before command: {cmd}")
            return False
        
        nss.off()
        spi.write(bytes(cmd))
        nss.on()
        time.sleep_ms(10)
        return True
    
    def get_status():
        if not wait_busy():
            return None
        nss.off()
        spi.write(bytes([0xC0, 0x00]))
        data = spi.read(1, 0x00)
        nss.on()
        return data[0] if data else None
    
    # Reset device
    reset.off()
    time.sleep_ms(10)
    reset.on()
    time.sleep_ms(100)
    
    # Test commands
    commands = [
        ([0x80, 0x00], "SetStandby"),
        ([0x96, 0x01], "SetRegulatorMode"),
        ([0x8A, 0x01], "SetPacketType"),
    ]
    
    for cmd, name in commands:
        print(f"Sending {name}...")
        if send_command(cmd):
            status = get_status()
            if status is not None:
                print(f"  Status after {name}: 0x{status:02X}")
            else:
                print(f"  Failed to read status after {name}")
        else:
            print(f"  Failed to send {name}")
    
    print("\nBasic command test complete")

if __name__ == "__main__":
    if test_spi_connection():
        test_basic_commands()
    else:
        print("\nConnection test failed - check wiring!")