import machine
import time
from machine import Pin, SPI

class SX1262:
    # Essential SX1262 commands
    CMD_SET_SLEEP = 0x84
    CMD_SET_STANDBY = 0x80
    CMD_SET_PACKET_TYPE = 0x8A
    CMD_SET_RF_FREQUENCY = 0x86
    CMD_SET_TX_PARAMS = 0x8E
    CMD_SET_MODULATION_PARAMS = 0x8B
    CMD_SET_PACKET_PARAMS = 0x8C
    CMD_SET_BUFFER_BASE_ADDR = 0x8F
    CMD_WRITE_BUFFER = 0x0E
    CMD_READ_BUFFER = 0x1E
    CMD_SET_TX = 0x83
    CMD_SET_RX = 0x82
    CMD_GET_IRQ_STATUS = 0x12
    CMD_CLEAR_IRQ_STATUS = 0x02
    CMD_SET_DIO_IRQ_PARAMS = 0x08
    CMD_GET_RX_BUFFER_STATUS = 0x13
    CMD_GET_STATUS = 0xC0
    CMD_SET_DIO2_RF_SWITCH = 0x9D
    CMD_SET_REGULATOR_MODE = 0x96
    CMD_CALIBRATE = 0x89
    CMD_SET_PA_CONFIG = 0x95
    
    # Constants
    LORA_MODEM = 0x01
    STANDBY_RC = 0x00
    STANDBY_XOSC = 0x01
    IRQ_TX_DONE = 0x0001
    IRQ_RX_DONE = 0x0002
    IRQ_TIMEOUT = 0x0200
    IRQ_ALL = 0x03FF
    REGULATOR_DC_DC = 0x01
    
    def __init__(self, spi, cs_pin, reset_pin, busy_pin, dio1_pin, txen_pin=None, rxen_pin=None):
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        
        # Optional TXEN/RXEN pins for external RF switch
        self.txen = Pin(txen_pin, Pin.OUT) if txen_pin else None
        self.rxen = Pin(rxen_pin, Pin.OUT) if rxen_pin else None
        
        self.cs.value(1)  # CS high initially
        self.reset.value(1)  # Reset high initially
        
        if self.txen:
            self.txen.value(0)
        if self.rxen:
            self.rxen.value(0)
        
    def wait_busy(self, timeout_ms=1000):
        """Wait for BUSY pin to go low"""
        start = time.ticks_ms()
        while self.busy.value():
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                print("BUSY timeout!")
                return False
            time.sleep_ms(1)
        return True
    
    def write_command(self, cmd, data=None):
        """Write command to SX1262"""
        if not self.wait_busy():
            return False
            
        self.cs.value(0)
        time.sleep_us(10)  # Small delay
        self.spi.write(bytes([cmd]))
        if data:
            self.spi.write(data)
        time.sleep_us(10)
        self.cs.value(1)
        return True
    
    def read_command(self, cmd, length, dummy_bytes=1):
        """Read command from SX1262"""
        if not self.wait_busy():
            return None
            
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytes([cmd]))
        # Read with dummy byte for status
        result = self.spi.read(length + dummy_bytes)
        time.sleep_us(10)
        self.cs.value(1)
        return result[dummy_bytes:] if dummy_bytes > 0 else result
    
    def get_status(self):
        """Get chip status"""
        if not self.wait_busy():
            return None
        self.cs.value(0)
        result = self.spi.read(1)
        self.cs.value(1)
        return result[0] if result else None
    
    def reset_chip(self):
        """Reset the SX1262 chip"""
        print("Resetting SX1262...")
        self.reset.value(0)
        time.sleep_ms(10)
        self.reset.value(1)
        time.sleep_ms(50)
        
        # Wake up from sleep
        self.cs.value(0)
        time.sleep_ms(1)
        self.cs.value(1)
        time.sleep_ms(10)
        
        return self.wait_busy(2000)
    
    def init(self, frequency=868000000, tx_power=14):
        """Initialize SX1262 for LoRa communication"""
        print("Resetting chip...")
        if not self.reset_chip():
            print("Reset failed!")
            return False
        
        print("Setting standby mode...")
        # Set standby mode
        if not self.write_command(self.CMD_SET_STANDBY, bytes([self.STANDBY_RC])):
            print("Standby command failed!")
            return False
        time.sleep_ms(10)
        
        # Check status
        status = self.get_status()
        print(f"Status after standby: 0x{status:02X}" if status else "Status read failed")
        
        # Set regulator to DC-DC (more efficient)
        print("Setting regulator...")
        self.write_command(self.CMD_SET_REGULATOR_MODE, bytes([self.REGULATOR_DC_DC]))
        
        # Calibrate all
        print("Calibrating...")
        self.write_command(self.CMD_CALIBRATE, bytes([0xFF]))
        time.sleep_ms(100)
        
        # Set DIO2 as RF switch control (important!)
        print("Setting DIO2 as RF switch...")
        self.write_command(self.CMD_SET_DIO2_RF_SWITCH, bytes([0x01]))
        
        print("Setting packet type...")
        # Set packet type to LoRa
        if not self.write_command(self.CMD_SET_PACKET_TYPE, bytes([self.LORA_MODEM])):
            print("Packet type command failed!")
            return False
        
        print("Setting PA config...")
        # Set PA configuration for SX1262 (22dBm max)
        pa_config = bytes([0x04, 0x07, 0x00, 0x01])  # paDutyCycle, hpMax, deviceSel, paLut
        self.write_command(self.CMD_SET_PA_CONFIG, pa_config)
        
        print(f"Setting frequency to {frequency} Hz...")
        # Set frequency
        freq_val = int(frequency * 33554432 / 32000000)
        freq_bytes = bytes([
            (freq_val >> 24) & 0xFF,
            (freq_val >> 16) & 0xFF,
            (freq_val >> 8) & 0xFF,
            freq_val & 0xFF
        ])
        self.write_command(self.CMD_SET_RF_FREQUENCY, freq_bytes)
        
        print(f"Setting TX power to {tx_power} dBm...")
        # Set TX power (limited to 14dBm for testing)
        power = min(tx_power, 14)  # Conservative power setting
        self.write_command(self.CMD_SET_TX_PARAMS, bytes([power, 0x04]))  # ramp time 800us
        
        print("Setting modulation parameters...")
        # Set modulation parameters (SF7, BW125, CR4/5, LDRO off)
        modulation = bytes([7, 4, 1, 0, 0, 0, 0, 0])
        self.write_command(self.CMD_SET_MODULATION_PARAMS, modulation)
        
        print("Setting packet parameters...")
        # Set packet parameters (explicit header, 12 symbol preamble, CRC on)
        packet_params = bytes([0, 12, 0, 32, 1, 0, 0, 0, 0])  # preamble=12, explicit, payload=32, CRC on
        self.write_command(self.CMD_SET_PACKET_PARAMS, packet_params)
        
        print("Setting buffer addresses...")
        # Set buffer base addresses
        self.write_command(self.CMD_SET_BUFFER_BASE_ADDR, bytes([0, 128]))  # TX at 0, RX at 128
        
        print("Setting IRQ parameters...")
        # Set DIO IRQ parameters - all IRQs on DIO1
        irq_mask = bytes([0x03, 0xFF, 0x03, 0xFF, 0x00, 0x00, 0x00, 0x00])
        self.write_command(self.CMD_SET_DIO_IRQ_PARAMS, irq_mask)
        
        print("Initialization complete!")
        return True
    
    def send_message(self, message, dest_addr=0xFF):
        """Send a message with address"""
        # Set RF switch for TX
        if self.txen and self.rxen:
            self.txen.value(1)
            self.rxen.value(0)
        
        # Prepare packet: [dest_addr, src_addr, message]
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        packet = bytes([dest_addr, MY_ADDRESS]) + message
        print(f"Sending packet: {packet}")
        
        # Write to buffer at offset 0
        buffer_data = bytes([0]) + packet  # Offset 0 + data
        if not self.write_command(self.CMD_WRITE_BUFFER, buffer_data):
            print("Write buffer failed!")
            return False
        
        # Update packet length in packet parameters
        packet_params = bytes([0, 12, 0, len(packet), 1, 0, 0, 0, 0])
        self.write_command(self.CMD_SET_PACKET_PARAMS, packet_params)
        
        # Clear IRQ status
        self.write_command(self.CMD_CLEAR_IRQ_STATUS, bytes([0x03, 0xFF]))
        
        print("Starting transmission...")
        # Start transmission (no timeout)
        if not self.write_command(self.CMD_SET_TX, bytes([0, 0, 0])):
            print("TX command failed!")
            return False
        
        # Wait for TX done or timeout
        start_time = time.ticks_ms()
        tx_done = False
        
        while time.ticks_diff(time.ticks_ms(), start_time) < 10000:  # 10 second timeout
            # Check DIO1 pin first (faster)
            if self.dio1.value():
                print("DIO1 interrupt detected!")
                
            # Read IRQ status
            irq_status = self.read_command(self.CMD_GET_IRQ_STATUS, 2, 1)
            if irq_status and len(irq_status) >= 2:
                irq_val = (irq_status[0] << 8) | irq_status[1]
                print(f"IRQ status: 0x{irq_val:04X}")
                
                if irq_val & self.IRQ_TX_DONE:
                    print(f"✓ Message sent to {dest_addr:02X}: {message}")
                    tx_done = True
                    break
                elif irq_val & self.IRQ_TIMEOUT:
                    print("✗ TX timeout (IRQ)")
                    break
            
            time.sleep_ms(100)
        
        # Reset RF switch
        if self.txen and self.rxen:
            self.txen.value(0)
            self.rxen.value(0)
        
        if not tx_done:
            print("✗ TX timeout (no IRQ)")
            
        return tx_done
    
    def receive_message(self, timeout_ms=5000):
        """Receive a message"""
        # Set RF switch for RX
        if self.txen and self.rxen:
            self.txen.value(0)
            self.rxen.value(1)
        
        # Clear IRQ status
        self.write_command(self.CMD_CLEAR_IRQ_STATUS, bytes([0x03, 0xFF]))
        
        print("Starting reception...")
        # Start reception (continuous)
        if not self.write_command(self.CMD_SET_RX, bytes([0xFF, 0xFF, 0xFF])):
            print("RX command failed!")
            return None
        
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            # Check DIO1 pin
            if self.dio1.value():
                print("DIO1 interrupt during RX!")
                
            irq_status = self.read_command(self.CMD_GET_IRQ_STATUS, 2, 1)
            if irq_status and len(irq_status) >= 2:
                irq_val = (irq_status[0] << 8) | irq_status[1]
                
                if irq_val & self.IRQ_RX_DONE:
                    print(f"RX done IRQ: 0x{irq_val:04X}")
                    
                    # Get buffer status
                    buffer_status = self.read_command(self.CMD_GET_RX_BUFFER_STATUS, 2, 1)
                    if buffer_status and len(buffer_status) >= 2:
                        payload_length = buffer_status[0]
                        buffer_offset = buffer_status[1]
                        
                        print(f"Payload length: {payload_length}, offset: {buffer_offset}")
                        
                        # Read buffer
                        buffer_data = self.read_command(self.CMD_READ_BUFFER, payload_length, 1, buffer_offset)
                        
                        if buffer_data and len(buffer_data) >= 2:
                            dest_addr = buffer_data[0]
                            src_addr = buffer_data[1]
                            message = buffer_data[2:].decode('utf-8', errors='ignore')
                            
                            # Check if message is for us or broadcast
                            if dest_addr == MY_ADDRESS or dest_addr == 0xFF:
                                print(f"✓ Received from {src_addr:02X}: {message}")
                                return (src_addr, message)
                        
                elif irq_val & self.IRQ_TIMEOUT:
                    print("RX timeout")
                    break
            
            time.sleep_ms(50)
        
        # Reset RF switch
        if self.txen and self.rxen:
            self.txen.value(0)
            self.rxen.value(0)
        
        return None
    
    def read_command_with_address(self, cmd, length, dummy_bytes, address):
        """Read command with address (for buffer read)"""
        if not self.wait_busy():
            return None
            
        self.cs.value(0)
        time.sleep_us(10)
        self.spi.write(bytes([cmd, address]))
        result = self.spi.read(length + dummy_bytes)
        time.sleep_us(10)
        self.cs.value(1)
        return result[dummy_bytes:] if dummy_bytes > 0 else result

# Configuration - Change these for each radio
MY_ADDRESS = 0x01      # Your radio address (change to 0x02 for second radio)
PEER_ADDRESS = 0x02    # Peer radio address (change to 0x01 for second radio)

# Initialize SPI and radio
print("Initializing SPI...")
spi = SPI(1, baudrate=1000000, polarity=0, phase=0)

# For Core1262-868M, you may need TXEN/RXEN pins if external RF switch
# If using DIO2 as RF switch, set txen_pin and rxen_pin to None
radio = SX1262(spi, 'P3', 'P6', 'P7', 'P13')  # cs, reset, busy, dio1

def test_radio():
    """Test radio functionality"""
    print("\n=== Radio Test ===")
    
    # Test status
    status = radio.get_status()
    print(f"Radio status: 0x{status:02X}" if status else "Status read failed")
    
    # Test simple transmission
    print("Testing transmission...")
    success = radio.send_message("TEST", 0xFF)
    print(f"Test TX: {'✓ SUCCESS' if success else '✗ FAILED'}")
    
    return success

def main():
    print("=== OpenMV SX1262 LoRa Communication ===")
    print("Initializing SX1262...")
    
    if not radio.init():
        print("✗ Failed to initialize radio!")
        return
    
    print(f"✓ Radio initialized. My address: 0x{MY_ADDRESS:02X}")
    
    # Test the radio
    if not test_radio():
        print("⚠ Radio test failed, but continuing...")
    
    print("\nCommands:")
    print("  send <message>     - Send message to peer")
    print("  listen            - Listen for messages")
    print("  broadcast <msg>   - Broadcast message")
    print("  test              - Test transmission")
    print("  help              - Show commands")
    
    while True:
        try:
            # cmd = input("> ").strip()
            
            # if cmd.startswith("send "):
            #     message = cmd[5:]
            #     radio.send_message(message, PEER_ADDRESS)
            
            # elif cmd == "listen":
            #     print("Listening for messages (10s)...")
            #     result = radio.receive_message(10000)
            #     if result:
            #         src_addr, message = result
            #         print(f"✓ Got message from 0x{src_addr:02X}: {message}")
            #     else:
            #         print("✗ No messages received")
            
            # elif cmd.startswith("broadcast "):
            #     message = cmd[10:]
            #     radio.send_message(message, 0xFF)  # 0xFF = broadcast
            
            # elif cmd == "test":
            #     test_radio()
            
            # elif cmd == "help":
            #     print("Commands: send <msg>, listen, broadcast <msg>, test")
            
            # elif cmd == "":
            #     continue
                
            # else:
            #     print("Unknown command. Type 'help' for commands.")

            message = "Hello from OpenMV!"  # Example message``
            radio.send_message(message, PEER_ADDRESS)
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()