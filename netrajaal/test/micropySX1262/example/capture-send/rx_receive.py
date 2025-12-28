"""
RX Image Receive and Display
OpenMV RT1062 + Waveshare Core1262-868M

Receives image via SX1262 with ACK protocol and displays it.
Uses fastest LoRa settings for maximum speed.
"""

import sensor
import image
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

# Initialize camera (for display)
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
print("Camera initialized for display")

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
    print("Waiting for image...")

# Receive image header: [0xFF, width_hi, width_lo, height_hi, height_lo, size_bytes...]
print("Waiting for image header...")
img_size = None
img_width = None
img_height = None
while img_size is None:
    msg, status = sx.recv(timeout_en=True, timeout_ms=30000)
    if status == 0 and len(msg) >= 9 and msg[0] == 0xFF:
        img_width = int.from_bytes(msg[1:3], 'big')
        img_height = int.from_bytes(msg[3:5], 'big')
        img_size = int.from_bytes(msg[5:9], 'big')
        print(f"Image header: {img_width}x{img_height}, {img_size} bytes")
        sleep_ms(50)
        sx.send(bytes([0xFF]))  # ACK for header
        break

if img_size is None:
    print("Failed to receive image header")
else:
    # Receive image data
    received_data = bytearray()
    expected_seq = 0
    num_packets = (img_size + MAX_PAYLOAD_SIZE - 1) // MAX_PAYLOAD_SIZE
    print(f"Receiving {num_packets} packets...")
    print("=" * 60)
    
    start_time = ticks_ms()
    
    while len(received_data) < img_size:
        msg, status = sx.recv(timeout_en=True, timeout_ms=30000)
        
        if (status == 0 or status == -7) and len(msg) >= SEQ_NUM_SIZE:
            packet_seq = msg[0]
            packet_data = msg[SEQ_NUM_SIZE:]
            
            if packet_seq == expected_seq:
                received_data.extend(packet_data)
                expected_seq = (expected_seq + 1) & 0xFF
                
                status_str = "OK" if status == 0 else "CRC_ERR"
                print(f"Packet {len(received_data) // MAX_PAYLOAD_SIZE + 1}/{num_packets}: "
                      f"{len(packet_data)} bytes [{status_str}] "
                      f"({len(received_data)}/{img_size})")
                
                sleep_ms(50)
                
                # Send ACK
                ack = bytes([packet_seq])
                sx.send(ack)
                
                if len(received_data) >= img_size:
                    break
            else:
                # Out-of-order or duplicate packet - always send ACK to keep communication alive
                sleep_ms(50)
                ack = bytes([packet_seq])
                sx.send(ack)
                if packet_seq < expected_seq:
                    print(f"  Duplicate packet seq {packet_seq}, ACK sent")
    
    elapsed_ms = ticks_diff(ticks_ms(), start_time)
    elapsed_s = elapsed_ms / 1000.0
    
    print("=" * 60)
    print(f"Received: {len(received_data)}/{img_size} bytes in {elapsed_s:.2f}s")
    
    # Reconstruct and display image
    if len(received_data) >= img_size and img_width and img_height:
        print("Reconstructing image...")
        try:
            # Get JPEG compressed bytes
            jpeg_data = bytes(received_data[:img_size])
            
            # Create compressed image from JPEG bytes (1 byte per pixel for JPEG)
            compressed_img = image.Image(img_size, 1, jpeg_data, copy_to_fb=False)
            
            # Decompress JPEG to RGB565 image (returns mutable image)
            received_img = compressed_img.decompress(copy_to_fb=False)
            print("JPEG decompressed")
            
            # Display image on frame buffer (received_img is mutable)
            print("Displaying image...")
            sensor.get_fb().replace(received_img)
            print("Image displayed! Check OpenMV IDE.")
            
            # Keep displaying
            while True:
                sleep_ms(1000)
        except Exception as e:
            print(f"Error displaying image: {e}")
            import sys
            sys.print_exception(e)
    else:
        print("Incomplete image received")

print("\nReady for next image...")

