"""
IQ Inversion Test - Most Common Fix for Strong Signal but No Packets

If RSSI shows strong signal (-28 dBm in your case) but no packets received,
the issue is almost always IQ inversion mismatch between TX and RX.
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

print("=" * 70)
print("IQ Inversion Test - Testing 4 Critical Configurations")
print("=" * 70)
print("Strong RSSI (-28 dBm) detected - trying IQ inversion fixes...")
print("=" * 70)

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

# Base configuration
FREQUENCY = 868.0
BANDWIDTH = 125.0
SPREADING_FACTOR = 9
CODING_RATE = 7

# Test the 4 most common configurations
test_configs = [
    {'sync': 0x12, 'tx_iq': False, 'rx_iq': False, 'desc': 'Standard (txIQ=False, rxIQ=False)'},
    {'sync': 0x12, 'tx_iq': False, 'rx_iq': True, 'desc': 'RX IQ Inverted (txIQ=False, rxIQ=True)'},
    {'sync': 0x12, 'tx_iq': True, 'rx_iq': False, 'desc': 'TX IQ Inverted (txIQ=True, rxIQ=False)'},
    {'sync': 0x12, 'tx_iq': True, 'rx_iq': True, 'desc': 'Both IQ Inverted (txIQ=True, rxIQ=True)'},
    {'sync': 0x34, 'tx_iq': False, 'rx_iq': False, 'desc': 'Standard + Sync 0x34 (txIQ=False, rxIQ=False)'},
    {'sync': 0x34, 'tx_iq': False, 'rx_iq': True, 'desc': 'RX IQ Inverted + Sync 0x34 (txIQ=False, rxIQ=True)'},
    {'sync': 0x34, 'tx_iq': True, 'rx_iq': False, 'desc': 'TX IQ Inverted + Sync 0x34 (txIQ=True, rxIQ=False)'},
    {'sync': 0x34, 'tx_iq': True, 'rx_iq': True, 'desc': 'Both IQ Inverted + Sync 0x34 (txIQ=True, rxIQ=True)'},
]

for idx, config in enumerate(test_configs, 1):
    print(f"\n[{idx}/{len(test_configs)}] Testing: {config['desc']}")
    print(f"    Sync Word: 0x{config['sync']:02X}")
    
    try:
        status = sx.begin(
            freq=FREQUENCY,
            bw=BANDWIDTH,
            sf=SPREADING_FACTOR,
            cr=CODING_RATE,
            syncWord=config['sync'],
            power=14,
            currentLimit=60.0,
            preambleLength=8,
            implicit=False,
            crcOn=True,
            txIq=config['tx_iq'],
            rxIq=config['rx_iq'],
            tcxoVoltage=1.6,
            useRegulatorLDO=False,
            blocking=True
        )
        
        if status != ERR_NONE:
            print(f"    ✗ Configuration failed")
            continue
        
        # Try to receive for 3 seconds
        received = False
        for attempt in range(30):  # 30 attempts x 100ms = 3 seconds
            msg, err = sx.recv(timeout_en=True, timeout_ms=100)
            
            if err == ERR_NONE and len(msg) > 0:
                print(f"\n    🎉 SUCCESS! Configuration found!")
                print(f"    Received: {msg}")
                try:
                    print(f"    Text: {msg.decode()}")
                except:
                    print(f"    Hex: {' '.join([f'{b:02X}' for b in msg])}")
                print(f"    Length: {len(msg)} bytes")
                try:
                    print(f"    RSSI: {sx.getRSSI():.2f} dBm")
                    print(f"    SNR: {sx.getSNR():.2f} dB")
                except:
                    pass
                
                print(f"\n    ✅ USE THESE SETTINGS IN YOUR RX SCRIPT:")
                print(f"    sx.begin(")
                print(f"        freq={FREQUENCY},")
                print(f"        bw={BANDWIDTH},")
                print(f"        sf={SPREADING_FACTOR},")
                print(f"        cr={CODING_RATE},")
                print(f"        syncWord=0x{config['sync']:02X},")
                print(f"        txIq={config['tx_iq']},")
                print(f"        rxIq={config['rx_iq']},")
                print(f"        blocking=True")
                print(f"    )")
                received = True
                break
            sleep_ms(100)
        
        if not received:
            print(f"    ✗ No packet received")
            
    except Exception as e:
        print(f"    ✗ Exception: {e}")
        continue
    
    if received:
        print("\n" + "=" * 70)
        print("✅ WORKING CONFIGURATION FOUND!")
        print("=" * 70)
        break

if not received:
    print("\n" + "=" * 70)
    print("⚠ IQ inversion test didn't find a match.")
    print("Try running rx_deep_troubleshoot.py for more comprehensive testing.")
    print("=" * 70)

