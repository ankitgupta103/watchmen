"""
TX Image Capture and Send
OpenMV RT1062 + Waveshare Core1262-868M

Captures an image and sends it via SX1262 with ACK protocol.
Uses fastest LoRa settings for maximum speed.
"""

import sensor
import time
try:
    from utime import ticks_ms, ticks_diff, sleep_ms
except ImportError:
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
    sleep_ms = time.sleep_ms if hasattr(time, 'sleep_ms') else lambda ms: time.sleep(ms / 1000.0)

from sx1262 import SX1262

# Pin definitions
SPI_BUS = 1
P2_SCLK = 'P2'
P0_MOSI = 'P0'
P1_MISO = 'P1'
P3_CS = 'P3'
P6_RST = 'P6'
P7_BUSY = 'P7'
P13_DIO1 = 'P13'

# SPI Configuration
SPI_BAUDRATE = 2000000
SPI_POLARITY = 0
SPI_PHASE = 0

# Protocol constants
MAX_PACKET_SIZE = 255
SEQ_NUM_SIZE = 1
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - SEQ_NUM_SIZE
MAX_RETRIES = 5
ACK_TIMEOUT_MS = 3000

# Initialize camera
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)  # 320x240
sensor.skip_frames(time=2000)
print("Camera initialized")

# Initialize SX1262
print("Initializing SX1262...")
sx = SX1262(
    spi_bus=SPI_BUS,
    clk=P2_SCLK,
    mosi=P0_MOSI,
    miso=P1_MISO,
    cs=P3_CS,
    irq=P13_DIO1,
    rst=P6_RST,
    gpio=P7_BUSY,
    spi_baudrate=SPI_BAUDRATE,
    spi_polarity=SPI_POLARITY,
    spi_phase=SPI_PHASE
)

# Configure for fastest speed: SF5, BW500kHz, CR5
print("Configuring LoRa (SF5, BW500kHz, CR5)...")
status = sx.begin(
    freq=868.0,
    bw=500.0,
    sf=5,
    cr=5,
    syncWord=0x12,
    power=14,
    currentLimit=60.0,
    preambleLength=8,
    implicit=False,
    crcOn=True,
    tcxoVoltage=1.6,
    useRegulatorLDO=False,
    blocking=True
)

if status != 0:
    print(f"Error initializing SX1262: {status}")
else:
    print("SX1262 ready!")

# Capture image
print("Capturing image...")
img = sensor.snapshot()
# Get raw image bytes (uncompressed RGB565)
img_bytes = img.bytearray()
img_size = len(img_bytes)
img_width = img.width()
img_height = img.height()
print(f"Image captured: {img_size} bytes ({img_width}x{img_height})")

# Send image header: [0xFF, width_hi, width_lo, height_hi, height_lo, size_bytes...]
# 0xFF = header marker, then 2 bytes width, 2 bytes height, 4 bytes size
header = bytes([0xFF]) + img_width.to_bytes(2, 'big') + img_height.to_bytes(2, 'big') + img_size.to_bytes(4, 'big')
print("Sending image header...")
sx.send(header)
sleep_ms(100)

# Wait for header ACK
ack_received = False
ack_start = ticks_ms()
while ticks_diff(ticks_ms(), ack_start) < ACK_TIMEOUT_MS:
    ack_msg, ack_status = sx.recv(timeout_en=True, timeout_ms=500)
    if ack_status == 0 and len(ack_msg) >= 1 and ack_msg[0] == 0xFF:
        ack_received = True
        print("Header ACK received")
        break
if not ack_received:
    print("Warning: No header ACK, continuing anyway...")

# Send image data in packets
num_packets = (img_size + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
print(f"Sending {img_size} bytes in {num_packets} packets...")
print("=" * 60)

start_time = ticks_ms()
total_sent = 0
retry_count = 0

for packet_num in range(num_packets):
    start_idx = packet_num * MAX_PAYLOAD_SIZE
    end_idx = min(start_idx + MAX_PAYLOAD_SIZE, img_size)
    chunk = img_bytes[start_idx:end_idx]
    
    packet_seq = packet_num & 0xFF
    packet = bytes([packet_seq]) + chunk
    
    ack_received = False
    retries = 0
    
    while not ack_received and retries <= MAX_RETRIES:
        if retries > 0:
            print(f"  Retry {retries}/{MAX_RETRIES}")
            retry_count += 1
        
        # Send packet
        payload_len, send_status = sx.send(packet)
        if send_status != 0:
            retries += 1
            continue
        
        sleep_ms(50)
        
        # Wait for ACK
        ack_timeout_start = ticks_ms()
        while ticks_diff(ticks_ms(), ack_timeout_start) < ACK_TIMEOUT_MS:
            ack_msg, ack_status = sx.recv(timeout_en=True, timeout_ms=500)
            if ack_status == 0 and len(ack_msg) >= 1:
                if ack_msg[0] == packet_seq:
                    ack_received = True
                    total_sent += len(chunk)
                    print(f"Packet {packet_num + 1}/{num_packets}: {len(chunk)} bytes OK")
                    break
            elif ack_status == -6:  # RX_TIMEOUT
                continue
        
        if not ack_received:
            retries += 1
    
    if not ack_received:
        print(f"Packet {packet_num + 1} failed after {MAX_RETRIES} retries")
        break

elapsed_ms = ticks_diff(ticks_ms(), start_time)
elapsed_s = elapsed_ms / 1000.0

print("=" * 60)
print(f"Transmission complete!")
print(f"Sent: {total_sent}/{img_size} bytes")
print(f"Retries: {retry_count}")
print(f"Time: {elapsed_s:.2f}s")
if elapsed_s > 0:
    print(f"Speed: {total_sent / elapsed_s:.0f} bytes/s")
print("=" * 60)

