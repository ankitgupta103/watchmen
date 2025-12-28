"""
API Test: Initialization and Configuration

This example demonstrates:
- SX1262 constructor with all parameters
- begin() method with all configuration options
- Error handling during initialization
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

print("=== SX1262 Initialization Test ===\n")

# Test 1: Basic initialization with default SPI settings
print("Test 1: Basic initialization with default SPI settings")
try:
    sx = SX1262(
        spi_bus=SPI_BUS,
        clk=P2_SCLK,
        mosi=P0_MOSI,
        miso=P1_MISO,
        cs=P3_CS,
        irq=P13_DIO1,
        rst=P6_RST,
        gpio=P7_BUSY
    )
    print("[OK] Initialization successful")
except Exception as e:
    print(f"[FAIL] Initialization failed: {e}")

# Test 2: Initialization with custom SPI settings
print("\nTest 2: Initialization with custom SPI settings")
try:
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
    print("[OK] Custom SPI initialization successful")
except Exception as e:
    print(f"[FAIL] Custom SPI initialization failed: {e}")

# Test 3: begin() with default parameters
print("\nTest 3: begin() with default parameters")
try:
    status = sx.begin(
        freq=868.0,
        bw=125.0,
        sf=9,
        cr=7,
        syncWord=0x12,
        power=14
    )
    if status == 0:
        print("[OK] Configuration successful (default parameters)")
    else:
        print(f"[FAIL] Configuration failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Configuration error: {e}")

# Test 4: begin() with all parameters
print("\nTest 4: begin() with all parameters")
try:
    status = sx.begin(
        freq=868.0,           # Frequency in MHz
        bw=125.0,             # Bandwidth in kHz
        sf=9,                 # Spreading Factor
        cr=7,                 # Coding Rate
        syncWord=0x12,        # Sync word
        power=14,             # TX power in dBm
        currentLimit=60.0,    # Current limit in mA
        preambleLength=8,     # Preamble length
        implicit=False,       # Explicit header
        implicitLen=0xFF,     # Implicit length
        crcOn=True,           # Enable CRC
        txIq=False,          # TX IQ inversion
        rxIq=False,          # RX IQ inversion
        tcxoVoltage=1.6,     # TCXO voltage
        useRegulatorLDO=False, # Use DC-DC regulator
        blocking=True         # Blocking mode
    )
    if status == 0:
        print("[OK] Full configuration successful")
    else:
        print(f"[FAIL] Full configuration failed with status: {status}")
except Exception as e:
    print(f"[FAIL] Full configuration error: {e}")

# Test 5: begin() with different frequency bands
print("\nTest 5: Testing different frequency bands")
frequencies = [433.0, 868.0, 915.0]
for freq in frequencies:
    try:
        status = sx.begin(
            freq=freq,
            bw=125.0,
            sf=9,
            cr=7,
            syncWord=0x12,
            power=14,
            blocking=True
        )
        if status == 0:
            print(f"[OK] Frequency {freq} MHz configured successfully")
        else:
            print(f"[FAIL] Frequency {freq} MHz failed: {status}")
    except Exception as e:
        print(f"[FAIL] Frequency {freq} MHz error: {e}")

# Test 6: begin() with different spreading factors
print("\nTest 6: Testing different spreading factors")
spreading_factors = [5, 7, 9, 12]
for sf in spreading_factors:
    try:
        status = sx.begin(
            freq=868.0,
            bw=125.0,
            sf=sf,
            cr=7,
            syncWord=0x12,
            power=14,
            blocking=True
        )
        if status == 0:
            print(f"[OK] Spreading Factor {sf} configured successfully")
        else:
            print(f"[FAIL] Spreading Factor {sf} failed: {status}")
    except Exception as e:
        print(f"[FAIL] Spreading Factor {sf} error: {e}")

# Test 7: begin() with different bandwidths
print("\nTest 7: Testing different bandwidths")
bandwidths = [125.0, 250.0, 500.0]
for bw in bandwidths:
    try:
        status = sx.begin(
            freq=868.0,
            bw=bw,
            sf=9,
            cr=7,
            syncWord=0x12,
            power=14,
            blocking=True
        )
        if status == 0:
            print(f"[OK] Bandwidth {bw} kHz configured successfully")
        else:
            print(f"[FAIL] Bandwidth {bw} kHz failed: {status}")
    except Exception as e:
        print(f"[FAIL] Bandwidth {bw} kHz error: {e}")

# Test 8: begin() with different TX power levels
print("\nTest 8: Testing different TX power levels")
power_levels = [0, 10, 14, 20]
for power in power_levels:
    try:
        status = sx.begin(
            freq=868.0,
            bw=125.0,
            sf=9,
            cr=7,
            syncWord=0x12,
            power=power,
            blocking=True
        )
        if status == 0:
            print(f"[OK] TX Power {power} dBm configured successfully")
        else:
            print(f"[FAIL] TX Power {power} dBm failed: {status}")
    except Exception as e:
        print(f"[FAIL] TX Power {power} dBm error: {e}")

print("\n=== Initialization Tests Complete ===")

