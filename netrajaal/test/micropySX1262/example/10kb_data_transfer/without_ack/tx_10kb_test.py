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

sx = SX1262(
    spi_bus=SPI_BUS, clk=P2_SCLK, mosi=P0_MOSI, miso=P1_MISO, cs=P3_CS,
    irq=P13_DIO1, rst=P6_RST, gpio=P7_BUSY, spi_baudrate=2000000
)

sx.begin(freq=868.0, bw=500.0, sf=5, cr=5, power=14, preambleLength=8, crcOn=True, blocking=True)

test_data = bytes([i % 256 for i in range(DATA_SIZE)])
num_packets = (DATA_SIZE + MAX_PAYLOAD - 1) // MAX_PAYLOAD
packets = []

for i in range(num_packets):
    start_idx = i * MAX_PAYLOAD
    chunk = test_data[start_idx:start_idx + MAX_PAYLOAD]
    packets.append(bytes([i & 0xFF]) + chunk)

print(f"Transmitting {num_packets} packets...")
start_time = time.ticks_ms()

for i, packet in enumerate(packets):
    sx.send(packet)
    print(f"packet: {packet}")
    if (i + 1) % 10 == 0:
        print(f"Sent {i + 1}/{num_packets}")

tx_time = time.ticks_diff(time.ticks_ms(), start_time)
print(f"Initial TX: {tx_time} ms")

print("Waiting for missing packet list...")
time.sleep_ms(2000)

missing = []
timeout_start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), timeout_start) < 10000:
    msg, status = sx.recv(timeout_en=True, timeout_ms=2000)
    print(f"msg: {msg}")
    if status == 0 and len(msg) > 0:
        if msg[0] == 0xFF:
            missing = list(msg[1:])
            break

if missing:
    print(f"Retransmitting {len(missing)} packets...")
    retry_start = time.ticks_ms()
    for seq in missing:
        if seq < len(packets):
            sx.send(packets[seq])
    retry_time = time.ticks_diff(time.ticks_ms(), retry_start)
    print(f"Retry TX: {retry_time} ms")
    total_time = time.ticks_diff(time.ticks_ms(), start_time)
else:
    total_time = tx_time

print(f"\nTotal time: {total_time} ms ({total_time/1000:.3f} s)")
print(f"Rate: {DATA_SIZE * 1000 / total_time:.2f} bytes/s")

