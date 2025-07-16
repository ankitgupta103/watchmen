import uasyncio as asyncio
#import asyncio
import sys
import utime
import random
from machine import UART
import omv
#import serial

print_lock = asyncio.Lock() 

# === Constants for openmv system ===
UART_PORT = 1
UART_BAUDRATE = 57600

# === Constants for Rpi system ===
USBA_PORT = "/dev/ttyUSB0"
USBA_BAUDRATE = 57600

# === Constants ===
MIN_SLEEP = 0.1
ACK_SLEEP = 0.3

clock_start = utime.ticks_ms() # get millisecond counter

# === Simulated sys.argv for MicroPython ===
# argv = sys.argv if hasattr(sys, "argv") else ["main.py", "1"]
# if len(argv) < 2:
#     print("Usage: main.py <device_id>")
#     sys.exit()

# device_id = int(argv[1])
my_addr = None
peer_addr = None

print("Running on device : " + omv.board_id())
if omv.board_id() == "5D4676E05D4676E05D4676E0":
    my_addr = 1
    peer_addr = 2
else:
    print("Unknown device ID for " + omv.board_id())
    sys.exit()

# === UART Init in Openmv ===
uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

# === UART Init in Rpi ===
#try:
#    uart = serial.Serial(USBA_PORT, USBA_BAUDRATE, timeout=0.1)
#except serial.SerialException as e:
#    print(f"[ERROR] Could not open serial port {USBA_PORT}: {e}")
#    sys.exit(1)

msgs_sent = []
msgs_unacked = []
msgs_recd = []

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), N(ack), C(hunk), e(V)ent

def time_msec():
    delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    return delta

# TypeSourceDestRRRandom
def get_msg_id(msgtype, dest):
    rrr = random.randint(100,999)
    mid = f"{msgtype}{my_addr}{dest}{rrr}"
    return mid

def radio_send(data):
    uart.write(data)

# === Send Function ===
async def send_msg(msgtype, msgstr, dest, ackneeded=False):
    if len(msgstr) > 225:
        async with print_lock:
            print("[NOT SENDING] Msg too long")
        return
    mid = get_msg_id(msgtype, dest)
    datastr = f"{mid};{msgstr}\n"
    data = datastr.encode()
    radio_send(data)
    msgs_sent.append((datastr, time_msec()))
    async with print_lock:
        print(f"[SENT ] {datastr} to {dest} at {time_msec()}")
    await asyncio.sleep(ACK_SLEEP if ackneeded else MIN_SLEEP)

# === Message Handling ===
def ack_time(msg):
    for (mid, msg, t) in msgs_recd:
        if mid == f"Ack:{msg}":
            return t
    return -1

async def print_status():
    await asyncio.sleep(1)
    async with print_lock:
        print("$$$$ %%%%% ###### Printing status ###### $$$$$$ %%%%%%%%")
        print(f"So far sent {len(msgs_sent)} messages and received {len(msgs_recd)} messages")
    ackts = []
    msgs_not_acked = []
    for s, t in msgs_sent:
        if s.startswith("Ack"):
            continue
        #print("Getting ackt for " + s + "which was sent at " + str(t))
        ackt = ack_time(s)
        if ackt > 0:
            time_to_ack = ackt - t
            ackts.append(time_to_ack)
        else:
            msgs_not_acked.append(s)
    if ackts:
        ackts.sort()
        mid = ackts[len(ackts)//2]
        p90 = ackts[int(len(ackts) * 0.9)]
        async with print_lock:
            print(f"[ACK Times] 50% = {mid:.2f}s, 90% = {p90:.2f}s")
            print(f"So far {len(msgs_not_acked)} messsages havent been acked")
            print(msgs_not_acked)

# === Async Sender ===
async def send_messages():
    long_string = ""
    for i in range(18):
        long_string += "_0123456789"
    for i in range(10000):
        if i > 0 and i % 10 == 0:
            asyncio.create_task(print_status())
        msg = f"MSG-{i}-{long_string}"
        await send_msg("H", msg, peer_addr)
        await asyncio.sleep(2)

# === Async Receiver for openmv ===
async def uart_receiver():
    buffer = b""
    while True:
        if uart.any():
            buffer = uart.readline()
            process_message(buffer)
        await asyncio.sleep(0.01)

# === Async Receiver for rpi ===
# async def uart_receiver():
#     buffer = b""
#     while True:
#         await asyncio.sleep(0.01)
#         while uart.in_waiting > 0:
#             byte = uart.read(1)
#             if byte == b'\n':
#                 process_message(buffer)
#                 buffer = b""
#             else:
#                 buffer += byte

def process_message(data):
    if len(data) < 8:
        return
    mid = data[0:6]
    sender = mid[1]
    receiver = mid[2]
    msg = data[7:].decode().strip()
    if my_addr != receiver:
        print(f"Skipping message as it is not for me but for {receiver} : {mid}")
        return
    print(f"[RECV ] MID: {mid}: {msg} at {time_msec()}")
    msgs_recd.append((mid, msg, time_msec()))
    if not msg.startswith("Ack"):
        asyncio.create_task(send_msg("A", f"{msgid}", peer_addr))

# === Main Entry ===
async def main():
    print(f"[INFO] Started device {my_addr} listening for {peer_addr}")
    asyncio.create_task(uart_receiver())
    print(get_msg_id("H", 2))
    if my_addr == 1:
        await send_messages()        
        await asyncio.sleep(3600)
    elif my_addr == 2:
        await asyncio.sleep(2)
        await send_messages()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped.")
