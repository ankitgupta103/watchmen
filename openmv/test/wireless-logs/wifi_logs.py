import network, socket, time

# --- WiFi Credentials ---
SSID = "A"
PASSWORD = "123456789"

# --- Laptop IP & Port ---
LAPTOP_IP = "10.42.0.1"  # change if needed
PORT = 5005

# Connect to WiFi
print("Connecting to WiFi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

while not wlan.isconnected():
    time.sleep(1)
print("Connected, IP:", wlan.ifconfig()[0])

# Setup UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def log(msg):
    """Send log to laptop and also keep local print."""
    full_msg = f"[OpenMV] {msg}"
    sock.sendto(full_msg.encode(), (LAPTOP_IP, PORT))
    print(full_msg)

# Example logs
i = 0
while True:
    log(f"Heartbeat {i}")
    i += 1
    time.sleep(2)
