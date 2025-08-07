import time
import machine
import uasyncio as asyncio
import binascii
import sys

# UART configuration
UART_PORT = 1
UART_BAUDRATE = 57600
uart = machine.UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

# Device Identification
NETID_MAP = {
    b'e076465dd7194025': ('A', 1),
    b'e076465dd7091027': ('B', 2),
    b'e076465dd7194211': ('C', 3)
}

# Get my device ID and role
my_id = binascii.hexlify(machine.unique_id())
if my_id not in NETID_MAP:
    print("Unknown device ID")
    sys.exit()

my_name, my_netid = NETID_MAP[my_id]
print(f"[INFO] Device: {my_name}, NETID: {my_netid}")

# Select a target for test communication
TARGETS = {'A': 'B', 'B': 'C', 'C': 'A'}
target_name = TARGETS[my_name]
target_netid = [v[1] for k, v in NETID_MAP.items() if v[0] == target_name][0]

# State variables
msgs_recd = []
msgs_sent = []
current_netid = my_netid

def change_netid(new_netid):
    global current_netid

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

    current_netid = new_netid
    print(f"NETID changed to {new_netid}")
    return True

def send_message(msg):
    uart.write((msg + "\n").encode())

def process_message(data):
    try:
        msg = data.decode().strip()
        if msg.startswith("MSG:"):
            sender = msg.split(":")[1]
            msgs_recd.append(sender)
            print(f"[RECV] From {sender} | Total received: {len(msgs_recd)}")
    except Exception as e:
        print(f"[ERROR] {e}")

async def radio_read():
    buffer = b""
    while True:
        while uart.any():
            byte = uart.read(1)
            buffer += byte
            if byte == b'\n':
                process_message(buffer)
                buffer = b""
        await asyncio.sleep(0.01)

def send_messages(n):
    global msgs_sent
    for i in range(n):
        msg = f"MSG:{my_name}:{current_netid}:{i}"
        send_message(msg)
        msgs_sent.append((msg, time.time()))
        print(f"[SEND] {msg}")
        await asyncio.sleep(2)

def summarize_received():
    print(f"\n=== SUMMARY by {my_name} ===")
    for peer in ['A', 'B', 'C']:
        if peer == my_name:
            continue
        count = msgs_recd.count(peer)
        print(f"Messages received from {peer}: {count}")
    print("============================\n")

async def main_loop():
    change_netid(my_netid)
    print("Sending messages")
    if my_name == "B":
        asyncio.run(send_messages(100))
    elif my_name == "A":
        asyncio.run(send_messages(5))
        # At 10 seconds
        change_netid(2)
        # At 15 seconds
        asyncio.run(send_messages(20))
        # At 55 seconds
        change_netid(1)
        asyncio.run(send_messages(20))
    elif my_name == "C":
        asyncio.run(send_messages(17))
        # At 35
        change_netid(2)
        # At 40
        asyncio.run(send_messages(5))
        # at 50
        change_netid(3)
        # at 55
        await asyncio.sleep(20)
        # at 75
        change_netid(2)
        # 80
        asyncio.run(send_messages(5))
        # 90
        change_netid(3)


async def run_all():
    asyncio.create_task(radio_read())
    await main_loop()

asyncio.run(run_all())
