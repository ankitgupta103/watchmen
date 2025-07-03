import sx126x
import time
import threading
import socket

FREQ = 868

def get_dev_addr():
    hn = socket.gethostname()
    if hn == "rpi7":
        return (9, 8)
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
    air_speed=2400,
    relay=False
)

def send_message(seq_num):
    payload = f"MSG-{seq_num}"
    offset_freq = FREQ - 850
    data = (
        bytes([peer_addr >> 8]) +
        bytes([peer_addr & 0xFF]) +
        bytes([offset_freq]) +
        bytes([my_addr >> 8]) +
        bytes([my_addr & 0xFF]) +
        bytes([node.offset_freq]) +
        payload.encode()
    )
    node.send(data)
    print(f"[SENT ] {payload}")

def send_messages(num_messages):
    for i in range(num_messages):
        send_message(i)
        time.sleep(1)

def radioreceive():
    if node.ser.inWaiting() > 0:
        time.sleep(0.1)
        r_buff = node.ser.read(node.ser.inWaiting())
        #print("message is "+str(r_buff[3:-1]),end='\r\n')
        #print("receive message from node address with frequence\033[1;32m %d,%d.125MHz\033[0m"%((r_buff[0]<<8)+r_buff[1],r_buff[2]+node.start_freq),end='\r\n',flush = True)
        peer_addr = r_buff[0]<<8 + r_buff[1]
        msgstr = str(r_buff[3:-1])
        printstr = f"## Received ## ## From @{peer_addr} : Msg = {msgstr}"
        if node.rssi:
            # print('\x1b[3A',end='\r')
            rssi = format(256-r_buff[-1:][0])
            #print("the packet rssi value: -{0}dBm".format(256-r_buff[-1:][0]))
            noise_rssi = node.get_channel_rssi()
            printstr += f"    [rssi = {rssi}, noise = {noise_rssi}]"
        else:
            pass
            #print('\x1b[2A',end='\r')
        print(printstr)

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
        time.sleep(100)
    elif my_addr == 8:
        send_messages(100)
    else:
        print("Unknown host")
        sys.exit(1)

if __name__ == "__main__":
    main()
