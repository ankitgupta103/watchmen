"""
Simple TX Example for OpenMV RT1062 + Waveshare Core1262-868M

This example demonstrates basic LoRa transmission.
"""

import time
from sx1262 import SX1262

# Pin definitions for OpenMV RT1062
SPI_BUS = 1
P0_MOSI = 'P0'  # MOSI
P1_MISO = 'P1'  # MISO
P2_SCLK = 'P2'  # SCLK
P3_CS = 'P3'    # Chip Select
P6_RST = 'P6'   # Reset
P7_BUSY = 'P7'  # Busy
P13_DIO1 = 'P13'  # DIO1 (IRQ)

# SPI Configuration
SPI_BAUDRATE = 2000000
SPI_POLARITY = 0
SPI_PHASE = 0

# Initialize SX1262
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

# Configure LoRa (868 MHz, SF9, BW125kHz, CR7, 14dBm)
sx.begin(
    freq=868.0,
    bw=125.0,
    sf=9,
    cr=7,
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

# Transmit loop
counter = 0
while True:
    message = f"Hello World! Counter: {counter}"
    print(f"Transmitting: {message}")
    
    payload_len, status = sx.send(message.encode())
    print(f"Sent {payload_len} bytes. Status: {status}")
    
    counter += 1
    time.sleep(5)  # Wait 5 seconds between transmissions

