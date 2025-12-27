"""
OpenMV RT1062 + Waveshare Core1262-868M Test Suite

This comprehensive test suite demonstrates:
1. Basic initialization and configuration
2. Operation mode changes (Sleep, Standby, TX, RX)
3. LoRa parameter configuration
4. Transmit and receive operations
5. RSSI and SNR readings
6. Frequency changes
7. Power level changes
8. Blocking and non-blocking modes

Hardware Connections:
- P0: MOSI
- P1: MISO
- P2: SCLK (SPI Clock)
- P3: CS (Chip Select)
- P6: RESET
- P7: BUSY
- P13: DIO1 (IRQ)
"""

import sys
try:
    from utime import sleep_ms, ticks_ms, ticks_diff
except ImportError:
    # Fallback: use time module with conversions
    import time
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)
    def ticks_ms():
        return int(time.time() * 1000) & 0x7FFFFFFF
    def ticks_diff(end, start):
        diff = (end - start) & 0x7FFFFFFF
        return diff if diff < 0x40000000 else diff - 0x80000000

from sx1262 import SX1262
from _sx126x import ERR_NONE, ERROR

# Pin definitions for OpenMV RT1062
SPI_BUS = 1
P0_MOSI = 'P0'  # MOSI
P1_MISO = 'P1'  # MISO
P2_SCLK = 'P2'  # SCLK
P3_CS = 'P3'    # Chip Select
P6_RST = 'P6'   # Reset
P7_BUSY = 'P7'  # Busy
P13_DIO1 = 'P13'  # DIO1 (IRQ)

# SPI Configuration (as per user specification)
SPI_BAUDRATE = 2000000
SPI_POLARITY = 0
SPI_PHASE = 0

# LoRa Configuration
FREQUENCY = 868.0  # MHz (868 MHz for European ISM band)
BANDWIDTH = 125.0  # kHz
SPREADING_FACTOR = 9
CODING_RATE = 7
SYNC_WORD = 0x12   # Private sync word
TX_POWER = 14      # dBm
CURRENT_LIMIT = 60.0  # mA
PREAMBLE_LENGTH = 8
TCXO_VOLTAGE = 1.6  # V (adjust based on your module)

def print_status(message, status_code=ERR_NONE):
    """Print status message with error code if applicable."""
    if status_code == ERR_NONE:
        print(f"✓ {message}")
    else:
        error_msg = ERROR.get(status_code, f"Unknown error: {status_code}")
        print(f"✗ {message} - {error_msg}")

def test_initialization():
    """Test 1: Initialize the SX1262 module."""
    print("\n" + "="*60)
    print("TEST 1: Module Initialization")
    print("="*60)
    
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
        print_status("SX1262 object created successfully")
        return sx
    except Exception as e:
        print(f"✗ Failed to create SX1262 object: {e}")
        return None

def test_begin_lora(sx):
    """Test 2: Begin LoRa mode with default parameters."""
    print("\n" + "="*60)
    print("TEST 2: Begin LoRa Mode")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    status = sx.begin(
        freq=FREQUENCY,
        bw=BANDWIDTH,
        sf=SPREADING_FACTOR,
        cr=CODING_RATE,
        syncWord=SYNC_WORD,
        power=TX_POWER,
        currentLimit=CURRENT_LIMIT,
        preambleLength=PREAMBLE_LENGTH,
        implicit=False,
        implicitLen=0xFF,
        crcOn=True,
        txIq=False,
        rxIq=False,
        tcxoVoltage=TCXO_VOLTAGE,
        useRegulatorLDO=False,
        blocking=True
    )
    
    print_status(f"Begin LoRa mode (freq={FREQUENCY}MHz, bw={BANDWIDTH}kHz, sf={SPREADING_FACTOR})", status)
    return status == ERR_NONE

def test_operation_modes(sx):
    """Test 3: Test different operation modes."""
    print("\n" + "="*60)
    print("TEST 3: Operation Mode Changes")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    # Test Standby mode
    status = sx.standby()
    print_status("Set to Standby mode", status)
    sleep_ms(100)
    
    # Test Sleep mode
    status = sx.sleep(retainConfig=True)
    print_status("Set to Sleep mode (retain config)", status)
    sleep_ms(100)
    
    # Wake up from sleep (standby automatically wakes from sleep)
    status = sx.standby()
    print_status("Wake up to Standby mode", status)
    sleep_ms(100)
    
    return True

def test_parameter_changes(sx):
    """Test 4: Change LoRa parameters."""
    print("\n" + "="*60)
    print("TEST 4: LoRa Parameter Changes")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    # Change frequency
    new_freq = 868.5
    status = sx.setFrequency(new_freq)
    print_status(f"Change frequency to {new_freq} MHz", status)
    sleep_ms(50)
    
    # Change back to original frequency
    status = sx.setFrequency(FREQUENCY)
    print_status(f"Change frequency back to {FREQUENCY} MHz", status)
    sleep_ms(50)
    
    # Change spreading factor
    new_sf = 10
    status = sx.setSpreadingFactor(new_sf)
    print_status(f"Change spreading factor to {new_sf}", status)
    sleep_ms(50)
    
    # Change back
    status = sx.setSpreadingFactor(SPREADING_FACTOR)
    print_status(f"Change spreading factor back to {SPREADING_FACTOR}", status)
    sleep_ms(50)
    
    # Change bandwidth
    new_bw = 250.0
    status = sx.setBandwidth(new_bw)
    print_status(f"Change bandwidth to {new_bw} kHz", status)
    sleep_ms(50)
    
    # Change back
    status = sx.setBandwidth(BANDWIDTH)
    print_status(f"Change bandwidth back to {BANDWIDTH} kHz", status)
    sleep_ms(50)
    
    # Change coding rate
    new_cr = 8
    status = sx.setCodingRate(new_cr)
    print_status(f"Change coding rate to {new_cr}", status)
    sleep_ms(50)
    
    # Change back
    status = sx.setCodingRate(CODING_RATE)
    print_status(f"Change coding rate back to {CODING_RATE}", status)
    sleep_ms(50)
    
    # Change TX power
    new_power = 10
    status = sx.setOutputPower(new_power)
    print_status(f"Change TX power to {new_power} dBm", status)
    sleep_ms(50)
    
    # Change back
    status = sx.setOutputPower(TX_POWER)
    print_status(f"Change TX power back to {TX_POWER} dBm", status)
    sleep_ms(50)
    
    return True

def test_rssi_snr(sx):
    """Test 5: Read RSSI and SNR values."""
    print("\n" + "="*60)
    print("TEST 5: RSSI and SNR Readings")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    # Start RX mode to get RSSI
    status = sx.startReceive()
    print_status("Start RX mode for RSSI reading", status)
    sleep_ms(100)
    
    # Read RSSI
    try:
        rssi = sx.getRSSI()
        print(f"✓ RSSI: {rssi:.2f} dBm")
    except Exception as e:
        print(f"✗ Failed to read RSSI: {e}")
    
    # Read SNR (only available after receiving a packet in LoRa mode)
    try:
        snr = sx.getSNR()
        print(f"✓ SNR: {snr:.2f} dB")
    except Exception as e:
        print(f"ℹ SNR not available (no packet received yet): {e}")
    
    # Go back to standby
    sx.standby()
    return True

def test_transmit_blocking(sx):
    """Test 6: Transmit in blocking mode."""
    print("\n" + "="*60)
    print("TEST 6: Transmit (Blocking Mode)")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    test_message = b"Hello from OpenMV RT1062!"
    print(f"Transmitting message: {test_message.decode()}")
    
    payload_len, status = sx.send(test_message)
    print_status(f"Transmit completed (payload length: {payload_len})", status)
    
    return status == ERR_NONE

def test_receive_blocking(sx, timeout_sec=5):
    """Test 7: Receive in blocking mode."""
    print("\n" + "="*60)
    print("TEST 7: Receive (Blocking Mode)")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    print(f"Waiting for message (timeout: {timeout_sec} seconds)...")
    start_time = ticks_ms()
    
    msg, status = sx.recv(timeout_en=True, timeout_ms=timeout_sec * 1000)
    
    elapsed = ticks_diff(ticks_ms(), start_time) / 1000.0
    
    if status == ERR_NONE:
        print(f"✓ Message received after {elapsed:.2f} seconds")
        print(f"  Message: {msg.decode()}")
        print(f"  Length: {len(msg)} bytes")
        
        # Read RSSI and SNR
        try:
            rssi = sx.getRSSI()
            snr = sx.getSNR()
            print(f"  RSSI: {rssi:.2f} dBm")
            print(f"  SNR: {snr:.2f} dB")
        except:
            pass
    elif status == -6:  # ERR_RX_TIMEOUT
        print(f"ℹ No message received within {timeout_sec} seconds (timeout)")
    else:
        print_status(f"Receive operation (elapsed: {elapsed:.2f}s)", status)
    
    return True

def test_blocking_callback_modes(sx):
    """Test 8: Test blocking and non-blocking callback modes."""
    print("\n" + "="*60)
    print("TEST 8: Blocking/Non-blocking Mode Changes")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    # Test non-blocking mode
    def dummy_callback(events):
        print(f"  Callback triggered with events: {events}")
    
    status = sx.setBlockingCallback(blocking=False, callback=dummy_callback)
    print_status("Set to non-blocking mode with callback", status)
    sleep_ms(100)
    
    # Switch back to blocking mode
    status = sx.setBlockingCallback(blocking=True, callback=None)
    print_status("Set back to blocking mode", status)
    sleep_ms(100)
    
    return True

def test_frequency_scan(sx):
    """Test 9: Test frequency changes across the band."""
    print("\n" + "="*60)
    print("TEST 9: Frequency Scanning")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    frequencies = [868.0, 868.1, 868.3, 868.5, 868.7, 868.9]
    
    for freq in frequencies:
        status = sx.setFrequency(freq)
        if status == ERR_NONE:
            print(f"✓ Frequency set to {freq} MHz")
        else:
            print_status(f"Set frequency to {freq} MHz", status)
        sleep_ms(50)
    
    # Return to original frequency
    sx.setFrequency(FREQUENCY)
    return True

def test_power_levels(sx):
    """Test 10: Test different TX power levels."""
    print("\n" + "="*60)
    print("TEST 10: TX Power Level Changes")
    print("="*60)
    
    if sx is None:
        print("✗ SX1262 object not initialized")
        return False
    
    power_levels = [-9, -6, -3, 0, 3, 6, 9, 12, 14, 17, 20, 22]
    
    for power in power_levels:
        status = sx.setOutputPower(power)
        if status == ERR_NONE:
            print(f"✓ TX power set to {power} dBm")
        else:
            print_status(f"Set TX power to {power} dBm", status)
        sleep_ms(50)
    
    # Return to original power
    sx.setOutputPower(TX_POWER)
    return True

def run_all_tests():
    """Run all test sequences."""
    print("\n" + "="*60)
    print("OpenMV RT1062 + Waveshare Core1262-868M Test Suite")
    print("="*60)
    print(f"Frequency: {FREQUENCY} MHz")
    print(f"Bandwidth: {BANDWIDTH} kHz")
    print(f"Spreading Factor: {SPREADING_FACTOR}")
    print(f"Coding Rate: {CODING_RATE}")
    print(f"TX Power: {TX_POWER} dBm")
    print("="*60)
    
    # Initialize
    sx = test_initialization()
    if sx is None:
        print("\n✗ Initialization failed. Cannot continue with tests.")
        return
    
    # Run tests
    tests = [
        ("Begin LoRa Mode", lambda: test_begin_lora(sx)),
        ("Operation Modes", lambda: test_operation_modes(sx)),
        ("Parameter Changes", lambda: test_parameter_changes(sx)),
        ("RSSI/SNR Reading", lambda: test_rssi_snr(sx)),
        ("Blocking/Callback Modes", lambda: test_blocking_callback_modes(sx)),
        ("Frequency Scanning", lambda: test_frequency_scan(sx)),
        ("Power Level Changes", lambda: test_power_levels(sx)),
        ("Transmit (Blocking)", lambda: test_transmit_blocking(sx)),
        ("Receive (Blocking)", lambda: test_receive_blocking(sx, timeout_sec=3)),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test '{test_name}' raised exception: {e}")
            failed += 1
        sleep_ms(200)  # Brief pause between tests
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    print("="*60)

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()

