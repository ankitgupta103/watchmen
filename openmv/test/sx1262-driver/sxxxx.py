import time
from machine import SPI, Pin

class SX1262:
    """SX1262 Hardware Diagnostic Tests"""
    
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
    CMD_SET_FS = 0xC1
    CMD_SET_TX_CONTINUOUS_WAVE = 0xD1
    
    # Packet types
    PACKET_TYPE_LORA = 0x01
    
    def __init__(self, nss_pin='P3', reset_pin='P6', busy_pin='P7', dio1_pin='P13'):
        """Initialize for hardware diagnostics"""
        
        print("=== SX1262 Hardware Diagnostic Setup ===")
        
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
        
        # Basic setup
        self.hardware_reset()
        self.basic_init()
    
    def hardware_reset(self):
        """Hardware reset"""
        print("Hardware reset...")
        self.reset.off()
        time.sleep_ms(10)
        self.reset.on()
        time.sleep_ms(20)
        self.wait_busy()
        print("✓ Reset completed")
    
    def wait_busy(self, timeout_ms=1000):
        """Wait for BUSY pin"""
        timeout = 10000
        while self.busy.value() and timeout > 0:
            time.sleep_us(100)
            timeout -= 1
        return timeout > 0
    
    def spi_write(self, data):
        """SPI write"""
        self.wait_busy()
        self.nss.off()
        time.sleep_us(10)
        
        if isinstance(data, list):
            data = bytes(data)
        
        try:
            self.spi.write(data)
            time.sleep_us(10)
        except Exception as e:
            print(f"SPI write error: {e}")
            self.nss.on()
            return False
        finally:
            self.nss.on()
            
        time.sleep_ms(1)
        return True
    
    def spi_read(self, cmd, length):
        """SPI read"""
        self.wait_busy()
        self.nss.off()
        time.sleep_us(10)
        
        try:
            if isinstance(cmd, list):
                cmd = bytes(cmd)
            self.spi.write(cmd)
            time.sleep_us(10)
            data = self.spi.read(length, 0x00)
            time.sleep_us(10)
        except Exception as e:
            print(f"SPI read error: {e}")
            self.nss.on()
            return None
        finally:
            self.nss.on()
            
        time.sleep_ms(1)
        return data
    
    def get_status(self):
        """Get status"""
        try:
            status = self.spi_read([self.CMD_GET_STATUS, 0x00], 1)
            return status[0] if status else 0
        except:
            return 0
    
    def get_errors(self):
        """Get device errors"""
        try:
            error_data = self.spi_read([self.CMD_GET_DEVICE_ERRORS, 0x00], 3)
            if error_data and len(error_data) >= 3:
                return (error_data[1] << 8) | error_data[2]
        except:
            pass
        return 0
    
    def clear_errors(self):
        """Clear errors"""
        self.spi_write([self.CMD_CLEAR_DEVICE_ERRORS, 0x00, 0x00])
    
    def basic_init(self):
        """Basic initialization for testing"""
        print("Basic initialization...")
        
        # Clear errors
        self.clear_errors()
        
        # STDBY_RC
        self.spi_write([self.CMD_SET_STANDBY, 0x00])
        time.sleep_ms(10)
        
        # LDO regulator
        self.spi_write([self.CMD_SET_REGULATOR_MODE, 0x00])
        time.sleep_ms(10)
        
        # Calibrate
        self.spi_write([self.CMD_CALIBRATE, 0x7F])
        time.sleep_ms(500)
        
        print("✓ Basic initialization complete")
    
    def test_different_pa_configs(self):
        """Test different PA configurations to find working one"""
        print("\n=== Testing Different PA Configurations ===")
        
        # Test configurations from most conservative to original
        configs = [
            # [paDutyCycle, hpMax, deviceSel, paLut] - Description
            ([0x01, 0x00, 0x00, 0x01], "Minimal SX1262 (duty=1, hp=0)"),
            ([0x02, 0x02, 0x00, 0x01], "Low SX1262 (duty=2, hp=2)"),
            ([0x02, 0x03, 0x00, 0x01], "Medium SX1262 (duty=2, hp=3)"),
            ([0x04, 0x07, 0x00, 0x01], "Original SX1262 (duty=4, hp=7)"),
            ([0x04, 0x00, 0x01, 0x01], "SX1261 config test"),
        ]
        
        for config, description in configs:
            print(f"\nTesting: {description}")
            print(f"  Config: {config}")
            
            # Reset to clean state
            self.basic_init()
            
            # Set LoRa packet type
            self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
            time.sleep_ms(10)
            
            # Set frequency
            freq_raw = int((868000000 * 33554432) // 32000000)
            self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                           (freq_raw >> 24) & 0xFF, (freq_raw >> 16) & 0xFF, 
                           (freq_raw >> 8) & 0xFF, freq_raw & 0xFF])
            time.sleep_ms(10)
            
            # Test this PA config
            pa_cmd = [self.CMD_SET_PA_CONFIG] + config
            result = self.spi_write(pa_cmd)
            time.sleep_ms(10)
            
            if not result:
                print("  ✗ PA config command failed")
                continue
            
            # Set low TX power
            self.spi_write([self.CMD_SET_TX_PARAMS, 0, 0x02])  # 0dBm
            time.sleep_ms(10)
            
            # Check errors after PA config
            errors = self.get_errors()
            if errors:
                print(f"  ⚠ Errors after PA config: 0x{errors:04X}")
                self.clear_errors()
            
            # Try to enter FS mode first (safer than TX)
            print("    Testing FS mode...")
            fs_result = self.spi_write([self.CMD_SET_FS])
            time.sleep_ms(50)
            
            status = self.get_status()
            mode = (status >> 4) & 0x7
            cmd_status = (status >> 1) & 0x7
            errors = self.get_errors()
            
            print(f"    FS result: mode={mode}, cmd_status={cmd_status}, errors=0x{errors:04X}")
            
            if mode == 3 and cmd_status != 5:  # FS mode, no execution failure
                print("    ✓ FS mode successful!")
                
                # Now try TX mode
                print("    Testing TX mode...")
                self.spi_write([self.CMD_SET_STANDBY, 0x00])
                time.sleep_ms(10)
                
                tx_result = self.spi_write([self.CMD_SET_TX, 0x00, 0x00, 0x00])
                time.sleep_ms(50)
                
                status = self.get_status()
                mode = (status >> 4) & 0x7
                cmd_status = (status >> 1) & 0x7
                errors = self.get_errors()
                
                print(f"    TX result: mode={mode}, cmd_status={cmd_status}, errors=0x{errors:04X}")
                
                if mode == 5 and cmd_status != 5:  # TX mode, no execution failure
                    print("    ✓ TX mode successful with this config!")
                    print(f"  *** WORKING PA CONFIG FOUND: {config} ***")
                    return config
                else:
                    print("    ✗ TX mode failed")
            else:
                print("    ✗ FS mode failed")
        
        print("\n✗ No working PA configuration found")
        return None
    
    def test_frequency_synthesis_only(self):
        """Test if frequency synthesis works without PA"""
        print("\n=== Testing Frequency Synthesis Only ===")
        
        # Basic init
        self.basic_init()
        
        # Set packet type
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        time.sleep_ms(10)
        
        # Set frequency
        freq_raw = int((868000000 * 33554432) // 32000000)
        self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                       (freq_raw >> 24) & 0xFF, (freq_raw >> 16) & 0xFF, 
                       (freq_raw >> 8) & 0xFF, freq_raw & 0xFF])
        time.sleep_ms(10)
        
        # Try FS mode (frequency synthesis without TX)
        print("Entering FS mode...")
        result = self.spi_write([self.CMD_SET_FS])
        time.sleep_ms(100)
        
        status = self.get_status()
        mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        errors = self.get_errors()
        
        print(f"FS result: mode={mode}, cmd_status={cmd_status}, errors=0x{errors:04X}")
        
        if mode == 3:  # FS mode
            print("✓ Frequency synthesis works!")
            print("  This means:")
            print("    - SPI communication is good")
            print("    - Crystal oscillator is working")
            print("    - PLL can lock to frequency")
            print("    - Problem is likely in PA/TX circuitry")
            return True
        else:
            print("✗ Frequency synthesis failed")
            print("  This indicates deeper hardware issues")
            return False
    
    def test_rx_mode(self):
        """Test if RX mode works (doesn't use PA)"""
        print("\n=== Testing RX Mode ===")
        
        # Basic init
        self.basic_init()
        
        # Set packet type and frequency
        self.spi_write([self.CMD_SET_PACKET_TYPE, self.PACKET_TYPE_LORA])
        time.sleep_ms(10)
        
        freq_raw = int((868000000 * 33554432) // 32000000)
        self.spi_write([self.CMD_SET_RF_FREQUENCY, 
                       (freq_raw >> 24) & 0xFF, (freq_raw >> 16) & 0xFF, 
                       (freq_raw >> 8) & 0xFF, freq_raw & 0xFF])
        time.sleep_ms(10)
        
        # Set modulation
        self.spi_write([self.CMD_SET_MODULATION_PARAMS, 0x07, 0x04, 0x01, 0x00])
        time.sleep_ms(10)
        
        # Try RX mode
        print("Entering RX mode...")
        result = self.spi_write([self.CMD_SET_RX, 0x00, 0x10, 0x00])  # Short timeout
        time.sleep_ms(100)
        
        status = self.get_status()
        mode = (status >> 4) & 0x7
        cmd_status = (status >> 1) & 0x7
        errors = self.get_errors()
        
        print(f"RX result: mode={mode}, cmd_status={cmd_status}, errors=0x{errors:04X}")
        
        if mode == 4:  # RX mode
            print("✓ RX mode works!")
            print("  This confirms:")
            print("    - Receiver circuitry is functional")
            print("    - Problem is specifically with PA/transmitter")
            return True
        else:
            print("✗ RX mode failed")
            return False
    
    def hardware_diagnostic_summary(self):
        """Run complete hardware diagnostic"""
        print("\n" + "="*60)
        print("HARDWARE DIAGNOSTIC SUMMARY")
        print("="*60)
        
        print("\n1. TESTING FREQUENCY SYNTHESIS...")
        fs_works = self.test_frequency_synthesis_only()
        
        print("\n2. TESTING RECEIVER...")
        rx_works = self.test_rx_mode()
        
        print("\n3. TESTING PA CONFIGURATIONS...")
        working_config = self.test_different_pa_configs()
        
        print("\n" + "="*60)
        print("DIAGNOSTIC RESULTS:")
        print("="*60)
        
        print(f"✓ Frequency Synthesis: {'WORKING' if fs_works else 'FAILED'}")
        print(f"✓ Receiver Mode: {'WORKING' if rx_works else 'FAILED'}")
        print(f"✓ Transmitter: {'WORKING' if working_config else 'FAILED'}")
        
        if working_config:
            print(f"✓ Working PA Config: {working_config}")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        
        if not fs_works:
            print("❌ CRITICAL: Basic frequency synthesis failed")
            print("   → Check power supply, crystal, and SPI connections")
            print("   → Module may be defective")
        
        elif not rx_works:
            print("❌ ISSUE: Receiver not working")
            print("   → Check RF circuitry and antenna connections")
        
        elif not working_config:
            print("❌ ISSUE: No working PA configuration found")
            print("   → Check antenna connection (CRITICAL!)")
            print("   → Check power supply current capability (need >100mA)")
            print("   → Try connecting a simple wire antenna (8.6cm for 868MHz)")
            print("   → Module PA may be defective")
        
        else:
            print("✅ HARDWARE APPEARS FUNCTIONAL!")
            print(f"   → Use PA config: {working_config}")
            print("   → Try transmission with working configuration")
        
        print("\n" + "="*60)
        return working_config


def run_hardware_diagnostics():
    """Run comprehensive hardware diagnostics"""
    print("=== SX1262 HARDWARE DIAGNOSTICS ===")
    print("This will test different aspects of the hardware")
    print("to identify what's working and what's not.\n")
    
    try:
        # Initialize diagnostic system
        sx1262 = SX1262()
        
        # Run full diagnostic
        working_config = sx1262.hardware_diagnostic_summary()
        
        if working_config:
            print(f"\n🎉 GOOD NEWS: Found working PA configuration!")
            print(f"Use this in your main code: {working_config}")
            print("\nTry modifying your PA config to:")
            print(f"self.spi_write([self.CMD_SET_PA_CONFIG, {working_config[0]}, {working_config[1]}, {working_config[2]}, {working_config[3]}])")
        else:
            print(f"\n😞 No working PA configuration found.")
            print("\nTRY THESE HARDWARE FIXES:")
            print("1. 🔌 Connect an antenna (most likely cause!)")
            print("   - Simple wire: 8.6cm long for 868MHz")
            print("   - Connect to antenna pad/SMA connector")
            print("2. 🔋 Check power supply:")
            print("   - Measure actual voltage (should be 3.3V)")
            print("   - Ensure >150mA current capability")
            print("3. 🔍 Try the other module to compare")
            print("4. 📏 Check all wire connections")
        
    except Exception as e:
        print(f"Diagnostic error: {e}")
        import traceback
        traceback.print_exc()

# Run diagnostics
if __name__ == "__main__":
    run_hardware_diagnostics()