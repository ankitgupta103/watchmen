import socket
import datetime

PORT = 5005  # must match OpenMV
BUFFER_SIZE = 1024

# Listen on all interfaces (0.0.0.0)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))

print(f"Listening for OpenMV logs on UDP port {PORT}...\n")

while True:
    data, addr = sock.recvfrom(BUFFER_SIZE)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {addr[0]}: {data.decode().strip()}")
