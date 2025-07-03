import sx126x
import time
import threading
import socket

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
    freq=868,
    addr=my_addr,
    power=22,
    rssi=True,
    air_speed=2400,
    relay=False
)

MAX_MESSAGES = 1000
TIMEOUT = 5  # seconds


def send_message(seq_num):
    payload = f"MSG-{seq_num} FROM-{my_addr}"
    offset_freq = 868 - 850
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

def keep_receiving_bg():
    while True:
        try:
            node.receive()
        except IndexError:
            print("[INFO ] No data received, retrying...")
            continue
        except Exception as e:
            print(f"[ERROR] Receiving failed: {e}")
            continue

def receive_message(expected_seq, respond=False):
    start = time.time()
    while time.time() - start < TIMEOUT:
        if node.ser.inWaiting() > 0:
            time.sleep(0.2)
            r_buff = node.ser.read(node.ser.inWaiting())
            if len(r_buff) < 7:
                continue

            src_addr = (r_buff[0] << 8) + r_buff[1]
            freq = r_buff[2] + node.start_freq
            payload_bytes = r_buff[6:]
            try:
                payload = payload_bytes.decode('utf-8', errors='ignore').strip()
            except Exception:
                payload = str(payload_bytes)

            print(f"[RECV] from {src_addr} @ {freq}MHz: {payload}")

            if f"FROM-{peer_addr}" in payload and f"MSG-{expected_seq}" in payload:
                print(f"[INFO ] Valid message: {payload}")
                if respond:
                    reply_message(expected_seq)
                return True
    return False


def main():
    reader_thread = threading.Thread(target=keep_receiving_bg, daemon=True)
    reader_thread.start()
    send_messages(100)

if __name__ == "__main__":
    main()
