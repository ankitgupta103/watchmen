import uasyncio as asyncio
import time
import machine
import binascii
import sys

# Constants
UART_BAUDRATE = 57600
UART_PORT = 1
MESSAGE_INTERVAL = 5
TOTAL_MESSAGES = 100

# Global variables
msgs_recd = []
msgs_sent = []
my_addr = None
peer_addrs = []

# Initialize UART
uart = machine.UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

def get_dev_addr():
    global my_addr, peer_addrs
    uid = binascii.hexlify(machine.unique_id())

    if uid == b'e076465dd7194025':
        my_addr = 'A'
    elif uid == b'e076465dd7091027':
        my_addr = 'B'
    elif uid == b'e076465dd7194211':
        my_addr = 'C'
    else:
        print("Unknown device ID")
        sys.exit()

    # Define other peer nodes
    peer_addrs = [x for x in ['A', 'B', 'C'] if x != my_addr]
    print(f"[INFO] Device ID: {uid} mapped to address: {my_addr}")

def send_message(msgstr):
    uart.write((msgstr + "\n").encode())

def process_message(msg_bytes):
    global msgs_recd
    try:
        msg = msg_bytes.decode().strip()
        if msg.startswith("MSG:"):
            sender = msg.split(":")[1]
            msgs_recd.append(sender)
            print(f"[RECV] {msg_bytes} From {sender} | Total received: {len(msgs_recd)}")
    except Exception as e:
        print(f"[ERROR] Decoding message: {e}")

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
    for i in range(TOTAL_MESSAGES):
        await asyncio.sleep(MESSAGE_INTERVAL)
        msg = f"MSG:{my_addr}:{i}"
        send_message(msg)
        msgs_sent.append((msg, time.time()))
        print(f"[SEND] {msg}")
        if i % 10 == 0:
            summarize_received()

    await asyncio.sleep(5)  # Give some time to receive remaining messages
    summarize_received()

def summarize_received():
    print(f"\n=== SUMMARY by {my_addr} ===")
    counts = {peer: 0 for peer in peer_addrs}
    for sender in msgs_recd:
        if sender in counts:
            counts[sender] += 1

    for peer in peer_addrs:
        print(f"Messages received from {peer}: {counts[peer]} / {TOTAL_MESSAGES}")
    print("===========================\n")

async def main():
    get_dev_addr()
    asyncio.create_task(radio_read())
    await send_messages()
    while True:
        await asyncio.sleep(60)  # Keep running for background receiving

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Execution stopped.")
