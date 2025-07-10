import RPi.GPIO as GPIO
import serial
import time

# === GPIO PINS for M0 and M1 ===
PIN_M0 = 22
PIN_M1 = 27

# === SERIAL CONFIGURATION ===
SERIAL_PORT = "/dev/ttyAMA0"
CONFIG_BAUD = 9600  # Always use 9600 to configure
STOP_BITS = serial.STOPBITS_TWO
TIMEOUT = 1

# # Lookup Tables
# UART_BAUD_TABLE = {
#     0x00: "1200", 0x20: "2400", 0x40: "4800", 0x60: "9600",
#     0x80: "19200", 0xA0: "38400", 0xC0: "57600", 0xE0: "115200"
# }
# AIR_SPEED_TABLE = {
#     0x01: "1200 bps", 0x02: "2400 bps", 0x03: "4800 bps",
#     0x04: "9600 bps", 0x05: "19200 bps", 0x06: "38400 bps", 0x07: "62500 bps"
# }
# PACKET_SIZE_TABLE = { 0x00: "240 bytes", 0x40: "128 bytes", 0x80: "64 bytes", 0xC0: "32 bytes" }
# POWER_TABLE = { 0x00: "22 dBm", 0x01: "17 dBm", 0x02: "13 dBm", 0x03: "10 dBm" }

# === DEFAULT CONFIG FRAME (volatile - lost after power off) ===
# Format: [0xC2, 0x00, 0x09, ADDH, ADDL, NETID, UART+AIR, PACKET+POWER, FREQ, OPTION, CRYPT_H, CRYPT_L]
# Address: 0x0000, NetID: 0x00, Baud: 9600, Air speed: 2400bps, Packet: 240, Power: 22dBm, Freq: 868MHz (offset 18)
DEFAULT_CONFIG_FRAME = [
    0xC2, 0x00, 0x09,        # Command: C2 = volatile, length = 9 bytes
    0x00, 0x00,              # ADDH = 0x00, ADDL = 0x00 (Node address = 0x0000)
    0x00,                    # NETID = 0x00
    0x60 + 0x02,             # UART = 9600 (0x60) + Air speed = 2400 (0x02)
    0x00 + 0x00 + 0x20,      # Packet size = 240 (0x00), Power = 22dBm (0x00), + 0x20 fixed bit
    0x12,                    # Frequency channel offset: 868 - 850 = 18 (0x12)
    0x43,                    # Option: Transparent mode, RSSI disabled
    0x00, 0x00               # Encryption key: disabled
]

def setup_gpio():
    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except ValueError:
        pass  # Mode already set
    GPIO.setup(PIN_M0, GPIO.OUT)
    GPIO.setup(PIN_M1, GPIO.OUT)

def set_mode(config=True):
    GPIO.output(PIN_M0, GPIO.LOW)
    GPIO.output(PIN_M1, GPIO.HIGH if config else GPIO.LOW)
    time.sleep(0.3)

def configure_to_default():
    setup_gpio()
    set_mode(config=True)

    try:
        with serial.Serial(SERIAL_PORT, CONFIG_BAUD, timeout=TIMEOUT, stopbits=STOP_BITS) as ser:
            ser.flushInput()
            print("Sending Default Config Frame:", ' '.join(f"{b:02X}" for b in DEFAULT_CONFIG_FRAME))
            ser.write(bytes(DEFAULT_CONFIG_FRAME))
            time.sleep(0.3)

            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print("Raw Response:", response.hex())
                if response[0] == 0xC1:
                    print("LoRa module configured to default values successfully.")
                else:
                    print("Unexpected response:", response)
            else:
                print("No response from LoRa module.")
    finally:
        set_mode(config=False)
        GPIO.cleanup()

if __name__ == "__main__":
    configure_to_default()
