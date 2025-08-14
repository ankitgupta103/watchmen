import machine
import time

# === PIN SETUP FOR SPI BUS 1 ===
# Control pins only (SPI pins are fixed for bus 1)
cs = machine.Pin('P3', machine.Pin.OUT)      # SPI Chip Select (SS)
reset = machine.Pin('P6', machine.Pin.OUT)   # Reset
busy = machine.Pin('P7', machine.Pin.IN)     # Busy status

# SPI setup - Bus 1 (pins P0=MOSI, P1=MISO, P2=SCK are automatic)
spi = machine.SPI(1, baudrate=1000000)

cs.on()     # CS high = not selected
reset.on()  # Reset high = normal operation

# === BASIC FUNCTIONS ===
def wait_ready():
    """Wait until SX1262 is ready"""
    while busy.value():
        time.sleep_us(10)

def send_command(cmd_data):
    """Send command to SX1262 and read response"""
    wait_ready()
    cs.off()  # Select chip
    
    # Send command and read response
    response = bytearray(len(cmd_data))
    spi.write_readinto(bytearray(cmd_data), response)
    cs.on()   # Deselect chip
    
    # Print command details
    cmd_name = get_command_name(cmd_data[0])
    print(f"  📤 CMD: {cmd_name} [0x{cmd_data[0]:02X}]")
    print(f"  📥 Response: {[hex(b) for b in response]}")
    
    return response

def send_command_read(cmd_data, read_len=0):
    """Send command and read additional data"""
    wait_ready()
    cs.off()
    
    # Send command
    spi.write(bytearray(cmd_data))
    
    # Read additional data if requested
    if read_len > 0:
        response = bytearray(read_len)
        spi.readinto(response)
        print(f"  📊 Read data: {[hex(b) for b in response]}")
        cs.on()
        return response
    
    cs.on()
    return None

def get_command_name(cmd_code):
    """Get human-readable command name"""
    commands = {
        0x80: "SetStandby",
        0x8A: "SetPacketType", 
        0x86: "SetRfFrequency",
        0x8B: "SetModulationParams",
        0x8E: "SetTxParams",
        0x8F: "SetBufferBaseAddress",
        0x0E: "WriteBuffer",
        0x8C: "SetPacketParams",
        0x83: "SetTx",
        0xC0: "GetStatus",
        0x1D: "GetStats",
        0x17: "GetPacketStatus"
    }
    return commands.get(cmd_code, f"Unknown_0x{cmd_code:02X}")

def get_status():
    """Get and decode SX1262 status"""
    wait_ready()
    cs.off()
    response = bytearray(2)
    spi.write_readinto(bytearray([0xC0, 0x00]), response)
    cs.on()
    
    status = response[1]
    chip_mode = (status >> 4) & 0x07
    cmd_status = (status >> 1) & 0x07
    
    modes = ["", "RFU", "STDBY_RC", "STDBY_XOSC", "FS", "RX", "TX", "RFU"]
    cmd_states = ["", "RFU", "Data available", "Cmd timeout", "Cmd error", "Cmd fail", "Cmd TX done", "RFU"]
    
    print(f"  📊 STATUS: 0x{status:02X}")
    print(f"    ├─ Chip Mode: {modes[chip_mode]} ({chip_mode})")
    print(f"    └─ Command Status: {cmd_states[cmd_status]} ({cmd_status})")
    
    return status

def reset_chip():
    """Reset the LoRa chip"""
    reset.off()
    time.sleep_us(100)
    reset.on()
    time.sleep_ms(10)

# === LORA SETUP FUNCTIONS ===
def set_standby():
    """Put chip in standby mode"""
    print("⚙️  Setting STANDBY mode...")
    send_command([0x80])
    get_status()
    print("✓ Standby mode\n")

def set_lora_mode():
    """Set to LoRa packet type"""
    print("⚙️  Setting LORA packet type...")
    send_command([0x8A, 0x01])  # 0x01 = LoRa, 0x00 = GFSK
    print("  📝 Packet Type: LoRa (0x01)")
    get_status()
    print("✓ LoRa mode\n")

def set_frequency(freq_mhz=868):
    """Set frequency in MHz (default 868MHz)"""
    print(f"⚙️  Setting FREQUENCY to {freq_mhz}MHz...")
    freq_hz = freq_mhz * 1000000
    freq_val = int(freq_hz * (2**25) / 32000000)
    
    cmd = [0x86,
           (freq_val >> 24) & 0xFF,
           (freq_val >> 16) & 0xFF,
           (freq_val >> 8) & 0xFF,
           freq_val & 0xFF]
    
    send_command(cmd)
    print(f"  📝 Frequency Value: 0x{freq_val:08X} ({freq_val})")
    print(f"  📝 Formula: {freq_hz} * 2^25 / 32MHz = {freq_val}")
    get_status()
    print(f"✓ Frequency: {freq_mhz}MHz\n")

def set_speed(speed="medium"):
    """Set LoRa speed with detailed parameter explanation"""
    print(f"⚙️  Setting MODULATION parameters for '{speed}' speed...")
    
    if speed == "fast":
        sf, bw, cr = 7, 0, 1    # SF7, 125kHz, 4/5
        rate = "5.5 kbps"
        range_km = "2-5km"
    elif speed == "slow":
        sf, bw, cr = 12, 0, 1   # SF12, 125kHz, 4/5  
        rate = "0.3 kbps"
        range_km = "15-40km"
    else:  # medium
        sf, bw, cr = 9, 0, 1    # SF9, 125kHz, 4/5
        rate = "1.8 kbps"
        range_km = "5-15km"
    
    send_command([0x8B, sf, bw, cr, 0x00])
    
    # Decode parameters
    bw_values = ["125kHz", "250kHz", "500kHz"]
    cr_values = ["4/5", "4/6", "4/7", "4/8"]
    
    print(f"  📝 Spreading Factor (SF): {sf}")
    print(f"  📝 Bandwidth (BW): {bw_values[bw]} ({bw})")
    print(f"  📝 Coding Rate (CR): {cr_values[cr-1]} ({cr})")
    print(f"  📝 Low Data Rate Opt: Auto (0x00)")
    print(f"  📊 Expected Rate: ~{rate}")
    print(f"  📊 Expected Range: ~{range_km}")
    
    get_status()
    print(f"✓ Speed: {speed} ({rate})\n")

def set_power(power_dbm=14):
    """Set transmit power with detailed explanation"""
    print(f"⚙️  Setting TX POWER to {power_dbm}dBm...")
    
    if power_dbm > 22:
        power_dbm = 22
        print("  ⚠️  Power limited to 22dBm (regulatory limit)")
    
    send_command([0x8E, power_dbm, 0x00, 0x01, 0x01])
    
    # Convert to mW
    power_mw = round(10 ** (power_dbm / 10), 1)
    
    print(f"  📝 Power (dBm): {power_dbm}")
    print(f"  📝 Power (mW): {power_mw}")
    print(f"  📝 PA Ramp Time: 0x00 (10µs)")
    print(f"  📝 PA Duty Cycle: 0x01")
    print(f"  📝 PA HP Max: 0x01")
    
    get_status()
    print(f"✓ Power: {power_dbm}dBm ({power_mw}mW)\n")

# === SEND/RECEIVE FUNCTIONS ===
def send_message(message):
    """Send a text message with detailed transmission info"""
    print(f"📡 SENDING MESSAGE: '{message}'")
    
    # Convert string to bytes
    if isinstance(message, str):
        data = message.encode('utf-8')
    else:
        data = message
    
    print(f"  📝 Message Length: {len(data)} bytes")
    print(f"  📝 Message Data: {[hex(b) for b in data]}")
    
    # Set buffer address
    print("  ⚙️  Setting buffer base address...")
    send_command([0x8F, 0x00, 0x00])  # TX base=0, RX base=0
    
    # Write data to buffer
    print("  ⚙️  Writing data to buffer...")
    wait_ready()
    cs.off()
    write_cmd = bytearray([0x0E, 0x00] + list(data))
    spi.write(write_cmd)
    cs.on()
    print(f"  📤 WriteBuffer: [0x0E, 0x00] + {len(data)} data bytes")
    
    # Set packet parameters
    print("  ⚙️  Setting packet parameters...")
    packet_cmd = [0x8C, 0x00, len(data), 0x00, 0x00, 0x00]
    send_command(packet_cmd)
    print(f"  📝 Preamble Length: 0x00 (default)")
    print(f"  📝 Payload Length: {len(data)} bytes")
    print(f"  📝 Header Type: 0x00 (explicit)")
    print(f"  📝 CRC: 0x00 (off)")
    print(f"  📝 IQ: 0x00 (standard)")
    
    # Start transmission
    print("  ⚙️  Starting transmission...")
    send_command([0x83, 0x00, 0x00, 0x00])  # SetTx with no timeout
    print("  📝 TX Timeout: No timeout (0x000000)")
    
    # Check status after transmission command
    get_status()
    
    print(f"✅ Message queued for transmission!\n")

# === MAIN SETUP FUNCTION ===
def init_lora(freq=868, speed="medium", power=14):
    """Initialize LoRa with simple parameters"""
    print("🚀 Starting LoRa on SPI Bus 1...")
    print("📍 Pins: P0=MOSI, P1=MISO, P2=SCK, P3=CS, P6=RESET, P7=BUSY")
    
    reset_chip()
    set_standby()
    set_lora_mode()
    set_frequency(freq)
    set_speed(speed)
    set_power(power)
    
    print("✅ LoRa ready!")

# === MAIN PROGRAM ===
if __name__ == "__main__":
    try:
        # Initialize LoRa with MAXIMUM SPEED and POWER
        # Options: freq=868/915, speed="fast"/"medium"/"slow", power=0-22
        init_lora(freq=868, speed="fast", power=22)
        
        # Send messages every 5 seconds
        counter = 0
        while True:
            counter += 1
            message = f"OpenMV #{counter}"
            send_message(message)
            
            time.sleep(5)  # Wait 5 seconds
            
    except KeyboardInterrupt:
        print("⏹️ Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

# === QUICK TEST FUNCTIONS ===
def test_speeds():
    """Test different speeds"""
    speeds = ["fast", "medium", "slow"]
    
    for speed in speeds:
        print(f"\n--- Testing {speed} speed ---")
        init_lora(speed=speed)
        send_message(f"Test {speed} speed")
        time.sleep(3)

def test_connection():
    """Simple connection test"""
    print("🔧 Testing LoRa connection...")
    init_lora()
    
    for i in range(3):
        send_message(f"Test message {i+1}")
        time.sleep(2)
    
    print("✅ Connection test complete!")

# Uncomment to run tests:
# test_connection()
# test_speeds()