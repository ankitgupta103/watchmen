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

EXPECTED_SIZE = 10 * 1024
MAX_PAYLOAD = 254

print("Initializing SX1262...")
sx = SX1262(
    spi_bus=SPI_BUS, clk=P2_SCLK, mosi=P0_MOSI, miso=P1_MISO, cs=P3_CS,
    irq=P13_DIO1, rst=P6_RST, gpio=P7_BUSY, spi_baudrate=2000000
)

print("Configuring LoRa...")
sx.begin(freq=868.0, bw=500.0, sf=5, cr=5, power=14, preambleLength=8, crcOn=True, blocking=True)
print("SX1262 ready! Waiting for data...\n")

received_data = bytearray()
packet_count = 0
expected_seq = 0
first_time = None
last_time = None

while len(received_data) < EXPECTED_SIZE:
    msg, status = sx.recv(timeout_en=True, timeout_ms=30000)
    
    if (status == 0 or status == -7) and len(msg) >= 1:
        packet_seq = msg[0]
        packet_data = msg[1:]
        
        if packet_seq == expected_seq:
            current_time = time.ticks_ms()
            if first_time is None:
                first_time = current_time
            last_time = current_time
            
            received_data.extend(packet_data)
            packet_count += 1
            expected_seq = (expected_seq + 1) & 0xFF
            
            print(f"Packet {packet_count} (seq {packet_seq}): {len(packet_data)} bytes (Total: {len(received_data)}/{EXPECTED_SIZE})")
            
            time.sleep_ms(50)
            sx.send(bytes([packet_seq]))
            
            if len(received_data) >= EXPECTED_SIZE:
                break

total_received = len(received_data)
if first_time and last_time:
    duration_ms = time.ticks_diff(last_time, first_time)
    duration_s = duration_ms / 1000.0
else:
    duration_ms = 0
    duration_s = 0.0

print("\nRECEPTION COMPLETE")
print(f"Received: {total_received} bytes ({total_received / 1024:.2f} KB)")
print(f"Packets: {packet_count}")
print(f"Duration: {duration_ms} ms ({duration_s:.3f} s)")
if duration_s > 0:
    print(f"Rate: {total_received / duration_s:.2f} bytes/s ({total_received * 8 / duration_s / 1000:.2f} kbps)")
