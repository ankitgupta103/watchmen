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

def _run_command(cmd):
    uart.write(cmd + b'\r\n')
    time.sleep(0.5)
    return uart.read()

def change_netid(new_netid):
    while uart.any():
        uart.read()  # clear buffer

    print(f"Changing NETID to {new_netid}...")
    time.sleep(1.2)
    uart.write(b"+++")
    time.sleep(1.2)

    response = uart.read()
    if response and b'OK' in response:
        print("Entered config mode.")
    else:
        print("Failed to enter config mode.")
        return False

    uart.write(f'ATS3={new_netid}\r\n'.encode())
    time.sleep(0.5)

    uart.write(b'AT&W\r\n')  # Save config
    time.sleep(0.5)

    uart.write(b'ATZ\r\n')  # Reboot
    time.sleep(2)

    print(f"NETID changed to {new_netid}")
    return True

def hard_reboot():
    if not enter_config_mode:
        print("Couldnt enter config mode")
        return
    uart.write(b'ATZ\r\n')
    time.sleep(0.5)
