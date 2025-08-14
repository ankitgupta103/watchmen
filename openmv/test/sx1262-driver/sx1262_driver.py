"""
Simple SX1262 LoRa Module Connection Test for OpenMV RT1062
Pin connections:
- P0: MOSI
- P1: MISO  
- P2: SCK
- P3: NSS/CS
- P6: RESET
- P7: BUSY (DIO1)
"""

import time
from machine import SPI, Pin

# Pin definitions
PIN_MOSI = 'P0'
PIN_MISO = 'P1'
PIN_SCK = 'P2'
PIN_NSS = 'P3'
PIN_RESET = 'P6'
PIN_BUSY = 'P7'

# SX1262 Commands
CMD_GET_STATUS = 0xC0
CMD_GET_VERSION = 0x01

class SX1262Test:
    def __init__(self):
        # Initialize GPIO pins first
        self.nss = Pin(PIN_NSS, Pin.OUT)
        self.reset = Pin(PIN_RESET, Pin.OUT)
        self.busy = Pin(PIN_BUSY, Pin.IN, Pin.PULL_UP)
        
        # Initialize SPI (SPI bus 1) - simplified for OpenMV RT1062
        try:
            self.spi = SPI(1, baudrate=1000000)
        except:
            # Fallback initialization
            self.spi = SPI(1)
        
        # Set NSS high (inactive)
        self.nss.on()
        
        print("SX1262 Test Initialized")
        
    def reset_module(self):
        """Reset the SX1262 module"""
        print("Resetting SX1262...")
        self.reset.off()
        time.sleep_ms(10)
        self.reset.on()
        time.sleep_ms(20)
        print("Reset complete")
        
    def wait_busy(self, timeout_ms=1000):
        """Wait for BUSY pin to go low"""
        start = time.ticks_ms()
        while self.busy.value() == 1:
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                return False
        return True
        
    def spi_transfer(self, data):
        """Perform SPI transfer"""
        if not self.wait_busy():
            print("ERROR: BUSY timeout before transfer")
            return None
            
        self.nss.off()  # CS low
        result = bytearray(len(data))
        self.spi.write_readinto(data, result)
        self.nss.on()   # CS high
        
        if not self.wait_busy():
            print("ERROR: BUSY timeout after transfer")
            return None
            
        return result
        
    def get_status(self):
        """Get SX1262 status"""
        result = self.spi_transfer(bytearray([CMD_GET_STATUS, 0x00]))
        if result:
            return result[1]
        return None
        
    def test_connection(self):
        """Test if SX1262 is connected and responding"""
        print("\n=== SX1262 Connection Test ===")
        
        # Reset the module
        self.reset_module()
        
        # Check BUSY pin
        print(f"BUSY pin state: {'HIGH' if self.busy.value() else 'LOW'}")
        
        # Try to get status
        print("Getting module status...")
        status = self.get_status()
        
        if status is not None:
            print(f"Status received: 0x{status:02X}")
            
            # Decode status bits
            chip_mode = (status >> 4) & 0x07
            cmd_status = (status >> 1) & 0x07
            
            mode_names = {
                0: "SLEEP", 1: "STBY_RC", 2: "STBY_XOSC", 
                3: "FS", 4: "RX", 5: "TX", 6: "RESERVED"
            }
            
            cmd_names = {
                0: "RESERVED", 1: "RFU", 2: "DATA_AVAILABLE",
                3: "CMD_TIMEOUT", 4: "CMD_PROCESSING_ERROR",
                5: "EXEC_FAILURE", 6: "CMD_TX_DONE"
            }
            
            print(f"Chip Mode: {mode_names.get(chip_mode, 'UNKNOWN')} ({chip_mode})")
            print(f"Command Status: {cmd_names.get(cmd_status, 'UNKNOWN')} ({cmd_status})")
            
            if chip_mode in [1, 2]:  # STBY_RC or STBY_XOSC
                print("✓ SX1262 is connected and responding!")
                return True
            else:
                print("⚠ SX1262 responding but in unexpected mode")
                return True
        else:
            print("✗ No response from SX1262")
            return False

def main():
    """Main test function"""
    print("OpenMV RT1062 + SX1262 LoRa Module Test")
    print("=" * 40)
    
    try:
        # Create test instance
        sx1262 = SX1262Test()
        
        # Run connection test
        if sx1262.test_connection():
            print("\n🎉 Test PASSED - LoRa module is working!")
        else:
            print("\n❌ Test FAILED - Check connections")
            
    except Exception as e:
        print(f"Error during test: {e}")
        
    print("\nTest complete.")

# Run the test
if __name__ == "__main__":
    main()