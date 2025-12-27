"""
Quick Start Example for OpenMV RT1062 + Waveshare Core1262-868M

Minimal code to get started with LoRa communication.
"""

from sx1262 import SX1262

# Initialize SX1262 with OpenMV RT1062 pin configuration
sx = SX1262(
    spi_bus=1,
    clk='P2',    # SCLK
    mosi='P0',   # MOSI
    miso='P1',   # MISO
    cs='P3',     # Chip Select
    irq='P13',   # DIO1 (IRQ)
    rst='P6',    # Reset
    gpio='P7',   # Busy
    spi_baudrate=2000000,
    spi_polarity=0,
    spi_phase=0
)

# Configure for LoRa mode (868 MHz, SF9, BW125kHz)
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
    syncWord=0x12,
    power=14,
    blocking=True
)

# Example: Send a message
sx.send(b"Hello, LoRa!")

# Example: Receive a message
msg, status = sx.recv(timeout_en=True, timeout_ms=5000)
if len(msg) > 0:
    print(f"Received: {msg.decode()}")

