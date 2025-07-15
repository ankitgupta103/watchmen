import serial
import time

# Adjust your port if needed
ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=0.1)

received_packets = 0
expected_total = 1000
start_time = None

print(" Listening for 1000 packets...")

try:
    while received_packets < expected_total:
        line = ser.readline()
        if line:
            try:
                msg = line.decode('utf-8', errors='ignore').strip()
                if msg.startswith("DATA"):
                    parts = msg.split()
                    if len(parts) >= 2:
                        seq = parts[1]
                        if received_packets == 0:
                            start_time = time.time()

                        print(f" Received: {msg[:60]}...")

                        # Send ACK
                        ack = f"ACK {seq}\n"
                        ser.write(ack.encode())
                        print(f" Sent: {ack.strip()}")

                        received_packets += 1
            except Exception as e:
                print("Decode error:", e)

except KeyboardInterrupt:
    print(" Interrupted.")

finally:
    ser.close()

end_time = time.time()
duration = end_time - start_time if start_time else 0
print(f"\n All packets received.")
print(f" Time taken: {duration:.2f} sec")
print(f" Throughput: {(received_packets * 240) / 1024 / duration:.2f} KB/s")
