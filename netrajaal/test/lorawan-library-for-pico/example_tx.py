"""
SX1262 TX Example for OpenMV RT1062
Sends "HELLO_OPENMV" message repeatedly

Hardware Connections:
- P0 (MOSI) -> SX1262 MOSI
- P1 (MISO) -> SX1262 MISO
- P2 (SCK)  -> SX1262 SCK
- P3 (SS)   -> SX1262 NSS/CS
- P7        -> SX1262 BUSY
- P13       -> SX1262 RESET
- P6        -> SX1262 DIO1 (optional)
- GND       -> SX1262 GND
- 3.3V      -> SX1262 VCC
"""

from machine import SPI, Pin
import time
from sx1262 import SX1262, SF_7, BW_125, CR_4_5

# ============================================================================
# SPI Configuration
# ============================================================================

# OpenMV RT1062 SPI Bus 1
# P0 = MOSI, P1 = MISO, P2 = SCK, P3 = SS/CS
spi = SPI(
    1,
    baudrate=2000000,  # 2 MHz - safe for SX1262
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB
)

# ============================================================================
# GPIO Pin Configuration
# ============================================================================

# SPI CS (Chip Select)
cs = Pin("P3", Pin.OUT, value=1)

# SX1262 Control Pins
busy = Pin("P7", Pin.IN)      # BUSY pin (input)
reset = Pin("P13", Pin.OUT, value=1)  # RESET pin (output, high = normal)
dio1 = Pin("P6", Pin.IN)      # DIO1/IRQ pin (optional, for interrupt-driven operation)

# ============================================================================
# Initialize SX1262
# ============================================================================

print("Initializing SX1262...")
radio = SX1262(
    spi=spi,
    cs=cs,
    busy=busy,
    reset=reset,
    dio1=dio1,
    freq=868000000  # 868 MHz (EU868 band)
)

# ============================================================================
# Configure Radio Parameters
# ============================================================================

print("Configuring radio...")
radio.configure(
    frequency=868000000,      # 868 MHz
    sf=SF_7,                 # Spreading Factor 7 (good balance of range/speed)
    bw=BW_125,               # Bandwidth 125 kHz
    cr=CR_4_5,               # Coding Rate 4/5
    tx_power=14,             # TX Power 14 dBm
    preamble_length=12,      # Preamble length
    payload_length=0         # 0 = variable length packets
)

print("Radio configured successfully!")
print("Starting TX loop...")
print("-" * 50)

# ============================================================================
# TX Loop
# ============================================================================

message = "HELLO_OPENMV"
packet_count = 0

while True:
    try:
        # Send message
        print(f"Sending packet #{packet_count}: {message}")
        
        success = radio.send(message, timeout_ms=5000)
        
        if success:
            print(f"  ✓ TX successful")
            packet_count += 1
        else:
            print(f"  ✗ TX failed or timeout")
        
        # Wait before next transmission
        time.sleep_ms(2000)  # 2 second interval
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep_ms(1000)

