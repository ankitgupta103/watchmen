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
num_packets = (EXPECTED_SIZE + MAX_PAYLOAD - 1) // MAX_PAYLOAD

sx = SX1262(
    spi_bus=SPI_BUS, clk=P2_SCLK, mosi=P0_MOSI, miso=P1_MISO, cs=P3_CS,
    irq=P13_DIO1, rst=P6_RST, gpio=P7_BUSY, spi_baudrate=2000000
)

sx.begin(freq=868.0, bw=500.0, sf=5, cr=5, power=14, preambleLength=8, crcOn=True, blocking=True)

received = {}
first_time = None
last_time = None
timeout_start = time.ticks_ms()
last_packet_time = None
NO_PACKET_TIMEOUT = 3000

print("Receiving packets...")
while len(received) < num_packets:
    msg, status = sx.recv(timeout_en=True, timeout_ms=2000)
    
    if len(msg) >= 1 and status == 0:
        seq = msg[0]
        if seq not in received:
            received[seq] = msg[1:]
            if first_time is None:
                first_time = time.ticks_ms()
            last_time = time.ticks_ms()
            last_packet_time = time.ticks_ms()
            if len(received) % 10 == 0:
                print(f"Received {len(received)}/{num_packets}")
    else:
        if last_packet_time and time.ticks_diff(time.ticks_ms(), last_packet_time) > NO_PACKET_TIMEOUT:
            break
        if not last_packet_time and time.ticks_diff(time.ticks_ms(), timeout_start) > 10000:
            break

missing = [i for i in range(num_packets) if i not in received]
print(f"\nReceived: {len(received)}/{num_packets}, Missing: {len(missing)}")

if missing:
    print("Sending missing packet list...")
    time.sleep_ms(1000)
    missing_msg = bytes([0xFF]) + bytes(missing)
    sx.send(missing_msg)
    
    print("Waiting for retransmissions...")
    retry_start = time.ticks_ms()
    while len(missing) > 0 and time.ticks_diff(time.ticks_ms(), retry_start) < 30000:
        msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
        if status == 0 and len(msg) >= 1:
            seq = msg[0]
            if seq in missing:
                received[seq] = msg[1:]
                missing.remove(seq)

total_received = sum(len(data) for data in received.values())
if first_time and last_time:
    duration = time.ticks_diff(last_time, first_time)
    print(f"\nDuration: {duration} ms ({duration/1000:.3f} s)")
    print(f"Rate: {total_received * 1000 / duration:.2f} bytes/s")
else:
    print("\nNo packets received")

