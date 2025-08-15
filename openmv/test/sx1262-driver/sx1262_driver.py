import machine
import time
from machine import Pin, SPI

class SX1262:
    # Essential SX1262 commands
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
    
    # Constants
    LORA_MODEM = 0x01
    STANDBY_RC = 0x00
    IRQ_TX_DONE = 0x0001
    IRQ_RX_DONE = 0x0002
    IRQ_TIMEOUT = 0x0200
    
    def __init__(self, spi, cs_pin, reset_pin, busy_pin, dio1_pin):
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT)
        self.reset = Pin(reset_pin, Pin.OUT)
        self.busy = Pin(busy_pin, Pin.IN)
        self.dio1 = Pin(dio1_pin, Pin.IN)
        self.cs.value(1)  # CS high initially
        
    def wait_busy(self):
        """Wait for BUSY pin to go low"""
        timeout = 1000
        while self.busy.value() and timeout > 0:
            time.sleep_ms(1)
            timeout -= 1
        return timeout > 0
    
    def write_command(self, cmd, data=None):
        """Write command to SX1262"""
        if not self.wait_busy():
            return False
            
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        if data:
            self.spi.write(data)
        self.cs.value(1)
        return True
    
    def read_command(self, cmd, length):
        """Read command from SX1262"""
        if not self.wait_busy():
            return None
            
        self.cs.value(0)
        self.spi.write(bytes([cmd]))
        result = self.spi.read(length)
        self.cs.value(1)
        return result
    
    def reset_chip(self):
        """Reset the SX1262 chip"""
        self.reset.value(0)
        time.sleep_ms(10)
        self.reset.value(1)
        time.sleep_ms(100)
        return self.wait_busy()
    
    def init(self, frequency=868000000, tx_power=14):
        """Initialize SX1262 for LoRa communication"""
        if not self.reset_chip():
            return False
            
        # Set standby mode
        self.write_command(self.CMD_SET_STANDBY, bytes([self.STANDBY_RC]))
        
        # Set packet type to LoRa
        self.write_command(self.CMD_SET_PACKET_TYPE, bytes([self.LORA_MODEM]))
        
        # Set frequency (868 MHz)
        freq_val = int(frequency * 33554432 / 32000000)
        freq_bytes = bytes([
            (freq_val >> 24) & 0xFF,
            (freq_val >> 16) & 0xFF,
            (freq_val >> 8) & 0xFF,
            freq_val & 0xFF
        ])
        self.write_command(self.CMD_SET_RF_FREQUENCY, freq_bytes)
        
        # Set TX power
        self.write_command(self.CMD_SET_TX_PARAMS, bytes([tx_power, 0x04]))
        
        # Set modulation parameters (SF7, BW125, CR4/5)
        modulation = bytes([7, 4, 1, 0, 0, 0, 0, 0])  # SF7, BW125kHz, CR4/5
        self.write_command(self.CMD_SET_MODULATION_PARAMS, modulation)
        
        # Set packet parameters
        packet_params = bytes([0, 12, 0, 255, 1, 0, 0, 0, 0])  # Preamble 12, explicit header, max payload
        self.write_command(self.CMD_SET_PACKET_PARAMS, packet_params)
        
        # Set buffer base addresses
        self.write_command(self.CMD_SET_BUFFER_BASE_ADDR, bytes([0, 0]))
        
        # Set DIO IRQ parameters
        irq_mask = bytes([0x03, 0xFF, 0x03, 0xFF, 0x00, 0x00, 0x00, 0x00])
        self.write_command(self.CMD_SET_DIO_IRQ_PARAMS, irq_mask)
        
        return True
    
    def send_message(self, message, dest_addr=0xFF):
        """Send a message with address"""
        # Prepare packet: [dest_addr, src_addr, message]
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        packet = bytes([dest_addr, MY_ADDRESS]) + message
        
        # Write to buffer
        buffer_data = bytes([0]) + packet  # Offset 0
        self.write_command(self.CMD_WRITE_BUFFER, buffer_data)
        
        # Update packet length
        packet_params = bytes([0, 12, 0, len(packet), 1, 0, 0, 0, 0])
        self.write_command(self.CMD_SET_PACKET_PARAMS, packet_params)
        
        # Clear IRQ status
        self.write_command(self.CMD_CLEAR_IRQ_STATUS, bytes([0x03, 0xFF]))
        
        # Start transmission
        self.write_command(self.CMD_SET_TX, bytes([0, 0, 0]))  # No timeout
        
        # Wait for TX done
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < 5000:
            irq_status = self.read_command(self.CMD_GET_IRQ_STATUS, 3)
            if irq_status and len(irq_status) >= 3:
                irq_val = (irq_status[1] << 8) | irq_status[2]
                if irq_val & self.IRQ_TX_DONE:
                    print(f"Message sent to {dest_addr:02X}: {message}")
                    return True
            time.sleep_ms(10)
        
        print("TX timeout")
        return False
    
    def receive_message(self, timeout_ms=5000):
        """Receive a message"""
        # Clear IRQ status
        self.write_command(self.CMD_CLEAR_IRQ_STATUS, bytes([0x03, 0xFF]))
        
        # Start reception
        self.write_command(self.CMD_SET_RX, bytes([0xFF, 0xFF, 0xFF]))  # Continuous RX
        
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            irq_status = self.read_command(self.CMD_GET_IRQ_STATUS, 3)
            if irq_status and len(irq_status) >= 3:
                irq_val = (irq_status[1] << 8) | irq_status[2]
                
                if irq_val & self.IRQ_RX_DONE:
                    # Get buffer status
                    buffer_status = self.read_command(self.CMD_GET_RX_BUFFER_STATUS, 3)
                    if buffer_status and len(buffer_status) >= 3:
                        payload_length = buffer_status[1]
                        buffer_offset = buffer_status[2]
                        
                        # Read buffer
                        read_cmd = bytes([self.CMD_READ_BUFFER, buffer_offset])
                        self.cs.value(0)
                        self.spi.write(read_cmd)
                        data = self.spi.read(payload_length)
                        self.cs.value(1)
                        
                        if len(data) >= 2:
                            dest_addr = data[0]
                            src_addr = data[1]
                            message = data[2:].decode('utf-8', errors='ignore')
                            
                            # Check if message is for us or broadcast
                            if dest_addr == MY_ADDRESS or dest_addr == 0xFF:
                                print(f"Received from {src_addr:02X}: {message}")
                                return (src_addr, message)
                        
                elif irq_val & self.IRQ_TIMEOUT:
                    break
            
            time.sleep_ms(10)
        
        return None

# Configuration
MY_ADDRESS = 0x01  # Your radio address
PEER_ADDRESS = 0x02  # Address of radio you want to communicate with

# Initialize SPI and radio
spi = SPI(1, baudrate=1000000, polarity=0, phase=0)

radio = SX1262(spi, 'P3', 'P6', 'P7', 'P13')  # cs, reset, busy, dio1


# cs    = Pin('P3', Pin.OUT)
# busy  = Pin('P7', Pin.IN)
# reset = Pin('P6', Pin.OUT)  # Changed P6 reset
# dio1  = Pin('P13', Pin.IN)

def main():
    print("Initializing SX1262...")
    if not radio.init():
        print("Failed to initialize radio!")
        return
    
    print(f"Radio initialized. My address: {MY_ADDRESS:02X}")
    print("Commands:")
    print("  send <message>  - Send message to peer")
    print("  listen         - Listen for messages")
    print("  broadcast <msg> - Broadcast message")
    
    while True:
        try:
            cmd = input("> ").strip()
            
            if cmd.startswith("send "):
                message = cmd[5:]
                radio.send_message(message, PEER_ADDRESS)
            
            elif cmd == "listen":
                print("Listening for messages (5s)...")
                result = radio.receive_message(5000)
                if result:
                    src_addr, message = result
                    print(f"Got message from {src_addr:02X}: {message}")
                else:
                    print("No messages received")
            
            elif cmd.startswith("broadcast "):
                message = cmd[10:]
                radio.send_message(message, 0xFF)  # 0xFF = broadcast
            
            elif cmd == "help":
                print("Commands: send <msg>, listen, broadcast <msg>")
            
            else:
                print("Unknown command. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()