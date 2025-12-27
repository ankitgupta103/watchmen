"""
Simple RX Receiver for OpenMV RT1062 + Waveshare Core1262-868M

Minimal receiver script - continuously listens and prints received messages.
Configure the LoRa parameters to match your transmitter.
"""

from sx1262 import SX1262
from _sx126x import ERR_NONE, ERROR
try:
    from utime import sleep_ms
except ImportError:
    import time
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)

# Pin definitions
SPI_BUS = 1
P0_MOSI = 'P0'
P1_MISO = 'P1'
P2_SCLK = 'P2'
P3_CS = 'P3'
P6_RST = 'P6'
P7_BUSY = 'P7'
P13_DIO1 = 'P13'

# LoRa Configuration - MUST MATCH YOUR TRANSMITTER
FREQUENCY = 868.0      # MHz
BANDWIDTH = 125.0      # kHz
SPREADING_FACTOR = 9   # 5-12
CODING_RATE = 7        # 5-8
SYNC_WORD = 0x12       # 0x12 or 0x34

# Initialize
sx = SX1262(
    spi_bus=SPI_BUS,
    clk=P2_SCLK,
    mosi=P0_MOSI,
    miso=P1_MISO,
    cs=P3_CS,
    irq=P13_DIO1,
    rst=P6_RST,
    gpio=P7_BUSY,
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure LoRa
# NOTE: If you see strong RSSI but no packets, try changing txIq/rxIq:
# - Try: txIq=False, rxIq=True (RX IQ inverted)
# - Try: txIq=True, rxIq=False (TX IQ inverted)
# - Try: txIq=True, rxIq=True (Both inverted)
sx.begin(
    freq=FREQUENCY,
    bw=BANDWIDTH,
    sf=SPREADING_FACTOR,
    cr=CODING_RATE,
    syncWord=SYNC_WORD,
    power=14,
    txIq=False,   # Try True if packets not received
    rxIq=False,   # Try True if packets not received
    blocking=True
)

print("Receiver ready. Listening for messages...")
print("(If no messages received, check LoRa parameters match transmitter)")
print("-" * 60)

# Start RX mode explicitly
sx.startReceive()

# Receive loop
packet_count = 0
while True:
    msg, err = sx.recv(timeout_en=False)  # Blocking receive, no timeout
    
    if err == ERR_NONE and len(msg) > 0:
        packet_count += 1
        try:
            print(f"\n[#{packet_count}] RX: {msg.decode()}")
            print(f"    RSSI: {sx.getRSSI():.1f} dBm, SNR: {sx.getSNR():.1f} dB")
            print(f"    Length: {len(msg)} bytes")
        except:
            print(f"\n[#{packet_count}] RX (hex): {' '.join([f'{b:02X}' for b in msg])}")
            print(f"    RSSI: {sx.getRSSI():.1f} dBm")
            print(f"    Length: {len(msg)} bytes")
    elif err != ERR_NONE and err != -6:  # -6 is timeout, ignore it
        error_msg = ERROR.get(err, f"Error {err}")
        print(f"Error: {error_msg}")
        sleep_ms(100)

