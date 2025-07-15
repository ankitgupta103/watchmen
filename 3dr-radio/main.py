# import uasyncio as asyncio
import asyncio
import sys
import time
# from machine import UART
import serial

# === Constants for openmv system ===
UART_PORT = 1
UART_BAUDRATE = 57600

# === Constants for Rpi system ===
USBA_PORT = "/dev/ttyUSB0"
USBA_BAUDRATE = 57600

# === Constants ===
MIN_SLEEP = 0.1
ACK_SLEEP = 0.3

# === Simulated sys.argv for MicroPython ===
# argv = sys.argv if hasattr(sys, "argv") else ["main.py", "1"]
# if len(argv) < 2:
#     print("Usage: main.py <device_id>")
#     sys.exit()

# device_id = int(argv[1])
device_id = 2

# === Address Configuration ===
if device_id == 1:
    my_addr = 1
    peer_addr = 2
elif device_id == 2:
    my_addr = 2
    peer_addr = 1
else:
    print("Unknown device ID")
    sys.exit()

# # === UART Init in Openmv ===
# uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
# uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

# === UART Init in Rpi ===
try:
    uart = serial.Serial(USBA_PORT, USBA_BAUDRATE, timeout=0.1)
except serial.SerialException as e:
    print(f"[ERROR] Could not open serial port {USBA_PORT}: {e}")
    sys.exit(1)


msgs_sent = []
msgs_recd = []

# === Send Function ===
async def send_message(msgstr, dest, ackneeded=False):
    if len(msgstr) > 225:
        print("[NOT SENDING] Msg too long")
        return

    data = (
        bytes([dest]) +
        bytes([my_addr]) +
        msgstr.encode() +
        b'\n'
    )
    uart.write(data)
    msgs_sent.append((msgstr, time.time()))
    print(f"[SENT ] {msgstr} to {dest}")
    await asyncio.sleep(ACK_SLEEP if ackneeded else MIN_SLEEP)

# === Message Handling ===
def ack_time(msg):
    for (m, t) in msgs_recd:
        if m == f"Ack:{msg}":
            return t
    return -1

def print_status():
    ackts = []
    for s, t in msgs_sent:
        ackt = ack_time(s)
        if ackt > 0:
            ackts.append(ackt - t)
    if ackts:
        ackts.sort()
        mid = ackts[len(ackts)//2]
        p90 = ackts[int(len(ackts) * 0.9)]
        print(f"[ACK Times] 50% = {mid:.2f}s, 90% = {p90:.2f}s")

# === Async Sender ===
async def send_messages():
    long_string = "0123456789"
    for i in range(10000):
        if i > 0 and i % 10 == 0:
            print_status()
        msg = f"CHECKACK-{i}-{long_string}"
        await send_message(msg, peer_addr, ackneeded=True)

# # === Async Receiver for openmv ===
# async def uart_receiver():
#     buffer = b""
#     while True:
#         if uart.any():
#             byte = uart.read(1)
#             if byte == b'\n':
#                 process_message(buffer)
#                 buffer = b""
#             else:
#                 buffer += byte
#         await asyncio.sleep(0.01)

# === Async Receiver for rpi ===
async def uart_receiver():
    buffer = b""
    while True:
        await asyncio.sleep(0.01)
        while uart.in_waiting > 0:
            byte = uart.read(1)
            if byte == b'\n':
                process_message(buffer)
                buffer = b""
            else:
                buffer += byte

def process_message(data):
    if len(data) < 2:
        return
    sender = data[1]
    msg = data[2:].decode()
    print(f"[RECV ] From {sender}: {msg}")
    msgs_recd.append((msg, time.time()))
    if msg.startswith("CHECKACK"):
        asyncio.create_task(send_message(f"Ack:{msg}", peer_addr))

# === Main Entry ===
async def main():
    print(f"[INFO] Started device {my_addr} listening for {peer_addr}")
    asyncio.create_task(uart_receiver())

    if my_addr == 1:
        await asyncio.sleep(3600)
    elif my_addr == 2:
        await asyncio.sleep(2)
        await send_messages()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped.")




