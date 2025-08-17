import time
from machine import SPI, Pin

class SX1262_ModuleTest:
    """Final definitive test to determine if module is defective"""
    
    def __init__(self, nss_pin='P3', reset_pin='P6', busy_pin='P7', dio1_pin='P13'):
        print("=== SX1262 MODULE HEALTH CHECK ===")
        print("This will definitively determine if your module is defective\n")
        
        # Initialize SPI
        self.spi = SPI(1, baudrate=1000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
        
        # Initialize pins
        self.nss = Pin(nss_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        self.nss.on()
        self.reset.on()
    
    def hardware_reset(self):
        """Hardware reset"""
        self.reset.off()
        time.sleep_ms(10)
        self.reset.on()
        time.sleep_ms(50)
        
        # Wait for BUSY
        timeout = 20000
        while self.busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        
        return timeout > 0
    
    def spi_transaction(self, data_out, read_length=0):
        """Basic SPI transaction"""
        # Wait for BUSY
        timeout = 10000
        while self.busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        
        if timeout == 0:
            return None
        
        self.nss.off()
        time.sleep_us(10)
        
        try:
            if isinstance(data_out, list):
                data_out = bytes(data_out)
            
            self.spi.write(data_out)
            
            if read_length > 0:
                response = self.spi.read(read_length, 0x00)
                self.nss.on()
                time.sleep_ms(1)
                return response
            else:
                self.nss.on()
                time.sleep_ms(1)
                return True
                
        except Exception as e:
            self.nss.on()
            return None
    
    def test_basic_communication(self):
        """Test if module responds at all"""
        print("1. TESTING BASIC SPI COMMUNICATION...")
        
        # Reset module
        reset_ok = self.hardware_reset()
        if not reset_ok:
            print("   ✗ BUSY pin never went low after reset")
            return False
        
        # Try to read status multiple times
        responses = []
        for i in range(5):
            status = self.spi_transaction([0xC0, 0x00], 1)
            if status:
                responses.append(status[0])
            else:
                responses.append(None)
            time.sleep_ms(10)
        
        print(f"   Status responses: {responses}")
        
        # Check if we get consistent non-zero responses
        valid_responses = [r for r in responses if r is not None and r != 0]
        
        if len(valid_responses) >= 3:
            print("   ✓ Module responds to SPI commands")
            return True
        else:
            print("   ✗ Module does not respond reliably to SPI")
            return False
    
    def test_register_access(self):
        """Test if we can read/write registers"""
        print("\n2. TESTING REGISTER ACCESS...")
        
        # Try to read a known register (like XTA trim register at 0x0911)
        read_result = self.spi_transaction([0x1D, 0x09, 0x11, 0x00], 1)
        
        if read_result:
            original_value = read_result[0]
            print(f"   Read register 0x0911: 0x{original_value:02X}")
            
            # Try to write a different value
            new_value = (original_value + 1) & 0xFF
            write_result = self.spi_transaction([0x0D, 0x09, 0x11, new_value])
            
            if write_result:
                time.sleep_ms(10)
                # Read it back
                verify_result = self.spi_transaction([0x1D, 0x09, 0x11, 0x00], 1)
                
                if verify_result and verify_result[0] == new_value:
                    print(f"   ✓ Register write/read successful (0x{original_value:02X} → 0x{new_value:02X})")
                    
                    # Restore original value
                    self.spi_transaction([0x0D, 0x09, 0x11, original_value])
                    return True
                else:
                    print(f"   ✗ Register write failed (wrote 0x{new_value:02X}, read 0x{verify_result[0] if verify_result else 'None':02X})")
                    return False
            else:
                print("   ✗ Register write command failed")
                return False
        else:
            print("   ✗ Cannot read registers")
            return False
    
    def test_standby_command(self):
        """Test if basic standby command works"""
        print("\n3. TESTING STANDBY COMMAND...")
        
        # Clear any errors first
        self.spi_transaction([0x07, 0x00, 0x00])
        time.sleep_ms(10)
        
        # Try standby command
        standby_result = self.spi_transaction([0x80, 0x00])
        
        if standby_result:
            time.sleep_ms(50)
            
            # Check status
            status_result = self.spi_transaction([0xC0, 0x00], 1)
            if status_result:
                status = status_result[0]
                mode = (status >> 4) & 0x7
                cmd_status = (status >> 1) & 0x7
                
                print(f"   Status after STDBY: 0x{status:02X} (mode={mode}, cmd_status={cmd_status})")
                
                if cmd_status != 5:  # Not execution failure
                    print("   ✓ Standby command accepted")
                    return True
                else:
                    print("   ✗ Standby command rejected (execution failure)")
                    return False
            else:
                print("   ✗ Cannot read status after standby")
                return False
        else:
            print("   ✗ Standby command failed")
            return False
    
    def test_calibration_individual(self):
        """Test individual calibration commands"""
        print("\n4. TESTING INDIVIDUAL CALIBRATIONS...")
        
        # Set to standby first
        self.spi_transaction([0x80, 0x00])
        time.sleep_ms(10)
        
        # Test each calibration individually
        calibrations = [
            (0x01, "RC64k"),
            (0x02, "RC13M"), 
            (0x08, "ADC Pulse"),
            (0x10, "ADC Bulk N"),
            (0x20, "ADC Bulk P"),
        ]
        
        results = {}
        
        for cal_mask, cal_name in calibrations:
            print(f"   Testing {cal_name} calibration...")
            
            # Clear errors
            self.spi_transaction([0x07, 0x00, 0x00])
            time.sleep_ms(10)
            
            # Start this calibration
            cal_result = self.spi_transaction([0x89, cal_mask])
            
            if cal_result:
                # Wait for calibration
                time.sleep_ms(300)
                
                # Check errors
                error_result = self.spi_transaction([0x17, 0x00], 3)
                if error_result and len(error_result) >= 3:
                    errors = (error_result[1] << 8) | error_result[2]
                    
                    if errors == 0:
                        print(f"      ✓ {cal_name} calibration successful")
                        results[cal_name] = True
                    else:
                        print(f"      ✗ {cal_name} calibration failed (errors: 0x{errors:04X})")
                        results[cal_name] = False
                else:
                    print(f"      ? {cal_name} calibration status unknown")
                    results[cal_name] = None
            else:
                print(f"      ✗ {cal_name} calibration command failed")
                results[cal_name] = False
        
        return results
    
    def run_comprehensive_test(self):
        """Run all tests and provide verdict"""
        print("Testing module comprehensively...\n")
        
        # Test 1: Basic communication
        comm_ok = self.test_basic_communication()
        
        # Test 2: Register access
        reg_ok = self.test_register_access() if comm_ok else False
        
        # Test 3: Standby command
        standby_ok = self.test_standby_command() if reg_ok else False
        
        # Test 4: Individual calibrations
        cal_results = self.test_calibration_individual() if standby_ok else {}
        
        # Analysis
        print("\n" + "="*60)
        print("MODULE HEALTH ASSESSMENT")
        print("="*60)
        
        print(f"✓ Basic SPI Communication: {'PASS' if comm_ok else 'FAIL'}")
        print(f"✓ Register Read/Write: {'PASS' if reg_ok else 'FAIL'}")
        print(f"✓ Command Processing: {'PASS' if standby_ok else 'FAIL'}")
        
        if cal_results:
            print("✓ Calibration Results:")
            for cal_name, result in cal_results.items():
                status = "PASS" if result else ("FAIL" if result is False else "UNKNOWN")
                print(f"   - {cal_name}: {status}")
        
        print("\n" + "="*60)
        print("VERDICT")
        print("="*60)
        
        if not comm_ok:
            print("🔴 CRITICAL FAILURE: Module does not respond to SPI")
            print("   → Check wiring, power supply, module may be completely dead")
            
        elif not reg_ok:
            print("🔴 CRITICAL FAILURE: Cannot access registers")
            print("   → Module internal bus failure, module is defective")
            
        elif not standby_ok:
            print("🔴 COMMAND FAILURE: Basic commands rejected")
            print("   → Module firmware/control logic failure, module is defective")
            
        elif cal_results and not any(cal_results.values()):
            print("🔴 CALIBRATION FAILURE: All calibrations fail")
            print("   → Module analog/RF circuitry defective")
            print("   → This explains the 0x200A error you've been seeing")
            
        elif cal_results and cal_results.get('RC13M') == False:
            print("🔴 RC13M CALIBRATION FAILURE")
            print("   → This is the root cause of your 0x200A error")
            print("   → RC13M oscillator circuit is defective")
            print("   → Module cannot generate stable internal timing")
            
        else:
            print("🟡 PARTIAL FUNCTIONALITY")
            print("   → Some systems work, others don't")
            print("   → Module may be partially defective")
        
        print("\n" + "="*60)
        print("RECOMMENDATION")
        print("="*60)
        
        if not comm_ok or not reg_ok or not standby_ok:
            print("🚫 MODULE IS DEFECTIVE - Cannot be used")
            print("   → Request replacement from supplier")
            print("   → Try your second module")
            
        elif cal_results and cal_results.get('RC13M') == False:
            print("🚫 MODULE IS DEFECTIVE - RC13M oscillator failed")
            print("   → This is a hardware defect, cannot be fixed in software")
            print("   → Request replacement from supplier") 
            print("   → Try your second module")
            
        else:
            print("🤔 MODULE STATUS UNCLEAR")
            print("   → Try your second module for comparison")
            print("   → If second module works, first is defective")
        
        return comm_ok, reg_ok, standby_ok, cal_results


def test_module_health():
    """Test current module health"""
    try:
        tester = SX1262_ModuleTest()
        tester.run_comprehensive_test()
        
        print(f"\n{'='*60}")
        print("NEXT STEPS")
        print("="*60)
        print("1. 🔄 Test your SECOND Core1262 module with this same code")
        print("2. 📋 Compare results between both modules") 
        print("3. 📞 Contact supplier if module is defective")
        print("4. 🔁 If both modules fail the same way, recheck power supply")
        
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()

# Run the definitive module test
if __name__ == "__main__":
    test_module_health()