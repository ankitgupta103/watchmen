from machine import UART
import time

# Initialize UART1 (TX=P4, RX=P5)
uart = UART(1, baudrate=57600, timeout_char=1000)

total_packets = 1000
packet_size = 240
max_retries = 3
timeout_ms = 3000

def wait_for_ack(seq_no):
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
        if uart.any():
            try:
                data = uart.readline()
                if data:
                    print(" Got:", data)
                    msg = data.decode().strip()
                    if msg.startswith("ACK"):
                        parts = msg.split()
                        if parts[1] == f"{seq_no:04d}":
                            return True
            except Exception as e:
                print("Decode error:", e)
    return False

print(" Starting transmission...")

start_time = time.ticks_ms()

for i in range(1, total_packets + 1):
    header = f"DATA {i:04d} "
    payload = "X" * (packet_size - len(header) - 1)
    packet = header + payload + "\n"

    retry_count = 0
    while retry_count < max_retries:
        uart.write(packet)
        print(f"Sent packet {i} (try {retry_count + 1})")

        if wait_for_ack(i):
            print(f"ACK received for {i}")
            break
        else:
            print(f" Retry {retry_count + 1} for packet {i}")
            retry_count += 1

    if retry_count >= max_retries:
        print(f" Failed to get ACK for packet {i}, aborting.")
        break

end_time = time.ticks_ms()
duration = time.ticks_diff(end_time, start_time) / 1000.0

print(" Transmission complete.")
print(" Time taken:", duration, "sec")
print(" Throughput:", (i * packet_size) / 1024 / duration, "KB/s")
