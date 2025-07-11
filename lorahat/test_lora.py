import sx126x
import time
import threading
import socket
import sys
import numpy

FREQ = 868
AIRSPEED = 62500  # 62500 bps is the maximum speed for SX126x

MIN_SLEEP = 0.3
ACK_SLEEP = 1

def get_dev_addr():
    hn = socket.gethostname()
    if hn == "rpi7":
        return (7, 8)
    elif hn == "rpi8":
        return (8, 7)
    else:
        print(f"Unknown host {hn}")
        sys.exit(1)
    return None

# === CONFIGURE YOUR DEVICE ID HERE ===
my_addr, peer_addr = get_dev_addr()

# === LoRa Module Initialization ===
node = sx126x.sx126x(
    serial_num="/dev/ttyAMA0",  # or /dev/serial0 if that's what works
    freq=FREQ,
    addr=my_addr,
    power=22,
    rssi=True,
    air_speed=AIRSPEED,
    relay=False
)

print("\nPrinting config being sent to module...")
node.describe_config()

# print("Reading Lora settings...")
# node.get_settings()

def send_message(msgstr, dest, ackneeded=False, rssicheck=False):
    if len(msgstr) > 225:
        print(f"[NOT SENDING] Msg too long : {len(msgstr)} : {msgstr}")
        return
    payload = msgstr
    offset_freq = FREQ - 850
    data = (
        bytes([dest >> 8]) +
        bytes([dest & 0xFF]) +
        bytes([offset_freq]) +
        bytes([my_addr >> 8]) +
        bytes([my_addr & 0xFF]) +
        bytes([node.offset_freq]) +
        payload.encode()
    )
    msgs_sent.append((payload, time.time()))
    node.send(data)
    print(f"[SENT ] {payload} to {dest}")
    if ackneeded or rssicheck:
        time.sleep(ACK_SLEEP)
    else:
        time.sleep(MIN_SLEEP)

msgs_sent = []
msgs_recd = []

def ack_time(msg):
    for (m, t) in msgs_recd:
        if m == f"Ack:{msg}":
            return t
    return -1

def print_status():
    print(f"#### ******** Printing status after sending {len(msgs_sent)} Messages ****** ####")
    ackts = []
    for s,t in msgs_sent:
        ackt = ack_time(s)
        if ackt > 0:
            ackts.append(ackt-t)
    print(f"Actimes = {numpy.percentile(ackts, 50)}@50, {numpy.percentile(ackts, 90)}@90")

def send_messages():
    c180=""
    for i in range(15):
        c180 += "0123456789"
    for i in range(10000):
        if i > 0 and i % 10 == 0:
            print_status()
        msgstr = f"RSSICHECK-{i}"
        send_message(msgstr, peer_addr, False, True)
        msgstr = f"CHECKACK-{i}-{c180}"
        send_message(msgstr, peer_addr, True, False)

def radioreceive(rssideb=False):
    if node.ser.inWaiting() > 0:
        t1 = time.time()
        time.sleep(MIN_SLEEP)
        r_buff = node.ser.read(node.ser.inWaiting())
        print(r_buff)
        sender_addr = int(r_buff[0]<<8) + int(r_buff[1])
        msgstr = (r_buff[3:-1]).decode()
        printstr = f"## Received ## ## Totalsofar={len(msgs_recd)} From @{sender_addr} : Msg = {msgstr}"
        t2 = time.time()
        # printstr += f"  [time to read = {t2-t1}]"
        msgs_recd.append((msgstr, time.time()))
        if (rssideb or msgstr.find("RSSICHECK") >= 0 or msgstr.find("Ack") >= 0) and node.rssi:
            rssi = format(256-r_buff[-1:][0])
            noise_rssi = node.get_channel_rssi()
            printstr += f"    [rssi = {rssi}, noise = {noise_rssi}]"
        else:
            pass
        print(printstr)
        if msgstr.find("CHECKACK") == 0:
            send_message(f"Ack:{msgstr}", peer_addr)

def keep_receiving_bg():
    while True:
        try:
            radioreceive()
        except IndexError:
            print("[INFO ] No data received, retrying...")
            continue
        except Exception as e:
            print(f"[ERROR] Receiving failed: {e}")
            continue

def main():
    reader_thread = threading.Thread(target=keep_receiving_bg, daemon=True)
    reader_thread.start()
    if my_addr == 7:
        time.sleep(3600)
    elif my_addr == 8:
        send_messages()
    else:
        print("Unknown host")
        sys.exit(1)

if __name__ == "__main__":
    main()
