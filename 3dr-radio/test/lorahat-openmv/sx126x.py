import time
import struct
from machine import UART, Pin

class SX126x:
    # LoRa air speed dictionary
    lora_air_speed_dic = {
        2400: 0x00,    # 2.4kbps
        4800: 0x01,    # 4.8kbps
        9600: 0x02,    # 9.6kbps
        19200: 0x03,   # 19.2kbps
        38400: 0x04,   # 38.4kbps
        62500: 0x05    # 62.5kbps
    }

    # LoRa buffer size dictionary
    lora_buffer_size_dic = {
        32: 0x00,
        64: 0x01,
        128: 0x02,
        240: 0x03
    }

    # LoRa power dictionary
    lora_power_dic = {
        10: 0x00,
        13: 0x01,
        17: 0x02,
        22: 0x03
    }

    # UART baudrate constant
    SX126X_UART_BAUDRATE_9600 = 0x00

    def __init__(self, uart_id=3, freq=868, addr=0, power=22, rssi=True, air_speed=2400,
                 net_id=0, buffer_size=240, crypt=0, relay=False, lbt=False, wor=False,
                 m0_pin='P6', m1_pin='P7'):
        """
        Initialize SX126x LoRa module

        Args:
            uart_id: UART ID for OpenMV (default 3)
            freq: Frequency in MHz (433, 868, 915)
            addr: Module address (0-65535)
            power: Transmit power in dBm (10, 13, 17, 22)
            rssi: Enable RSSI output
            air_speed: Air data rate in bps
            net_id: Network ID (0-255)
            buffer_size: Buffer size (32, 64, 128, 240)
            crypt: Encryption key (0-65535)
            relay: Enable relay mode
            lbt: Enable Listen Before Talk
            wor: Enable Wake on Radio
            m0_pin: M0 control pin name (e.g., 'P6')
            m1_pin: M1 control pin name (e.g., 'P7')
        """
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.power = power

        # Initialize M0 and M1 control pins
        self.M0 = Pin(m0_pin, Pin.OUT)
        self.M1 = Pin(m1_pin, Pin.OUT)

        # Initialize UART
        self.uart = UART(uart_id,1baudrate=9600, bits=8, parity=None, stop=1)

        # Configuration register array (12 bytes)
        self.cfg_reg = [0xC0, 0x00, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        # Configure the module
        self.set_config(freq, addr, power, rssi, air_speed, net_id, buffer_size, crypt, relay, lbt, wor)

    def set_config(self, freq, addr, power, rssi, air_speed=2400,
                   net_id=0, buffer_size=240, crypt=0,
                   relay=False, lbt=False, wor=False):
        """Configure the LoRa module parameters"""

        self.send_to = addr
        self.addr = addr

        # Enter configuration mode (M0=LOW, M1=HIGH)
        self.M0.value(0)
        self.M1.value(1)
        time.sleep(0.1)

        # Calculate address bytes
        low_addr = addr & 0xff
        high_addr = (addr >> 8) & 0xff
        net_id_temp = net_id & 0xff

        # Calculate frequency offset
        if freq > 850:
            freq_temp = freq - 850
            self.start_freq = 850
            self.offset_freq = freq_temp
        elif freq > 410:
            freq_temp = freq - 410
            self.start_freq = 410
            self.offset_freq = freq_temp
        else:
            freq_temp = 0
            self.start_freq = 433
            self.offset_freq = 0

        # Get air speed, buffer size, and power settings
        air_speed_temp = self.lora_air_speed_dic.get(air_speed, 0x00)
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, 0x03)
        power_temp = self.lora_power_dic.get(power, 0x03)

        # Set RSSI enable flag
        rssi_temp = 0x80 if rssi else 0x00

        # Calculate encryption bytes
        l_crypt = crypt & 0xff
        h_crypt = (crypt >> 8) & 0xff

        # Configure registers based on relay mode
        if not relay:
            self.cfg_reg[3] = high_addr
            self.cfg_reg[4] = low_addr
            self.cfg_reg[5] = net_id_temp
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20  # Enable noise RSSI
            self.cfg_reg[8] = freq_temp
            self.cfg_reg[9] = 0x43 + rssi_temp  # Enable packet RSSI output
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt
        else:
            # Relay mode configuration
            self.cfg_reg[3] = 0x01
            self.cfg_reg[4] = 0x02
            self.cfg_reg[5] = 0x03
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            self.cfg_reg[9] = 0x03 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt

        # Clear UART buffer
        while self.uart.any():
            self.uart.read()

        # Send configuration (try twice)
        for attempt in range(2):
            self.uart.write(bytes(self.cfg_reg))
            time.sleep(0.2)

            if self.uart.any():
                time.sleep(0.1)
                response = self.uart.read()
                if response and response[0] == 0xC1:
                    print("Configuration successful")
                    break
                else:
                    print(f"Configuration failed, response: {response}")
            else:
                print(f"Configuration attempt {attempt + 1} failed, no response")
                if attempt == 1:
                    print("Configuration failed after 2 attempts")

        # Enter transmission mode (M0=LOW, M1=LOW)
        self.M0.value(0)
        self.M1.value(0)
        time.sleep(0.1)

    def send(self, data, target_addr=None):
        """
        Send data through LoRa
        Data format: [target_high_addr][target_low_addr][channel][payload]
        """
        # Ensure we're in transmission mode
        self.M0.value(0)
        self.M1.value(0)
        time.sleep(0.1)

        if target_addr is None:
            target_addr = 0xFFFF  # Broadcast address

        if isinstance(data, str):
            payload = data.encode('utf-8')
        else:
            payload = data

        # Create packet: [high_addr][low_addr][channel][payload]
        target_high = (target_addr >> 8) & 0xFF
        target_low = target_addr & 0xFF
        channel = self.offset_freq  # Use configured frequency offset

        packet = bytes([target_high, target_low, channel]) + payload

        self.uart.write(packet)
        time.sleep(0.1)
        print(f"Sent to addr {target_addr}: {data}")

    def receive(self):
        """Receive data from LoRa"""
        if self.uart.any():
            time.sleep(0.2)  # Wait for complete message
            data = self.uart.read()

            if data and len(data) >= 3:
                try:
                    # Parse the received message format
                    # Format: [sender_high][sender_low][channel][payload][rssi_byte if enabled]
                    sender_addr = (data[0] << 8) + data[1]
                    channel = data[2]
                    freq = channel + self.start_freq

                    if self.rssi and len(data) > 3:
                        # RSSI byte is at the end
                        message = data[3:-1]
                        rssi_value = 256 - data[-1]
                    else:
                        message = data[3:]
                        rssi_value = None

                    # Try to decode message as string
                    try:
                        message_str = message.decode('utf-8')
                    except:
                        message_str = str(message)

                    print("=" * 50)
                    print(f"📡 Received from node {sender_addr} at {freq}.125MHz")
                    print(f"📝 Message: {message_str}")

                    # Print RSSI if enabled
                    if self.rssi and rssi_value is not None:
                        print(f"📶 RSSI: -{rssi_value}dBm")
                    print("=" * 50)

                    return {
                        'sender_addr': sender_addr,
                        'frequency': freq,
                        'message': message_str,
                        'raw_message': message,
                        'rssi': rssi_value
                    }
                except Exception as e:
                    print(f"Error parsing received data: {e}")
                    print(f"Raw data: {[hex(b) for b in data]}")

        return None

    def set_mode(self, mode):
        """
        Set LoRa module operating mode
        Mode 0: Transmission mode (M0=0, M1=0)
        Mode 1: WOR transmit mode (M0=0, M1=1)
        Mode 2: Configuration mode (M0=1, M1=0)
        Mode 3: Deep sleep mode (M0=1, M1=1)
        """
        if mode == 0:    # Transmission mode
            self.M0.value(0)
            self.M1.value(0)
        elif mode == 1:  # WOR transmit mode
            self.M0.value(0)
            self.M1.value(1)
        elif mode == 2:  # Configuration mode
            self.M0.value(1)
            self.M1.value(0)
        elif mode == 3:  # Deep sleep mode
            self.M0.value(1)
            self.M1.value(1)
        else:
            print("Invalid mode")
            return False

        time.sleep(0.1)
        print(f"Set to mode {mode}")
        return True

    def get_channel_rssi(self):
        """Get current channel RSSI (noise level)"""
        # This would require sending a specific command to the module
        # Implementation depends on the specific SX126x command set
        pass


# Example usage
def main():
    """Main test function"""
    print("Initializing SX126x LoRa module...")

    # Initialize LoRa module
    # Adjust parameters according to your needs
    lora = SX126x(
        uart_id=1,        # OpenMV UART3
        freq=868,         # 868MHz (change to 433 or 915 as needed)
        addr=100,         # This node's address
        power=22,         # Maximum power
        rssi=True,        # Enable RSSI
        air_speed=2400,
        m0_pin='P6',         # M0 connected to Pin P6
        m1_pin='P7'          # M1 connected to Pin P7
    )

    print("LoRa module initialized")
    print("Commands:")
    print("- Type 's' to send a test message")
    print("- Type 'r' to check for received messages")
    print("- Type 'q' to quit")

    test_message = "Hello from OpenMV LoRa!"
    message_counter = 0

    while True:
        # Check for received messages
        received = lora.receive()
        if received:
            print("=" * 40)

        # Simple command interface (you can modify this for your needs)
        try:
            # Send a test message every 5 seconds
            time.sleep(5)
            message_counter += 1
            test_msg = f"{test_message} #{message_counter}"
            lora.send(test_msg)
            print(f"Sent message #{message_counter}")

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)


# For interactive testing
def create_lora_instance(my_addr=100):
    """Create and return a LoRa instance for interactive use"""
    return SX126x(
        uart_id=3,
        freq=868,         # Change as needed
        addr=my_addr,     # Unique address for this device
        power=22,
        rssi=True,
        air_speed=2400,
        m0_pin='P6',
        m1_pin='P7'
    )


def broadcast_test(my_addr=100):
    """Test function for broadcast communication"""
    lora = create_lora_instance(my_addr)
    counter = 0

    print(f"Starting broadcast test with address {my_addr}")
    print("Sending broadcast messages every 5 seconds...")

    while True:
        try:
            # Check for messages
            lora.receive()

            # Send broadcast message
            time.sleep(5)
            counter += 1
            msg = f"Broadcast from {my_addr}: #{counter}"
            lora.send(msg, target_addr=0xFFFF)  # Broadcast to all
            print(f"Broadcast #{counter}")

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
