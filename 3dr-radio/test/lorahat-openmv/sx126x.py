import machine
import time
from machine import Pin, UART

class sx126x:
    """
    SX126x LoRa module driver for OpenMV RT1062
    Flexible pin configuration for different OpenMV boards
    """

    # Configuration register template
    cfg_reg = [0xC2,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x12,0x43,0x00,0x00]
    get_reg = bytearray(12)

    # UART Baudrate constants
    SX126X_UART_BAUDRATE_1200 = 0x00
    SX126X_UART_BAUDRATE_2400 = 0x20
    SX126X_UART_BAUDRATE_4800 = 0x40
    SX126X_UART_BAUDRATE_9600 = 0x60
    SX126X_UART_BAUDRATE_19200 = 0x80
    SX126X_UART_BAUDRATE_38400 = 0xA0
    SX126X_UART_BAUDRATE_57600 = 0xC0
    SX126X_UART_BAUDRATE_115200 = 0xE0

    # Package size constants
    SX126X_PACKAGE_SIZE_240_BYTE = 0x00
    SX126X_PACKAGE_SIZE_128_BYTE = 0x40
    SX126X_PACKAGE_SIZE_64_BYTE = 0x80
    SX126X_PACKAGE_SIZE_32_BYTE = 0xC0

    # Power constants
    SX126X_Power_22dBm = 0x00
    SX126X_Power_17dBm = 0x01
    SX126X_Power_13dBm = 0x02
    SX126X_Power_10dBm = 0x03

    # Lookup dictionaries
    lora_air_speed_dic = {
        1200: 0x01,
        2400: 0x02,
        4800: 0x03,
        9600: 0x04,
        19200: 0x05,
        38400: 0x06,
        62500: 0x07
    }

    lora_power_dic = {
        22: 0x00,
        17: 0x01,
        13: 0x02,
        10: 0x03
    }

    lora_buffer_size_dic = {
        240: SX126X_PACKAGE_SIZE_240_BYTE,
        128: SX126X_PACKAGE_SIZE_128_BYTE,
        64: SX126X_PACKAGE_SIZE_64_BYTE,
        32: SX126X_PACKAGE_SIZE_32_BYTE
    }

    def __init__(self, uart_id, freq, addr, power, rssi, m0_pin="P6", m1_pin="P7",
                 air_speed=2400, net_id=0, buffer_size=240, crypt=0,
                 relay=False, lbt=False, wor=False):
        """
        Initialize the SX126x LoRa module

        Args:
            uart_id: UART ID (0, 1, 2, or 3 for OpenMV RT1062)
            freq: Frequency in MHz (410-493 or 850-930)
            addr: Node address (0-65535)
            power: Transmission power (10, 13, 17, or 22 dBm)
            rssi: Enable RSSI output (True/False)
            m0_pin: M0 control pin (default "P6", can be "P0", "P1", etc.)
            m1_pin: M1 control pin (default "P7", can be "P0", "P1", etc.)
            air_speed: Air data rate (1200, 2400, 4800, 9600, 19200, 38400, 62500)
            net_id: Network ID (0-255)
            buffer_size: Buffer size (32, 64, 128, 240)
            crypt: Encryption key (0-65535)
        """
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.power = power
        self.target_baud = 115200

        # Determine frequency parameters
        if freq > 850:
            self.start_freq = 850
            self.offset_freq = freq - 850
        elif freq > 410:
            self.start_freq = 410
            self.offset_freq = freq - 410
        else:
            raise ValueError("Frequency must be 410-493 MHz or 850-930 MHz")

        # Initialize GPIO pins for M0 and M1 with flexible pin naming
        self.m0_pin = self._init_pin(m0_pin, "M0")
        self.m1_pin = self._init_pin(m1_pin, "M1")

        print(f"[INFO] Using M0 pin: {m0_pin}, M1 pin: {m1_pin}")

        # Set module to configuration mode (M0=LOW, M1=HIGH)
        self.m0_pin.value(0)
        self.m1_pin.value(1)
        time.sleep(0.1)

        # Initialize UART at 9600 baud for configuration
        print(f"[INFO] Opening UART {uart_id} at 9600 baud for configuration")
        try:
            self.uart = UART(uart_id, baudrate=9600, bits=8, parity=None, stop=1, timeout=1000)
        except Exception as e:
            print(f"[ERROR] Failed to initialize UART {uart_id}: {e}")
            print("[INFO] Available UART IDs are typically 0, 1, 2, 3")
            print("[INFO] Make sure your LoRa module TX/RX are connected to the correct UART pins")
            raise

        time.sleep(0.3)

        # Configure the module
        self.set_config(freq, addr, power, rssi, air_speed, net_id, buffer_size, crypt, relay, lbt, wor)

        # Close and reopen at target baudrate
        print(f"[INFO] Reconfiguring UART to {self.target_baud} baud")
        self.uart.deinit()
        time.sleep(0.3)

        # Set to configuration mode again
        self.m0_pin.value(0)
        self.m1_pin.value(1)
        time.sleep(0.5)

        # Reopen UART at target baudrate
        try:
            self.uart = UART(uart_id, baudrate=self.target_baud, bits=8, parity=None, stop=1, timeout=1000)
        except Exception as e:
            print(f"[ERROR] Failed to reinitialize UART: {e}")
            raise

        time.sleep(0.3)

        # Set to normal mode (M0=LOW, M1=LOW)
        self.m0_pin.value(0)
        self.m1_pin.value(0)
        time.sleep(0.1)

        print("[INFO] SX126x initialization complete")

    def _init_pin(self, pin_name, pin_type):
        """Initialize a pin with flexible naming support"""
        pin_options = [
            pin_name,  # Try the provided pin name first
            f"P{pin_name}" if isinstance(pin_name, int) else pin_name,  # Add P prefix if numeric
            pin_name.replace("P", "") if pin_name.startswith("P") else f"P{pin_name}",  # Toggle P prefix
        ]

        # Add some common alternatives
        if pin_name in ["P6", "6"]:
            pin_options.extend(["P0", "P1", "P2", "P3", "P4", "P5"])
        elif pin_name in ["P7", "7"]:
            pin_options.extend(["P8", "P9", "P4", "P5"])

        for pin_option in pin_options:
            try:
                pin = Pin(pin_option, Pin.OUT)
                print(f"[INFO] {pin_type} pin initialized as {pin_option}")
                return pin
            except (ValueError, OSError):
                continue

        # If all options failed, show available information
        print(f"[ERROR] Could not initialize {pin_type} pin with any of: {pin_options}")
        print("[INFO] Common OpenMV RT1062 pins: P0, P1, P2, P3, P4, P5, P6, P7, P8, P9")
        print("[INFO] You can also try: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9")
        raise ValueError(f"Unable to initialize {pin_type} pin")

    def set_config(self, freq, addr, power, rssi, air_speed=2400,
                   net_id=0, buffer_size=240, crypt=0,
                   relay=False, lbt=False, wor=False):
        """Configure the LoRa module parameters"""

        # Set module to configuration mode
        self.m0_pin.value(0)
        self.m1_pin.value(1)
        time.sleep(0.1)

        # Calculate address bytes
        low_addr = addr & 0xff
        high_addr = (addr >> 8) & 0xff
        net_id_temp = net_id & 0xff

        # Calculate frequency offset
        if freq > 850:
            freq_temp = freq - 850
        elif freq > 410:
            freq_temp = freq - 410
        else:
            freq_temp = 0

        # Get configuration values from dictionaries
        air_speed_temp = self.lora_air_speed_dic.get(air_speed, 0x02)  # Default to 2400
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, 0x00)  # Default to 240
        power_temp = self.lora_power_dic.get(power, 0x00)  # Default to 22dBm

        # Set RSSI enable bit
        rssi_temp = 0x80 if rssi else 0x00

        # Calculate encryption key bytes
        l_crypt = crypt & 0xff
        h_crypt = (crypt >> 8) & 0xff

        # Build configuration register
        if not relay:
            self.cfg_reg[3] = high_addr
            self.cfg_reg[4] = low_addr
            self.cfg_reg[5] = net_id_temp
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20  # Enable noise RSSI
            self.cfg_reg[8] = freq_temp
            self.cfg_reg[9] = 0x43 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt
        else:
            # Relay configuration
            self.cfg_reg[3] = 0x01
            self.cfg_reg[4] = 0x02
            self.cfg_reg[5] = 0x03
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            self.cfg_reg[9] = 0x03 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt

        # Send configuration with retries
        for attempt in range(3):
            print(f"[INFO] Sending configuration (attempt {attempt + 1})")

            # Clear any pending data
            while self.uart.any():
                self.uart.read()

            self.uart.write(bytes(self.cfg_reg))
            time.sleep(0.3)

            if self.uart.any():
                time.sleep(0.1)
                response = self.uart.read()
                if response and len(response) > 0 and response[0] == 0xC1:
                    print("[INFO] Configuration successful")
                    print(f"[DEBUG] Config sent: {[hex(x) for x in self.cfg_reg]}")
                    print(f"[DEBUG] Response: {[hex(x) for x in response]}")
                    break
                else:
                    print(f"[WARN] Unexpected response: {response}")
            else:
                print(f"[WARN] No response on attempt {attempt + 1}")
                if attempt == 2:
                    print("[ERROR] Configuration failed after 3 attempts")

        # Return to normal mode
        self.m0_pin.value(0)
        self.m1_pin.value(0)
        time.sleep(0.1)

    def get_settings(self):
        """Read current configuration from the module"""
        # Set to configuration mode
        self.m0_pin.value(0)
        self.m1_pin.value(1)
        time.sleep(0.2)

        print("[INFO] Reading current settings...")

        # Clear input buffer
        while self.uart.any():
            self.uart.read()

        # Send get settings command
        self.uart.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep(0.5)

        if self.uart.any():
            response = self.uart.read()
            print(f"[DEBUG] Settings response: {[hex(b) for b in response] if response else 'None'}")

            if response and len(response) >= 12 and response[0] == 0xC1 and response[2] == 0x09:
                # Parse the response
                high_addr = response[3]
                low_addr = response[4]
                addr = (high_addr << 8) | low_addr
                net_id = response[5]
                freq = response[8] + self.start_freq

                print(f"[Config] Address: {addr}")
                print(f"[Config] Network ID: {net_id}")
                print(f"[Config] Frequency: {freq}.125 MHz")

                # Return to normal mode
                self.m0_pin.value(0)
                self.m1_pin.value(0)
                return response
            else:
                print("[ERROR] Invalid settings response")
        else:
            print("[ERROR] No response to settings request")

        # Return to normal mode
        self.m0_pin.value(0)
        self.m1_pin.value(0)
        return None

    def send_data(self, data):
        """
        Send data through LoRa

        Args:
            data: bytes or string to send
        """
        # Ensure normal transmission mode
        self.m0_pin.value(0)
        self.m1_pin.value(0)
        time.sleep(0.1)

        if isinstance(data, str):
            data = data.encode('utf-8')

        print(f"[SEND] Transmitting {len(data)} bytes: {data}")
        self.uart.write(data)
        time.sleep(0.1)

    def receive_data(self):
        """
        Check for and receive incoming LoRa data

        Returns:
            Received data as bytes, or None if no data
        """
        if self.uart.any():
            time.sleep(0.3)  # Wait for complete message
            data = self.uart.read()

            if data and len(data) >= 4:
                try:
                    # Parse LoRa packet format: [high_addr, low_addr, freq, payload..., rssi]
                    sender_addr = (data[0] << 8) + data[1]
                    sender_freq = data[2] + self.start_freq

                    if self.rssi and len(data) > 4:
                        payload = data[3:-1]
                        rssi_val = 256 - data[-1] if data[-1] > 0 else 0
                        print(f"[RECV] From addr {sender_addr}, freq {sender_freq}.125MHz")
                        print(f"[RECV] Payload: {payload}")
                        print(f"[RECV] RSSI: -{rssi_val}dBm")
                    else:
                        payload = data[3:]
                        print(f"[RECV] From addr {sender_addr}, freq {sender_freq}.125MHz")
                        print(f"[RECV] Payload: {payload}")

                    return payload
                except (IndexError, TypeError):
                    print(f"[RECV] Raw data (parsing failed): {data}")
                    return data
            else:
                print(f"[RECV] Raw data: {data}")
                return data

        return None

    def get_channel_rssi(self):
        """Get current channel noise RSSI"""
        # Ensure normal mode
        self.m0_pin.value(0)
        self.m1_pin.value(0)
        time.sleep(0.1)

        # Clear input buffer
        while self.uart.any():
            self.uart.read()

        # Send RSSI request
        self.uart.write(bytes([0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02]))
        time.sleep(0.5)

        if self.uart.any():
            response = self.uart.read()
            if response and len(response) >= 4 and response[0] == 0xC1 and response[1] == 0x00 and response[2] == 0x02:
                noise_rssi = 256 - response[3]
                print(f"[RSSI] Channel noise: -{noise_rssi}dBm")
                return noise_rssi
            else:
                print(f"[ERROR] Invalid RSSI response: {response}")
                return None
        else:
            print("[ERROR] No RSSI response")
            return None

# Test functions with flexible pin configuration
def test_send():
    """Test function for sending data"""
    try:
        # Initialize LoRa module with custom pins if needed
        # Change m0_pin and m1_pin if P6/P7 don't work
        lora = sx126x(uart_id=1, freq=868, addr=100, power=22, rssi=True,
                     m0_pin="P6", m1_pin="P7")  # Try "P0", "P1" etc. if these fail

        # Optional: Get current settings
        lora.get_settings()

        # Send test messages
        count = 0
        while True:
            message = f"Hello from OpenMV #{count}!"
            print(f"Sending: {message}")
            lora.send_data(message)
            count += 1
            time.sleep(5)  # Send every 5 seconds

    except Exception as e:
        print(f"[ERROR] Test send failed: {e}")
        print("[INFO] Try different pin combinations:")
        print("       m0_pin='P0', m1_pin='P1'")
        print("       m0_pin='P2', m1_pin='P3'")
        print("       m0_pin='P4', m1_pin='P5'")

def test_receive():
    """Test function for receiving data"""
    try:
        # Initialize LoRa module
        # Change m0_pin and m1_pin if P6/P7 don't work
        lora = sx126x(uart_id=1, freq=868, addr=200, power=22, rssi=True,
                     m0_pin="P6", m1_pin="P7")  # Try "P0", "P1" etc. if these fail

        # Optional: Get current settings
        lora.get_settings()

        # Continuous receive
        print("Listening for LoRa messages...")
        while True:
            data = lora.receive_data()
            if data:
                try:
                    decoded = data.decode('utf-8')
                    print(f"Decoded message: {decoded}")
                except:
                    print(f"Raw bytes: {data}")
            time.sleep(0.1)  # Small delay to prevent busy waiting

    except Exception as e:
        print(f"[ERROR] Test receive failed: {e}")
        print("[INFO] Try different pin combinations:")
        print("       m0_pin='P0', m1_pin='P1'")
        print("       m0_pin='P2', m1_pin='P3'")
        print("       m0_pin='P4', m1_pin='P5'")

# Quick pin test function
def test_pins():
    """Test which pins are available on your OpenMV board"""
    available_pins = []
    pin_names = ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]

    for pin_name in pin_names:
        try:
            pin = Pin(pin_name, Pin.OUT)
            pin.value(0)  # Test setting value
            available_pins.append(pin_name)
            print(f"[OK] Pin {pin_name} is available")
        except:
            print(f"[FAIL] Pin {pin_name} is not available")

    print(f"\n[INFO] Available pins: {available_pins}")
    print(f"[INFO] Use any two available pins for M0 and M1")

# Uncomment the function you want to test:
test_pins()    # Test which pins work on your board
# test_send()    # For sending
test_receive() # For receiving



# OpenMV v4.7.0; MicroPython v1.25.0-r0; OpenMV IMXRT1060 with MIMXRT1062DVJ6A
# Type "help()" for more information.
# >>> [OK] Pin P0 is available
# [OK] Pin P1 is available
# [OK] Pin P2 is available
# [OK] Pin P3 is available
# [OK] Pin P4 is available
# [OK] Pin P5 is available
# [OK] Pin P6 is available
# [OK] Pin P7 is available
# [OK] Pin P8 is available
# [OK] Pin P9 is available

# [INFO] Available pins: ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']
# [INFO] Use any two available pins for M0 and M1
# [INFO] M0 pin initialized as P6
# [INFO] M1 pin initialized as P7
# [INFO] Using M0 pin: P6, M1 pin: P7
# [INFO] Opening UART 1 at 9600 baud for configuration
# [INFO] Sending configuration (attempt 1)
# [INFO] Configuration successful
# [DEBUG] Config sent: ['0xc2', '0x0', '0x9', '0x0', '0xc8', '0x0', '0xe2', '0x20', '0x12', '0xc3', '0x0', '0x0']
# [DEBUG] Response: ['0xc1', '0x0', '0x9', '0x0', '0xc8', '0x0', '0xe2', '0x20', '0x12', '0xc3', '0x0', '0x0']
# [INFO] Reconfiguring UART to 115200 baud
# [INFO] SX126x initialization complete
# [INFO] Reading current settings...
# [DEBUG] Settings response: ['0x0', '0x0', '0x0']
# [ERROR] Invalid settings response
# Listening for LoRa messages...