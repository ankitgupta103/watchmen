"""
Deep Troubleshooting RX Receiver for OpenMV RT1062

Since RSSI shows -28 dBm (strong signal present), the issue is likely:
- IQ inversion mismatch (txIq/rxIq)
- Preamble length mismatch
- Implicit vs Explicit header mismatch
- CRC settings mismatch

This script systematically tests these critical parameters.
"""

from sx1262 import SX1262
from _sx126x import ERR_NONE, ERROR
try:
    from utime import sleep_ms, ticks_ms, ticks_diff
except ImportError:
    import time
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)
    def ticks_ms():
        return int(time.time() * 1000) & 0x7FFFFFFF
    def ticks_diff(end, start):
        diff = (end - start) & 0x7FFFFFFF
        return diff if diff < 0x40000000 else diff - 0x80000000

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
print("Deep Troubleshooting - Testing Critical Parameters")
print("=" * 70)
print("RSSI shows -28 dBm = STRONG SIGNAL PRESENT!")
print("Issue is likely IQ inversion, preamble, or header settings")
print("=" * 70)

# Initialize module
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
SYNC_WORD = 0x12  # Try 0x34 if this doesn't work

# Test configurations - systematically vary critical parameters
test_configs = []

# Standard configs with different IQ settings
for sync_word in [0x12, 0x34]:
    for tx_iq in [False, True]:
        for rx_iq in [False, True]:
            for preamble_len in [6, 8, 12, 16]:
                test_configs.append({
                    'freq': FREQUENCY,
                    'bw': BANDWIDTH,
                    'sf': SPREADING_FACTOR,
                    'cr': CODING_RATE,
                    'sync_word': sync_word,
                    'tx_iq': tx_iq,
                    'rx_iq': rx_iq,
                    'preamble': preamble_len,
                    'implicit': False,
                    'crc_on': True,
                    'desc': f"Sync:0x{sync_word:02X}, txIQ:{tx_iq}, rxIQ:{rx_iq}, Preamble:{preamble_len}"
                })

# Also test implicit header and CRC off
for sync_word in [0x12, 0x34]:
    test_configs.append({
        'freq': FREQUENCY,
        'bw': BANDWIDTH,
        'sf': SPREADING_FACTOR,
        'cr': CODING_RATE,
        'sync_word': sync_word,
        'tx_iq': False,
        'rx_iq': False,
        'preamble': 8,
        'implicit': True,
        'implicit_len': 32,  # Common implicit length
        'crc_on': True,
        'desc': f"Sync:0x{sync_word:02X}, Implicit Header, Preamble:8"
    })
    test_configs.append({
        'freq': FREQUENCY,
        'bw': BANDWIDTH,
        'sf': SPREADING_FACTOR,
        'cr': CODING_RATE,
        'sync_word': sync_word,
        'tx_iq': False,
        'rx_iq': False,
        'preamble': 8,
        'implicit': False,
        'crc_on': False,
        'desc': f"Sync:0x{sync_word:02X}, CRC Off, Preamble:8"
    })

print(f"\nTesting {len(test_configs)} configurations...")
print("This will take a few minutes. Press Ctrl+C to stop early if a match is found.\n")

found_match = False

for idx, config in enumerate(test_configs, 1):
    if found_match:
        break
        
    print(f"[{idx}/{len(test_configs)}] Testing: {config['desc']}")
    
    try:
        # Configure with these parameters
        status = sx.begin(
            freq=config['freq'],
            bw=config['bw'],
            sf=config['sf'],
            cr=config['cr'],
            syncWord=config['sync_word'],
            power=14,
            currentLimit=60.0,
            preambleLength=config['preamble'],
            implicit=config.get('implicit', False),
            implicitLen=config.get('implicit_len', 0xFF),
            crcOn=config.get('crc_on', True),
            txIq=config['tx_iq'],
            rxIq=config['rx_iq'],
            tcxoVoltage=1.6,
            useRegulatorLDO=False,
            blocking=True
        )
        
        if status != ERR_NONE:
            print(f"    ✗ Configuration failed: {ERROR.get(status, status)}")
            continue
        
        # Try to receive for 2 seconds
        start_time = ticks_ms()
        received = False
        
        while ticks_diff(ticks_ms(), start_time) < 2000:
            msg, err = sx.recv(timeout_en=True, timeout_ms=300)
            
            if err == ERR_NONE and len(msg) > 0:
                print(f"\n    🎉 SUCCESS! Configuration found!")
                print(f"    Data: {msg}")
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
                
                print(f"\n    ✅ USE THESE SETTINGS:")
                print(f"    FREQUENCY = {config['freq']}")
                print(f"    BANDWIDTH = {config['bw']}")
                print(f"    SPREADING_FACTOR = {config['sf']}")
                print(f"    CODING_RATE = {config['cr']}")
                print(f"    SYNC_WORD = 0x{config['sync_word']:02X}")
                print(f"    PREAMBLE_LENGTH = {config['preamble']}")
                print(f"    IMPLICIT = {config.get('implicit', False)}")
                if config.get('implicit', False):
                    print(f"    IMPLICIT_LEN = {config.get('implicit_len', 0xFF)}")
                print(f"    CRC_ON = {config.get('crc_on', True)}")
                print(f"    TX_IQ = {config['tx_iq']}")
                print(f"    RX_IQ = {config['rx_iq']}")
                received = True
                found_match = True
                break
                
            elif err == -6:  # Timeout
                continue
            elif err != ERR_NONE:
                # Non-timeout error, skip this config
                break
        
        if not received:
            print(f"    ✗ No packet received")
            
    except Exception as e:
        print(f"    ✗ Exception: {e}")
        continue

if not found_match:
    print("\n" + "=" * 70)
    print("⚠ No matching configuration found after testing all combinations.")
    print("\nPossible issues:")
    print("1. Transmitter may be using FSK mode instead of LoRa")
    print("2. Transmitter may be using a different frequency band (433 MHz, 915 MHz)")
    print("3. Hardware issue with antenna or module")
    print("4. Transmitter configuration is significantly different")
    print("=" * 70)
else:
    print("\n" + "=" * 70)
    print("✅ Matching configuration found! Use the settings above.")
    print("=" * 70)

