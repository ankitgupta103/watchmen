import time
from machine import UART

# Configure UART - pins parameter is not required in this setup
uart = UART(1, baudrate=57600, timeout=1000)

def enter_config_mode():
    print("Clearing serial buffer...")
    while uart.any():
        uart.read()  # clear buffer

    print("Waiting before sending +++...")
    time.sleep(1.2)  # guard time before sending +++

    uart.write(b"+++")
    time.sleep(1.2)  # guard time after sending +++

    response = uart.read()
    if response and b'OK' in response:
        print("Entered CONFIG mode!\n")
    else:
        print("Failed to enter CONFIG mode.")
        return False
    return True

def send_command(cmd):
    uart.write(cmd + b'\r\n')
    time.sleep(0.5)
    return uart.read()

def parse_ati5_response(raw_response):
    if not raw_response:
        print("No response received.")
        return

    print("Parsed ATI5 Response:")
    lines = raw_response.decode().splitlines()
    for line in lines:
        if ':' in line:
            key, value = line.split('=', 1)
            print(f"  {key.strip()} = {value.strip()}")
        else:
            print(f"  {line.strip()}")

# Run everything
if enter_config_mode():

    raw = send_command(b'ATI5')
    parse_ati5_response(raw)

    # Set NETID to 25
    print(send_command(b'ATS3=25'))

    # Set ECC = ON
    print(send_command(b'ATS5=1'))

    # Turn off mavlink
    print(send_command(b'ATS6=0'))

    # Set OPPRESEND = 1
    print(send_command(b'ATS7=1'))

    # Using max channels = 50
    print(send_command(b'ATS10=50'))

    raw = send_command(b'ATI5')
    parse_ati5_response(raw)

    # Write to EEPROM and reboot
    print(send_command(b'AT&W'))
    print(send_command(b'ATZ'))




# ATI5 responce breakdown

# S1: SERIAL_SPEED = 57       → UART baud rate (x1000) → 57 → 57600 bps
# S2: AIR_SPEED = 64          → Over-the-air speed (kbps)
# S3: NETID = 25              → Network ID                                        (only radios with same NETID communicate)
# S4: TXPOWER = 20            → Transmit power (dBm)
# S5: ECC = 0                 → Error correction (0 = off, 1 = on)
# S6: MAVLINK = 1             → MAVLink framing enabled (0 = transparent)
# S7: OPPRESEND = 0           → Opportunistic resend (used for reliability)
# S8: MIN_FREQ = 433050       → Lower frequency bound (Hz × 1k)
# S9: MAX_FREQ = 434790       → Upper frequency bound (Hz × 1k)
# S10: NUM_CHANNELS = 10      → Number of hopping channels
# S11: DUTY_CYCLE = 100       → % of time allowed to transmit
# S12: LBT_RSSI = 0           → Listen Before Talk RSSI threshold (0 = disabled)
# S13: MANCHESTER = 0         → Manchester encoding (0 = off, 1 = on)
# S14: RTSCTS = 0             → Flow control (0 = disabled, 1 = enabled)
# S15: MAX_WINDOW = 131       → Max window size for resend (used with ECC)


# 1

# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'ATS3=25\r\nOK\r\n'
# b'ATS5=1\r\nOK\r\n'
# b'ATS7=1\r\nOK\r\n'
# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'AT&W\r\nOK\r\n'
# b'ATZ\xff'


# 2

# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 0
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 0
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'ATS3=25\r\nOK\r\n'
# b'ATS5=1\r\nOK\r\n'
# b'ATS7=1\r\nOK\r\n'
# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'AT&W\r\nOK\r\n'
# b'ATZ\xff'


# 3

# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 0
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 0
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'ATS3=25\r\nOK\r\n'
# b'ATS5=1\r\nOK\r\n'
# b'ATS7=1\r\nOK\r\n'
# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'AT&W\r\nOK\r\n'
# b'ATZ\xff'


# 4

# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'ATS3=25\r\nOK\r\n'
# b'ATS5=1\r\nOK\r\n'
# b'ATS7=1\r\nOK\r\n'
# Parsed ATI5 Response:

#   S1:SERIAL_SPEED = 57
#   S2:AIR_SPEED = 64
#   S3:NETID = 25
#   S4:TXPOWER = 20
#   S5:ECC = 1
#   S6:MAVLINK = 1
#   S7:OPPRESEND = 1
#   S8:MIN_FREQ = 433050
#   S9:MAX_FREQ = 434790
#   S10:NUM_CHANNELS = 10
#   S11:DUTY_CYCLE = 100
#   S12:LBT_RSSI = 0
#   S13:MANCHESTER = 0
#   S14:RTSCTS = 0
#   S15:MAX_WINDOW = 131
# b'AT&W\r\nOK\r\n'
# b'ATZ\xff'
