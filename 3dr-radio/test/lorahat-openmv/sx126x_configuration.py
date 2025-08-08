# LoRa SX126x Configuration Script for OpenMV RT1062
# Use this script ONLY for configuring the LoRa module

import machine
import time
from machine import Pin, UART

class LoRaConfig:
    def __init__(self, uart_id=1, m0_pin='P6', m1_pin='P7'):
        # Pin setup for M0 and M1 using OpenMV pin names
        self.M0 = Pin(m0_pin, Pin.OUT)
        self.M1 = Pin(m1_pin, Pin.OUT)

        # Configuration register template
        self.cfg_reg = [0xC2, 0x00, 0x09, 0x00, 0x00, 0x00, 0x62, 0x00, 0x12, 0x43, 0x00, 0x00]

        # Dictionaries for configuration values
        self.lora_air_speed_dic = {
            1200: 0x01, 2400: 0x02, 4800: 0x03, 9600: 0x04,
            19200: 0x05, 38400: 0x06, 62500: 0x07
        }

        self.lora_power_dic = {22: 0x00, 17: 0x01, 13: 0x02, 10: 0x03}

        self.lora_buffer_size_dic = {
            240: 0x00, 128: 0x40, 64: 0x80, 32: 0xC0
        }

        # UART baudrate constants
        self.uart_baudrate_dic = {
            1200: 0x00, 2400: 0x20, 4800: 0x40, 9600: 0x60,
            19200: 0x80, 38400: 0xA0, 57600: 0xC0, 115200: 0xE0
        }

        # Initialize UART at 9600 for configuration
        print("[CONFIG] Initializing UART at 9600 baud for configuration...")
        self.uart = UART(uart_id, baudrate=9600)

    def set_config_mode(self):
        """Set module to configuration mode (M0=0, M1=1)"""
        self.M0.value(0)
        self.M1.value(1)
        time.sleep_ms(200)
        print("[CONFIG] Set to configuration mode (M0=0, M1=1)")

    def set_normal_mode(self):
        """Set module to normal mode (M0=0, M1=0)"""
        self.M0.value(0)
        self.M1.value(0)
        time.sleep_ms(100)
        print("[CONFIG] Set to normal mode (M0=0, M1=0)")

    def configure_module(self, freq, addr, power, uart_baud=9600, rssi=True,
                        air_speed=2400, net_id=0, buffer_size=240, crypt=0):
        """Configure the LoRa module with specified parameters"""

        print(f"\n[CONFIG] Starting configuration...")
        print(f"  Frequency: {freq} MHz")
        print(f"  Address: {addr}")
        print(f"  Power: {power} dBm")
        print(f"  UART Baud: {uart_baud}")
        print(f"  Air Speed: {air_speed}")
        print(f"  RSSI: {rssi}")

        # Set configuration mode
        self.set_config_mode()

        # Calculate frequency offset
        if freq > 850:
            start_freq = 850
            freq_temp = freq - 850
        else:
            start_freq = 410
            freq_temp = freq - 410

        # Prepare configuration values
        low_addr = addr & 0xff
        high_addr = (addr >> 8) & 0xff
        net_id_temp = net_id & 0xff

        air_speed_temp = self.lora_air_speed_dic.get(air_speed, 0x02)
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, 0x00)
        power_temp = self.lora_power_dic.get(power, 0x00)
        uart_baud_temp = self.uart_baudrate_dic.get(uart_baud, 0x60)

        rssi_temp = 0x80 if rssi else 0x00

        # Build configuration register
        self.cfg_reg[3] = high_addr
        self.cfg_reg[4] = low_addr
        self.cfg_reg[5] = net_id_temp
        self.cfg_reg[6] = uart_baud_temp + air_speed_temp
        self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20  # Enable noise RSSI
        self.cfg_reg[8] = freq_temp
        self.cfg_reg[9] = 0x43 + rssi_temp  # Enable packet RSSI if requested
        self.cfg_reg[10] = (crypt >> 8) & 0xff  # Crypt high byte
        self.cfg_reg[11] = crypt & 0xff         # Crypt low byte

        print(f"[CONFIG] Configuration bytes: {[hex(b) for b in self.cfg_reg]}")

        # Send configuration with retries
        success = False
        for attempt in range(3):
            print(f"[CONFIG] Configuration attempt {attempt + 1}/3")

            # Clear buffers
            while self.uart.any():
                self.uart.read()

            # Send configuration
            config_bytes = bytes(self.cfg_reg)
            self.uart.write(config_bytes)
            time.sleep_ms(500)  # Longer wait for config

            # Check response
            if self.uart.any():
                time.sleep_ms(100)
                response = self.uart.read()
                print(f"[CONFIG] Response: {[hex(b) for b in response]}")

                if response and len(response) >= 3 and response[0] == 0xC1:
                    print("[CONFIG] ✓ Configuration successful!")
                    success = True
                    break
                else:
                    print(f"[CONFIG] ✗ Unexpected response")
            else:
                print("[CONFIG] ✗ No response from module")
                time.sleep_ms(200)

        if not success:
            print("[CONFIG] ✗ Configuration failed after 3 attempts")
            return False

        # Return to normal mode
        self.set_normal_mode()
        return True

    def read_configuration(self):
        """Read current module configuration"""
        print("\n[CONFIG] Reading current configuration...")

        self.set_config_mode()

        # Clear buffer
        while self.uart.any():
            self.uart.read()

        # Send get settings command
        self.uart.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(1000)  # Wait longer for response

        if self.uart.any():
            response = self.uart.read()
            print(f"[CONFIG] Raw response: {[hex(b) for b in response]}")

            parsed = self.parse_config_response(response)
            self.set_normal_mode()
            return parsed
        else:
            print("[CONFIG] ✗ No response to configuration read")
            self.set_normal_mode()
            return None

    def parse_config_response(self, response_data):
        """Parse configuration response and display settings"""

        if not response_data or len(response_data) < 12:
            print(f"[CONFIG] ✗ Invalid response length: {len(response_data) if response_data else 0}")
            return None

        if response_data[0] != 0xC1 or response_data[2] != 0x09:
            print(f"[CONFIG] ✗ Invalid response header")
            return None

        # Parse configuration
        high_addr = response_data[3]
        low_addr = response_data[4]
        net_id = response_data[5]
        uart_air = response_data[6]
        sub_packet = response_data[7]
        freq_offset = response_data[8]
        trans_mode = response_data[9]
        crypt_high = response_data[10]
        crypt_low = response_data[11]

        # Calculate values
        address = (high_addr << 8) | low_addr
        frequency = freq_offset + (850 if freq_offset + 850 <= 930 else 410)

        # Parse UART baudrate
        uart_baud_code = uart_air & 0xE0
        uart_baud_map = {
            0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
            0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200
        }
        uart_baud = uart_baud_map.get(uart_baud_code, "Unknown")

        # Parse air speed
        air_code = uart_air & 0x07
        air_map = {
            0x01: 1200, 0x02: 2400, 0x03: 4800, 0x04: 9600,
            0x05: 19200, 0x06: 38400, 0x07: 62500
        }
        air_speed = air_map.get(air_code, "Unknown")

        # Parse power
        power_code = sub_packet & 0x03
        power_map = {0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10}
        power = power_map.get(power_code, "Unknown")

        # Parse buffer size
        buffer_code = sub_packet & 0xC0
        buffer_map = {0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32}
        buffer_size = buffer_map.get(buffer_code, "Unknown")

        # Parse features
        rssi_enabled = bool(trans_mode & 0x80)
        noise_rssi = bool(sub_packet & 0x20)

        # Display configuration
        print("\n" + "="*60)
        print("              LORA MODULE CONFIGURATION")
        print("="*60)
        print(f"Module Address      : {address}")
        print(f"Network ID          : {net_id}")
        print(f"Frequency           : {frequency}.125 MHz")
        print(f"UART Baudrate       : {uart_baud} bps")
        print(f"Air Data Rate       : {air_speed} bps")
        print(f"Buffer Size         : {buffer_size} bytes")
        print(f"TX Power            : {power} dBm")
        print(f"RSSI Output         : {'Enabled' if rssi_enabled else 'Disabled'}")
        print(f"Noise RSSI          : {'Enabled' if noise_rssi else 'Disabled'}")
        print(f"Encryption Key      : 0x{(crypt_high << 8 | crypt_low):04X}")
        print("="*60)

        return {
            'address': address,
            'network_id': net_id,
            'frequency': frequency,
            'uart_baudrate': uart_baud,
            'air_speed': air_speed,
            'buffer_size': buffer_size,
            'power': power,
            'rssi_enabled': rssi_enabled
        }

    def close(self):
        """Close UART connection"""
        if self.uart:
            self.uart.deinit()
        print("[CONFIG] UART closed")

# Configuration presets
PRESETS = {
    'default': {
        'freq': 868,
        'addr': 0,
        'power': 22,
        'uart_baud': 9600,
        'air_speed': 2400,
        'rssi': True
    },
    'long_range': {
        'freq': 868,
        'addr': 0,
        'power': 22,
        'uart_baud': 9600,
        'air_speed': 1200,  # Slower for longer range
        'rssi': True,
        'buffer_size': 32   # Smaller packets
    },
    'high_speed': {
        'freq': 868,
        'addr': 0,
        'power': 22,
        'uart_baud': 9600,
        'air_speed': 19200, # Faster air speed
        'rssi': True,
        'buffer_size': 240
    }
}

def quick_config(preset_name='default', addr=0):
    """Quick configuration using presets"""

    if preset_name not in PRESETS:
        print(f"[ERROR] Unknown preset: {preset_name}")
        print(f"Available presets: {list(PRESETS.keys())}")
        return False

    preset = PRESETS[preset_name].copy()
    preset['addr'] = addr  # Override address

    print(f"[CONFIG] Using preset: {preset_name}")
    print(f"[CONFIG] Settings: {preset}")

    config = LoRaConfig()

    try:
        success = config.configure_module(**preset)

        if success:
            print(f"\n[CONFIG] ✓ Module configured with preset '{preset_name}'")
            # Read back configuration to verify
            config.read_configuration()
        else:
            print(f"\n[CONFIG] ✗ Failed to configure with preset '{preset_name}'")

        return success

    finally:
        config.close()

def read_current_config():
    """Read and display current module configuration"""

    print("\n[CONFIG] Reading current module configuration...")

    config = LoRaConfig()

    try:
        current_config = config.read_configuration()

        if current_config:
            print("\n[CONFIG] ✓ Successfully read configuration")
            return current_config
        else:
            print("\n[CONFIG] ✗ Failed to read configuration")
            return None

    finally:
        config.close()

# Main execution examples
if __name__ == "__main__":
    print("LoRa SX126x Configuration Script")
    print("Available functions:")
    print("1. quick_config('default', addr=100)")
    print("2. interactive_config()")
    print("3. read_current_config()")
    print("\nExample usage:")
    print(">>> quick_config('default', addr=100)")

    # Uncomment the function you want to run:

    read_current_config()
    quick_config('default', addr=100)
    # interactive_config()
    read_current_config()





# =====================================================
# Device 1 config detail

# LoRa SX126x Configuration Script
# Available functions:
# 1. quick_config('default', addr=100)
# 2. interactive_config()
# 3. read_current_config()

# Example usage:
# >>> quick_config('default', addr=100)

# [CONFIG] Reading current module configuration...
# [CONFIG] Initializing UART at 9600 baud for configuration...

# [CONFIG] Reading current configuration...
# [CONFIG] Set to configuration mode (M0=0, M1=1)
# [CONFIG] Raw response: ['0xc1', '0x0', '0x9', '0x0', '0x64', '0x0', '0x62', '0x20', '0x12', '0xc3', '0x0', '0x0']

# ============================================================
#               LORA MODULE CONFIGURATION
# ============================================================
# Module Address      : 100
# Network ID          : 0
# Frequency           : 868.125 MHz
# UART Baudrate       : 9600 bps
# Air Data Rate       : 2400 bps
# Buffer Size         : 240 bytes
# TX Power            : 22 dBm
# RSSI Output         : Enabled
# Noise RSSI          : Enabled
# Encryption Key      : 0x0000
# ============================================================
# [CONFIG] Set to normal mode (M0=0, M1=0)

# [CONFIG] ✓ Successfully read configuration
# [CONFIG] UART closed
# [CONFIG] Using preset: default
# [CONFIG] Settings: {'uart_baud': 9600, 'air_speed': 2400, 'power': 22, 'rssi': True, 'addr': 100, 'freq': 868}
# [CONFIG] Initializing UART at 9600 baud for configuration...

# [CONFIG] Starting configuration...
#   Frequency: 868 MHz
#   Address: 100
#   Power: 22 dBm
#   UART Baud: 9600
#   Air Speed: 2400
#   RSSI: True
# [CONFIG] Set to configuration mode (M0=0, M1=1)
# [CONFIG] Configuration bytes: ['0xc2', '0x0', '0x9', '0x0', '0x64', '0x0', '0x62', '0x20', '0x12', '0xc3', '0x0', '0x0']
# [CONFIG] Configuration attempt 1/3
# [CONFIG] Response: ['0xc1', '0x0', '0x9', '0x0', '0x64', '0x0', '0x62', '0x20', '0x12', '0xc3', '0x0', '0x0']
# [CONFIG] ✓ Configuration successful!
# [CONFIG] Set to normal mode (M0=0, M1=0)

# [CONFIG] ✓ Module configured with preset 'default'

# [CONFIG] Reading current configuration...
# [CONFIG] Set to configuration mode (M0=0, M1=1)
# [CONFIG] Raw response: ['0xc1', '0x0', '0x9', '0x0', '0x64', '0x0', '0x62', '0x20', '0x12', '0xc3', '0x0', '0x0']

# ============================================================
#               LORA MODULE CONFIGURATION
# ============================================================
# Module Address      : 100
# Network ID          : 0
# Frequency           : 868.125 MHz
# UART Baudrate       : 9600 bps
# Air Data Rate       : 2400 bps
# Buffer Size         : 240 bytes
# TX Power            : 22 dBm
# RSSI Output         : Enabled
# Noise RSSI          : Enabled
# Encryption Key      : 0x0000
# ============================================================
# [CONFIG] Set to normal mode (M0=0, M1=0)
# [CONFIG] UART closed

# [CONFIG] Reading current module configuration...
# [CONFIG] Initializing UART at 9600 baud for configuration...

# [CONFIG] Reading current configuration...
# [CONFIG] Set to configuration mode (M0=0, M1=1)
# [CONFIG] Raw response: ['0xc1', '0x0', '0x9', '0x0', '0x64', '0x0', '0x62', '0x20', '0x12', '0xc3', '0x0', '0x0']

# ============================================================
#               LORA MODULE CONFIGURATION
# ============================================================
# Module Address      : 100
# Network ID          : 0
# Frequency           : 868.125 MHz
# UART Baudrate       : 9600 bps
# Air Data Rate       : 2400 bps
# Buffer Size         : 240 bytes
# TX Power            : 22 dBm
# RSSI Output         : Enabled
# Noise RSSI          : Enabled
# Encryption Key      : 0x0000
# ============================================================
# [CONFIG] Set to normal mode (M0=0, M1=0)

# [CONFIG] ✓ Successfully read configuration
# [CONFIG] UART closed
# OpenMV v4.7.0; MicroPython v1.25.0-r0; OpenMV IMXRT1060 with MIMXRT1062DVJ6A
# Type "help()" for more information.
