import time
from sx1262 import SX1262

SPI_BUS = 1
P0_MOSI = 'P0'
P1_MISO = 'P1'
P2_SCLK = 'P2'
P3_CS = 'P3'
P6_RST = 'P6'
P7_BUSY = 'P7'
P13_DIO1 = 'P13'

DATA_SIZE = 10 * 1024
MAX_PAYLOAD = 254
ACK_TIMEOUT = 5000
MAX_RETRIES = 5

print("Initializing SX1262...")
sx = SX1262(
    spi_bus=SPI_BUS, clk=P2_SCLK, mosi=P0_MOSI, miso=P1_MISO, cs=P3_CS,
    irq=P13_DIO1, rst=P6_RST, gpio=P7_BUSY, spi_baudrate=2000000
)

print("Configuring LoRa...")
sx.begin(freq=868.0, bw=500.0, sf=5, cr=5, power=14, preambleLength=8, crcOn=True, blocking=True)
print("SX1262 ready!\n")

test_data = bytes([i % 256 for i in range(DATA_SIZE)])
num_packets = (DATA_SIZE + MAX_PAYLOAD - 1) // MAX_PAYLOAD
print(f"Sending {DATA_SIZE} bytes in {num_packets} packets\n")

start_time = time.ticks_ms()
total_sent = 0
total_retries = 0

for packet_num in range(num_packets):
    start_idx = packet_num * MAX_PAYLOAD
    chunk = test_data[start_idx:start_idx + MAX_PAYLOAD]
    packet = bytes([packet_num & 0xFF]) + chunk
    
    ack_received = False
    retry_count = 0
    
    while not ack_received and retry_count <= MAX_RETRIES:
        if retry_count > 0:
            print(f"  Retry {retry_count}/{MAX_RETRIES}...")
            total_retries += 1
        
        sx.send(packet)
        time.sleep_ms(50)
        
        ack_start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), ack_start) < ACK_TIMEOUT:
            ack_msg, status = sx.recv(timeout_en=True, timeout_ms=1000)
            if status == 0 and len(ack_msg) >= 1 and ack_msg[0] == (packet_num & 0xFF):
                ack_received = True
                total_sent += len(chunk)
                print(f"Packet {packet_num + 1}/{num_packets}: Sent {len(chunk)} bytes, ACK received (Total: {total_sent}/{DATA_SIZE} bytes)")
                break
        
        if not ack_received:
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                print(f"  ACK timeout for packet {packet_num + 1}, retrying...")
    
    if not ack_received:
        print(f"Packet {packet_num + 1} failed after {MAX_RETRIES} retries")
        break

elapsed_ms = time.ticks_diff(time.ticks_ms(), start_time)
elapsed_s = elapsed_ms / 1000.0

print("\nTRANSMISSION COMPLETE")
print(f"Total: {total_sent} bytes ({total_sent / 1024:.2f} KB)")
print(f"Packets: {num_packets}, Retries: {total_retries}")
print(f"Time: {elapsed_ms} ms ({elapsed_s:.3f} s)")
if elapsed_s > 0:
    print(f"Rate: {total_sent / elapsed_s:.2f} bytes/s ({total_sent * 8 / elapsed_s / 1000:.2f} kbps)")
