run_omv = True
try:
    import omv
    print("The 'omv' library IS installed.")
except ImportError:
    print("The 'omv' library is NOT installed.")
    run_omv = False

if run_omv:
    from machine import UART
    import uasyncio as asyncio
    import omv
    import utime
else:
    import asyncio
    import serial
    import time as utime
import sys
import random

print_lock = asyncio.Lock() 

# === Constants for openmv system ===
UART_BAUDRATE = 57600

# === Constants for Rpi system ===
USBA_BAUDRATE = 57600

# === Constants ===
MIN_SLEEP = 0.1
ACK_SLEEP = 0.3

my_addr = None
peer_addr = None

if run_omv:
    print("Running on device : " + omv.board_id())
    if omv.board_id() == "5D4676E05D4676E05D4676E0":
        my_addr = 1
        peer_addr = 2
    else:
        print("Unknown device ID for " + omv.board_id())
        sys.exit()
    clock_start = utime.ticks_ms() # get millisecond counter
    UART_PORT = 1
    uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
    uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)
else:
    my_addr = 2
    peer_addr = 1
    USBA_PORT = "/dev/tty.usbserial-0001"
    try:
        uart = serial.Serial(USBA_PORT, USBA_BAUDRATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open serial port {USBA_PORT}: {e}")
        sys.exit(1)
    clock_start = int(utime.time() * 1000)

msgs_sent = []
msgs_unacked = []
msgs_recd = []

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), N(ack), C(hunk), e(V)ent

def time_msec():
    if run_omv:
        delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    else:
        delta = int(utime.time() * 1000) - clock_start
    return delta

# TypeSourceDestRRRandom
def get_msg_id(msgtype, dest):
    rrr = random.randint(100,999)
    mid = f"{msgtype}{my_addr}{dest}{rrr}"
    return mid

def ack_needed(msgtype):
    if msgtype == "A":
        return False
    if msgtype == "H":
        return True
    return False

def radio_send(data):
    uart.write(data)
    print(f"[SENT ] {data.decode()} at {time_msec()}")

# === Send Function ===
async def send_msg(msgtype, msgstr, dest):
    if len(msgstr) > 225:
        async with print_lock:
            print("[NOT SENDING] Msg too long")
        return
    mid = get_msg_id(msgtype, dest)
    datastr = f"{mid};{msgstr}\n"
    ackneeded = ack_needed(msgtype)
    unackedid = 0
    timesent = time_msec()
    if ackneeded:
        unackedid = len(msgs_unacked)
        msgs_unacked.append((mid, msgstr, timesent))
    else:
        msgs_sent.append((mid, msgstr, timesent))
    if not ackneeded:
        radio_send(datastr.encode())
        return
    for retry_i in range(3):
        radio_send(datastr.encode())
        await asyncio.sleep(ACK_SLEEP if ackneeded else MIN_SLEEP)
        for i in range(3):
            at = ack_time(mid)
            if at > 0:
                print(f"Msg {mid} : was acked in {at - timesent} msecs")
                msgs_sent.append(msgs_unacked.pop(unackedid))
                return
            else:
                print(f"Still waiting for ack for {mid} # {i}")
                await asyncio.sleep(ACK_SLEEP * (i+1)) # progressively more sleep
        print(f"Failed to get ack for message {mid} for retry # {retry_i}")
    print(f"Failed to send message {mid}")


# === Message Handling ===
def ack_time(smid):
    for (rmid, msg, t) in msgs_recd:
        if rmid[0] == "A" and smid == msg:
            return t
    return -1

async def print_status():
    await asyncio.sleep(1)
    async with print_lock:
        print("$$$$ %%%%% ###### Printing status ###### $$$$$$ %%%%%%%%")
        print(f"So far sent {len(msgs_sent)} messages and received {len(msgs_recd)} messages")
    ackts = []
    msgs_not_acked = []
    for mid, msg, t in msgs_sent:
        if mid[0] == "A":
            continue
        #print("Getting ackt for " + s + "which was sent at " + str(t))
        ackt = ack_time(mid)
        if ackt > 0:
            time_to_ack = ackt - t
            ackts.append(time_to_ack)
        else:
            msgs_not_acked.append(mid)
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
    i = 0
    while True:
        i = i + 1
        if i > 0 and i % 10 == 0:
            asyncio.create_task(print_status())
        msg = f"MSG-{i}-{long_string}"
        await send_msg("H", msg, peer_addr)
        await asyncio.sleep(2)

# === Async Receiver for openmv ===
async def uart_receiver():
    if run_omv:
        buffer = b""
        while True:
            if uart.any():
                buffer = uart.readline()
                process_message(buffer)
            await asyncio.sleep(0.01)
    else:
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
    if len(data) < 8:
        return
    mid = data[0:6].decode()
    msgtype = mid[0]
    sender = int(mid[1])
    receiver = int(mid[2])
    msg = data[7:].decode().strip()
    if my_addr != receiver:
        print(f"Skipping message as it is not for me but for {receiver} : {mid}")
        return
    print(f"[RECV ] MID: {mid}: {msg} at {time_msec()}")
    msgs_recd.append((mid, msg, time_msec()))
    if msgtype != "A":
        asyncio.create_task(send_msg("A", f"{mid}", peer_addr))

# === Main Entry ===
async def main():
    print(f"[INFO] Started device {my_addr} listening for {peer_addr}")
    asyncio.create_task(uart_receiver())
    await send_messages() 
    # await asyncio.sleep(3600000)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopped.")
