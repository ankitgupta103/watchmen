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
communicating = False

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

async def send_messages():
    global msgs_sent
    for i in range(5):  # Send 5 messages
        msg = f"MSG:{my_name}:{i}"
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
    global communicating

    while True:
        await asyncio.sleep(1)
        if communicating:
            continue  # wait until current communication is done

# Run everything
async def run_all():
    asyncio.create_task(radio_read())
    await main_loop()

try:
    asyncio.run(run_all())
except KeyboardInterrupt:
    print(f"\n[KEYBOARD INTERRUPT] Current NETID: {current_netid}")
    if current_netid == my_netid:
        # Switch to target NETID
        print(f"[ACTION] Switching to {target_name}'s NETID ({target_netid}) to communicate.")
        if change_netid(target_netid):
            print(f"[INFO] Now communicating with {target_name}")
            asyncio.run(send_messages())
            print("[INFO] Done. Switching back...")
            change_netid(my_netid)
        else:
            print("[ERROR] Failed to switch NETID.")
    else:
        print("[INFO] Already communicating. Switching back to own NETID.")
        change_netid(my_netid)

    summarize_received()
    print("[INFO] Restarting main loop...\n")
    asyncio.run(run_all())
