import time
from machine import UART

# Configure UART (adjust TX/RX pins based on your board)
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

    # Set OPPRESEND = 1
    print(send_command(b'ATS7=1'))

    raw = send_command(b'ATI5')
    parse_ati5_response(raw)

    # Write to EEPROM and reboot
    print(send_command(b'AT&W'))
    print(send_command(b'ATZ'))


