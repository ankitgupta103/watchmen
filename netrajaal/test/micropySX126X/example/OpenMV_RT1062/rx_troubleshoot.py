"""
Troubleshooting RX Receiver for OpenMV RT1062

This script systematically tries different configurations to find the right one.
Run this while your transmitter is sending data.
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
print("LoRa Receiver Troubleshooting Tool")
print("=" * 70)
print("This script will try different configurations to find the right one.")
print("Make sure your transmitter is sending data while running this script.")
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

# Common configurations to try
configs = [
    # (freq, bw, sf, cr, sync_word, description)
    (868.0, 125.0, 9, 7, 0x12, "EU Standard (SF9, CR7, Sync 0x12)"),
    (868.0, 125.0, 9, 7, 0x34, "EU Standard (SF9, CR7, Sync 0x34)"),
    (868.0, 125.0, 7, 5, 0x12, "Fast (SF7, CR5, Sync 0x12)"),
    (868.0, 125.0, 7, 5, 0x34, "Fast (SF7, CR5, Sync 0x34)"),
    (868.0, 125.0, 12, 8, 0x12, "Long Range (SF12, CR8, Sync 0x12)"),
    (868.0, 125.0, 12, 8, 0x34, "Long Range (SF12, CR8, Sync 0x34)"),
    (868.0, 250.0, 9, 7, 0x12, "Wide Band (250kHz, SF9, CR7, Sync 0x12)"),
    (868.0, 250.0, 9, 7, 0x34, "Wide Band (250kHz, SF9, CR7, Sync 0x34)"),
    (868.1, 125.0, 9, 7, 0x12, "868.1 MHz (SF9, CR7, Sync 0x12)"),
    (868.1, 125.0, 9, 7, 0x34, "868.1 MHz (SF9, CR7, Sync 0x34)"),
]

for config_idx, (freq, bw, sf, cr, sync_word, desc) in enumerate(configs, 1):
    print(f"\n[{config_idx}/{len(configs)}] Trying: {desc}")
    print(f"    Frequency: {freq} MHz, BW: {bw} kHz, SF: {sf}, CR: {cr}, Sync: 0x{sync_word:02X}")
    
    # Configure with this set of parameters
    status = sx.begin(
        freq=freq,
        bw=bw,
        sf=sf,
        cr=cr,
        syncWord=sync_word,
        power=14,
        blocking=True
    )
    
    if status != ERR_NONE:
        print(f"    ✗ Configuration failed: {ERROR.get(status, status)}")
        continue
    
    print(f"    ✓ Configured. Listening for 3 seconds...")
    
    # Try to receive for 3 seconds
    start_time = ticks_ms()
    received = False
    
    while ticks_diff(ticks_ms(), start_time) < 3000:
        msg, err = sx.recv(timeout_en=True, timeout_ms=500)
        
        if err == ERR_NONE and len(msg) > 0:
            print(f"\n    🎉 SUCCESS! Packet received with this configuration!")
            print(f"    Data: {msg}")
            try:
                print(f"    Text: {msg.decode()}")
            except:
                pass
            print(f"    Length: {len(msg)} bytes")
            try:
                print(f"    RSSI: {sx.getRSSI():.2f} dBm")
                print(f"    SNR: {sx.getSNR():.2f} dB")
            except:
                pass
            print(f"\n    ✅ USE THESE SETTINGS:")
            print(f"    FREQUENCY = {freq}")
            print(f"    BANDWIDTH = {bw}")
            print(f"    SPREADING_FACTOR = {sf}")
            print(f"    CODING_RATE = {cr}")
            print(f"    SYNC_WORD = 0x{sync_word:02X}")
            received = True
            break
        elif err == -6:  # Timeout
            continue
        elif err != ERR_NONE:
            print(f"    Error: {ERROR.get(err, err)}")
            break
    
    if received:
        print("\n" + "=" * 70)
        print("Configuration found! Use these settings in your receiver script.")
        print("=" * 70)
        break
    else:
        print(f"    ✗ No packet received with this configuration")

if not received:
    print("\n" + "=" * 70)
    print("⚠ No packets received with any tested configuration.")
    print("\nTroubleshooting suggestions:")
    print("1. Verify transmitter is actually sending (check LED/status)")
    print("2. Check antennas are connected on both devices")
    print("3. Try moving devices closer together")
    print("4. Verify frequency range (EU: 868.0-868.6 MHz)")
    print("5. Check if transmitter uses different frequency (e.g., 433 MHz, 915 MHz)")
    print("6. Verify all hardware connections")
    print("=" * 70)

