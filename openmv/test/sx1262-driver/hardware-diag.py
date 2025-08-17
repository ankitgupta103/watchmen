# Hardware diagnostic for SX1262 Core1262 module
import time
from machine import SPI, Pin

def comprehensive_hardware_test():
    """Comprehensive hardware test for Core1262 module"""
    print("=== SX1262 Core1262 Hardware Diagnostic ===")
    
    # Initialize SPI and pins
    spi = SPI(1)
    spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
    
    nss = Pin('P3', Pin.OUT)
    reset = Pin('P6', Pin.OUT)
    busy = Pin('P7', Pin.IN)
    dio1 = Pin('P13', Pin.IN)
    
    nss.on()
    reset.on()
    
    def wait_busy():
        timeout = 10000
        while busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        return timeout > 0
    
    def send_command(cmd):
        if not wait_busy():
            print(f"BUSY timeout before command")
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
    
    def get_errors():
        if not wait_busy():
            return None
        nss.off()
        spi.write(bytes([0x17, 0x00]))
        data = spi.read(2, 0x00)
        nss.on()
        if data:
            return (data[0] << 8) | data[1]
        return None
    
    # Hardware reset
    print("\n1. Testing hardware reset...")
    reset.off()
    time.sleep_ms(10)
    reset.on()
    time.sleep_ms(100)
    
    if not wait_busy():
        print("   FAIL: BUSY stuck high after reset")
        return False
    else:
        print("   PASS: BUSY went low after reset")
    
    # Test SPI communication
    print("\n2. Testing SPI communication...")
    status = get_status()
    if status is None:
        print("   FAIL: No SPI response")
        return False
    else:
        print(f"   PASS: Status = 0x{status:02X}")
    
    # Test different standby modes
    print("\n3. Testing standby modes...")
    
    # STDBY_RC
    print("   Testing STDBY_RC...")
    send_command([0x80, 0x00])
    time.sleep_ms(50)
    status = get_status()
    mode = (status >> 4) & 0x7
    print(f"     Status: 0x{status:02X}, Mode: {mode} {'(STDBY_RC)' if mode == 2 else '(WRONG)'}")
    
    # Try STDBY_XOSC
    print("   Testing STDBY_XOSC...")
    send_command([0x80, 0x01])
    time.sleep_ms(200)  # Give XOSC time to start
    status = get_status()
    mode = (status >> 4) & 0x7
    print(f"     Status: 0x{status:02X}, Mode: {mode} {'(STDBY_XOSC)' if mode == 3 else '(FAILED - Crystal issue)'}")
    
    xosc_works = (mode == 3)
    
    # Check errors
    errors = get_errors()
    if errors:
        print(f"   Device errors: 0x{errors:04X}")
        if errors & 0x01: print("     - RC64K_CALIB_ERR")
        if errors & 0x02: print("     - RC13M_CALIB_ERR") 
        if errors & 0x04: print("     - PLL_CALIB_ERR")
        if errors & 0x08: print("     - ADC_CALIB_ERR")
        if errors & 0x10: print("     - IMG_CALIB_ERR")
        if errors & 0x20: print("     - XOSC_START_ERR")
        if errors & 0x40: print("     - PLL_LOCK_ERR")
    else:
        print("   No device errors")
    
    # Test TCXO mode if XOSC fails
    if not xosc_works:
        print("\n4. Testing TCXO mode (since XOSC failed)...")
        
        # Go back to STDBY_RC
        send_command([0x80, 0x00])
        time.sleep_ms(50)
        
        # Try to enable TCXO on DIO3
        print("   Attempting to enable TCXO...")
        # SetDIO3AsTCXOCtrl: voltage=1.8V, timeout=320us
        send_command([0x97, 0x02, 0x00, 0x00, 0x20])
        time.sleep_ms(100)
        
        # Now try STDBY_XOSC with TCXO
        send_command([0x80, 0x01])
        time.sleep_ms(200)
        
        status = get_status()
        mode = (status >> 4) & 0x7
        print(f"     TCXO mode result - Status: 0x{status:02X}, Mode: {mode}")
        
        if mode == 3:
            print("   SUCCESS: TCXO mode works!")
            return True
        else:
            print("   FAIL: TCXO mode also failed")
    
    # Test different regulator modes
    print("\n5. Testing regulator modes...")
    
    # Go back to STDBY_RC for regulator test
    send_command([0x80, 0x00])
    time.sleep_ms(50)
    
    # Test LDO mode
    print("   Testing LDO regulator...")
    send_command([0x96, 0x00])  # LDO mode
    time.sleep_ms(10)
    status = get_status()
    print(f"     LDO mode status: 0x{status:02X}")
    
    # Test DC-DC mode
    print("   Testing DC-DC regulator...")
    send_command([0x96, 0x01])  # DC-DC mode
    time.sleep_ms(10)
    status = get_status()
    print(f"     DC-DC mode status: 0x{status:02X}")
    
    # Summary
    print("\n=== DIAGNOSTIC SUMMARY ===")
    if xosc_works:
        print("✓ External crystal oscillator works")
        print("→ Standard initialization should work")
    else:
        print("✗ External crystal oscillator FAILED")
        print("→ Module may need TCXO configuration")
        print("→ Check crystal circuit on module")
        print("→ Verify 3.3V power supply stability")
    
    return xosc_works

def test_tcxo_configuration():
    """Test TCXO configuration if crystal fails"""
    print("\n=== TESTING TCXO CONFIGURATION ===")
    
    # This is for modules that might have TCXO instead of crystal
    # Based on Core1262 documentation, some variants use TCXO
    
    spi = SPI(1)
    spi.init(baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
    
    nss = Pin('P3', Pin.OUT)
    reset = Pin('P6', Pin.OUT) 
    busy = Pin('P7', Pin.IN)
    
    nss.on()
    reset.on()
    
    def wait_busy():
        timeout = 10000
        while busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        return timeout > 0
    
    def send_command(cmd):
        if not wait_busy():
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
    
    # Reset
    reset.off()
    time.sleep_ms(10)
    reset.on()
    time.sleep_ms(100)
    
    # Start in STDBY_RC
    send_command([0x80, 0x00])
    time.sleep_ms(50)
    
    # Try different TCXO voltages
    tcxo_voltages = [
        (0x02, "1.8V"),
        (0x03, "2.2V"), 
        (0x04, "2.4V"),
        (0x05, "2.7V"),
        (0x06, "3.0V"),
        (0x07, "3.3V")
    ]
    
    for voltage_code, voltage_name in tcxo_voltages:
        print(f"Testing TCXO at {voltage_name}...")
        
        # Reset to clean state
        send_command([0x80, 0x00])
        time.sleep_ms(50)
        
        # Set TCXO
        send_command([0x97, voltage_code, 0x00, 0x00, 0x40])  # 1ms timeout
        time.sleep_ms(100)
        
        # Try STDBY_XOSC
        send_command([0x80, 0x01])
        time.sleep_ms(200)
        
        status = get_status()
        mode = (status >> 4) & 0x7
        print(f"  Result: Status=0x{status:02X}, Mode={mode}")
        
        if mode == 3:
            print(f"  SUCCESS: TCXO works at {voltage_name}!")
            return voltage_code
    
    print("No TCXO voltage worked")
    return None

if __name__ == "__main__":
    if not comprehensive_hardware_test():
        print("\nTrying TCXO configuration...")
        tcxo_voltage = test_tcxo_configuration()
        if tcxo_voltage:
            print(f"\nFound working TCXO voltage: {tcxo_voltage}")
        else:
            print("\nHardware issue detected - check:")
            print("- 3.3V power supply")
            print("- SPI connections")
            print("- Module crystal/TCXO circuit")